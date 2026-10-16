"""Private operator backup: consistent pg_dump, authenticated encryption, Drive.

Never imported by the web app. No route may export the school database.
"""
import base64
import binascii
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from urllib.error import URLError
from zipfile import ZipFile, ZIP_STORED

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.exceptions import InvalidTag
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

MAGIC=b'FAEHUB-BACKUP-1\n'
CHUNK=1024*1024


def key():
    try:
        value=base64.urlsafe_b64decode(os.environ['FAEHUB_BACKUP_KEY'])
        if len(value)!=32:
            raise ValueError()
        return value
    except (KeyError,ValueError,binascii.Error):
        raise ValueError('Configure FAEHUB_BACKUP_KEY com 32 bytes aleatórios em base64, guardados fora do backup.') from None


def encrypt(source, target, encryption_key):
    nonce=os.urandom(12)
    encryptor=Cipher(algorithms.AES(encryption_key),modes.GCM(nonce)).encryptor()
    encryptor.authenticate_additional_data(MAGIC)
    with Path(source).open('rb') as src, Path(target).open('xb') as dst:
        dst.write(MAGIC+nonce)
        while block:=src.read(CHUNK):
            dst.write(encryptor.update(block))
        dst.write(encryptor.finalize()); dst.write(encryptor.tag)


def decrypt(source, target, encryption_key):
    created=False
    try:
        with Path(source).open('rb') as src:
            if src.read(len(MAGIC))!=MAGIC:
                raise ValueError('Formato de backup desconhecido.')
            nonce=src.read(12)
            src.seek(-16,2); tag=src.read(16); length=src.tell()-len(MAGIC)-12-16
            if length<0:
                raise ValueError('Backup incompleto.')
            decryptor=Cipher(algorithms.AES(encryption_key),modes.GCM(nonce,tag)).decryptor()
            decryptor.authenticate_additional_data(MAGIC)
            src.seek(len(MAGIC)+12)
            with Path(target).open('xb') as dst:
                created=True
                while length:
                    block=src.read(min(CHUNK,length))
                    if not block:
                        raise ValueError('Backup incompleto.')
                    dst.write(decryptor.update(block));length-=len(block)
                dst.write(decryptor.finalize())
    except (InvalidTag,ValueError,OSError):
        # Only the exact temporary file this function created can be removed.
        # A pre-existing destination must NEVER be removed.
        if created:
            Path(target).unlink(missing_ok=True)
        raise ValueError('Não foi possível autenticar o backup. Confira a chave e a integridade do arquivo.') from None


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def pg_environment(url):
    config=conninfo_to_dict(url)
    env={name:value for name,value in os.environ.items() if not name.startswith('PG')}
    names={'dbname':'PGDATABASE','host':'PGHOST','hostaddr':'PGHOSTADDR','port':'PGPORT','user':'PGUSER',
           'password':'PGPASSWORD','sslmode':'PGSSLMODE','sslrootcert':'PGSSLROOTCERT','sslcert':'PGSSLCERT',
           'sslkey':'PGSSLKEY','options':'PGOPTIONS','application_name':'PGAPPNAME',
           'connect_timeout':'PGCONNECT_TIMEOUT','channel_binding':'PGCHANNELBINDING',
           'target_session_attrs':'PGTARGETSESSIONATTRS','gssencmode':'PGGSSENCMODE'}
    if set(config)-set(names):
        raise ValueError('Use uma conexão PostgreSQL direta ou Session pooler com parâmetros libpq explícitos.')
    for name,value in config.items():
        env[names[name]]=value
    env['PGCONNECT_TIMEOUT']='15'
    return env


def run_pg(program, args, url=None):
    executable=shutil.which(program)
    if not executable:
        raise ValueError('Instale os clientes PostgreSQL 17+ (pg_dump/pg_restore) no operador de backup.')
    try:
        result=subprocess.run([executable,*args],env=pg_environment(url) if url else os.environ.copy(),
                              capture_output=True,timeout=1800,check=False)
    except (OSError,subprocess.TimeoutExpired):
        raise ValueError('A ferramenta PostgreSQL não concluiu. Nenhum envio ao Drive foi iniciado.') from None
    if result.returncode:
        # Never echo libpq stderr: it can contain private hostnames/credentials.
        raise ValueError('A ferramenta PostgreSQL recusou a operação. Confira versão, conexão e permissões privadamente.')
    return result.stdout


def table_counts(conn):
    tables=[r[0] for r in conn.execute("""SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename""")]
    return {name:conn.execute(sql.SQL('SELECT count(*) FROM public.{}').format(sql.Identifier(name))).fetchone()[0] for name in tables}


def create_backup(output_dir, url):
    protector=key()
    output_dir=Path(output_dir).resolve()
    if not output_dir.is_dir():
        raise ValueError('Crie uma pasta privada fora do repositório e indique-a como destino.')
    root=Path(__file__).resolve().parent
    if output_dir==root or root in output_dir.parents:
        raise ValueError('O backup não pode ficar dentro do repositório.')
    target=output_dir/('faehub-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+os.urandom(4).hex()+'.fhbackup')
    with tempfile.TemporaryDirectory(prefix='faehub-backup-') as scratch:
        dump=Path(scratch)/'database.dump'; bundle=Path(scratch)/'bundle.zip'
        with psycopg.connect(url,connect_timeout=15) as conn:
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            snapshot=conn.execute('SELECT pg_export_snapshot()').fetchone()[0]
            counts=table_counts(conn)
            # Only app/public schema. Auth/storage services are not used by this app.
            run_pg('pg_dump',['--format=custom','--no-owner','--no-privileges','--schema=public',
                '--snapshot='+snapshot,'--file='+str(dump)],url)
        run_pg('pg_restore',['--list',str(dump)])
        manifest=dict(format=1,created_at=datetime.now(timezone.utc).isoformat(),schema='public',
                      tables=counts,sha256=digest(dump),scope='FaeHub public schema, including DB attachments/photos')
        with ZipFile(bundle,'x',compression=ZIP_STORED) as archive:
            archive.write(dump,'database.dump')
            archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False))
        encrypt(bundle,target,protector)
        with verified_backup(target,protector):
            pass
    return target


