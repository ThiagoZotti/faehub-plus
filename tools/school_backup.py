"""Private CLI; backup bytes and credentials must never be committed."""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import backup_service as backup


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--env-file',type=Path,help='Arquivo privado fora do Git; valores existentes prevalecem.')
    commands=parser.add_subparsers(dest='command',required=True)
    create=commands.add_parser('create');create.add_argument('--output-dir',required=True,type=Path);create.add_argument('--drive',action='store_true')
    verify=commands.add_parser('verify');verify.add_argument('archive',type=Path)
    restore=commands.add_parser('test-restore');restore.add_argument('archive',type=Path)
    args=parser.parse_args()
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file,override=False)
    url=os.getenv('FAEHUB_BACKUP_DATABASE_URL') or os.getenv('FAEHUB_DATABASE_URL') or os.getenv('DATABASE_URL')
    try:
        if args.command=='create':
            if not url:raise ValueError('Configure a conexão privada de backup (direta ou Session pooler, não Transaction pooler).')
            target=backup.create_backup(args.output_dir,url)
            print('Backup criptografado criado e integridade verificada. Não substitui teste de restauração.')
            if args.drive:
                backup.drive_upload(target)
                print('Drive confirmou o arquivo e seu checksum; permissões não foram ampliadas.')
        elif args.command=='verify':
            with backup.verified_backup(args.archive,backup.key()):pass
            print('Integridade e formato verificados; nenhuma restauração foi executada.')
        else:
            backup.restore_to_empty(args.archive,os.getenv('FAEHUB_RESTORE_DATABASE_URL'),url)
            print('Restauração em destino vazio concluída; contagens de todas as tabelas conferidas.')
    except Exception:
        # Provider/DB exceptions may include secrets. Never expose raw tracebacks.
        print('Operação não confirmada. Verifique privadamente configuração, dependências, integridade e destino. Nenhum dado de produção foi substituído.',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