@contextmanager
def verified_backup(path, encryption_key):
    with tempfile.TemporaryDirectory(prefix='faehub-restore-check-') as scratch:
        bundle=Path(scratch)/'bundle.zip'; dump=Path(scratch)/'database.dump'
        decrypt(path,bundle,encryption_key)
        with ZipFile(bundle) as archive:
            if set(archive.namelist())!={'database.dump','manifest.json'}:
                raise ValueError('Conteúdo de backup inesperado.')
            manifest=json.loads(archive.read('manifest.json'))
            with archive.open('database.dump') as source,dump.open('xb') as destination:
                shutil.copyfileobj(source,destination,CHUNK)
        if manifest.get('format')!=1 or manifest.get('sha256')!=digest(dump):
            raise ValueError('A verificação do conteúdo do backup falhou.')
        run_pg('pg_restore',['--list',str(dump)])
        yield dump,manifest


def restore_to_empty(path, restore_url, source_url):
    if not restore_url or not source_url:
        raise ValueError('Informe as conexões de origem e de um banco de teste vazio, distintos.')
    source=conninfo_to_dict(source_url);target=conninfo_to_dict(restore_url)
    if (source.get('host'),source.get('port','5432'),source.get('dbname'))==(target.get('host'),target.get('port','5432'),target.get('dbname')):
        raise ValueError('Restauração sobre a origem de produção é proibida por esta ferramenta.')
    with verified_backup(path,key()) as (dump,manifest):
        with psycopg.connect(restore_url,connect_timeout=15) as conn:
            if conn.execute("SELECT 1 FROM pg_tables WHERE schemaname='public' LIMIT 1").fetchone():
                raise ValueError('O destino não está vazio. Nenhum dado será sobrescrito.')
            # Do not permit two concurrent restore operators to pass the empty gate.
            if not conn.execute('SELECT pg_try_advisory_lock(16102026)').fetchone()[0]:
                raise ValueError('Outro operador está verificando este destino.')
            # An empty PostgreSQL database already has the public namespace.
            # Omit only its CREATE SCHEMA TOC entry; never DROP that namespace.
            listing=run_pg('pg_restore',['--list',str(dump)]).decode('utf-8')
            restore_list=dump.parent/'restore.list'
            restore_list.write_text('\n'.join(line for line in listing.splitlines()
                if not re.match(r'^\d+;\s+\d+\s+\d+\s+SCHEMA - public(?:\s|$)',line))+'\n',encoding='utf-8')
            run_pg('pg_restore',['--dbname='+target.get('dbname','postgres'),'--single-transaction',
                                '--exit-on-error','--no-owner','--no-privileges',
                                '--use-list='+str(restore_list),str(dump)],restore_url)
            if table_counts(conn)!=manifest['tables']:
                raise ValueError('Restauração executada, mas as contagens divergem. Não utilize este destino.')
    return manifest


def drive_upload(path):
    """Upload once; no sharing changes, deletes or uncertain automatic retries."""
    try:
        fields={name:os.environ['FAEHUB_DRIVE_'+name] for name in ('CLIENT_ID','CLIENT_SECRET','REFRESH_TOKEN','FOLDER_ID')}
        request=Request('https://oauth2.googleapis.com/token',data=urlencode(dict(
            client_id=fields['CLIENT_ID'],client_secret=fields['CLIENT_SECRET'],refresh_token=fields['REFRESH_TOKEN'],grant_type='refresh_token')).encode(),method='POST')
        with urlopen(request,timeout=15) as response:
            access=json.loads(response.read(16384))['access_token']
        metadata=dict(name=Path(path).name,parents=[fields['FOLDER_ID']],appProperties={'app':'faehub-backup-v1'})
        request=Request('https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&fields=id,size,md5Checksum',
            data=json.dumps(metadata).encode(),headers={'Authorization':'Bearer '+access,'Content-Type':'application/json',
            'X-Upload-Content-Type':'application/octet-stream','X-Upload-Content-Length':str(Path(path).stat().st_size)},method='POST')
        with urlopen(request,timeout=30) as response:
            location=response.headers.get('Location','')
        parsed=urlsplit(location)
        if parsed.scheme!='https' or parsed.hostname!='www.googleapis.com' or parsed.username or parsed.password:
            raise ValueError('Destino de upload recusado.')
        # urllib requires a bounded buffer here; reject huge backups before upload.
        if Path(path).stat().st_size>128*1024*1024:
            raise ValueError('Arquivo acima de 128 MB: use um operador com upload segmentado. A cópia local foi preservada.')
        body=Path(path).read_bytes()
        request=Request(location,data=body,headers={'Authorization':'Bearer '+access,'Content-Type':'application/octet-stream'},method='PUT')
        with urlopen(request,timeout=180) as response:
            result=json.loads(response.read(16384))
        if str(result.get('size'))!=str(len(body)) or result.get('md5Checksum')!=hashlib.md5(body).hexdigest() or not result.get('id'):
            raise ValueError('O Drive não confirmou tamanho e integridade. Confira a pasta antes de tentar novo envio.')
        return result['id']
    except (KeyError,URLError,OSError,TypeError):
        raise ValueError('O envio ao Drive não foi confirmado. Confira autorização/pasta antes de tentar novamente. A cópia local permanece.') from None
