"""Optional TOTP, encrypted at rest; recovery codes are single-use hashes."""
import base64
import hashlib
import os
import re
import secrets
import time
from io import BytesIO

from cryptography.fernet import Fernet, InvalidToken
import pyotp
import qrcode
from werkzeug.security import check_password_hash

import database as db


def init_mfa():
    if db.using_postgres():
        return
    with db.connection() as conn:
        conn.executescript('''
          CREATE TABLE IF NOT EXISTS account_mfa (
            username TEXT PRIMARY KEY REFERENCES users(username),secret_ciphertext TEXT,
            pending_ciphertext TEXT,pending_until INTEGER,enabled INTEGER NOT NULL DEFAULT 0,
            last_counter BIGINT NOT NULL DEFAULT -1);
          CREATE TABLE IF NOT EXISTS mfa_recovery_codes (
            username TEXT NOT NULL REFERENCES account_mfa(username),code_hash TEXT NOT NULL,
            used_at TEXT,PRIMARY KEY(username,code_hash));
        ''')


def cipher():
    try:
        return Fernet(os.environ.get('FAEHUB_MFA_ENCRYPTION_KEY','').encode('ascii'))
    except (ValueError, UnicodeError):
        raise ValueError('O autenticador aguarda a configuração privada da chave de proteção no servidor.') from None


def configured():
    try:
        cipher()
        return True
    except ValueError:
        return False


def enabled(username):
    with db.connection() as conn:
        row=conn.execute('SELECT enabled FROM account_mfa WHERE username=?',(username,)).fetchone()
        return bool(row and row['enabled'])


def _password(conn, username, password):
    row=conn.execute('''SELECT u.password_hash FROM users u JOIN account_identities ai ON ai.username=u.username
        WHERE u.username=? AND u.active=TRUE AND ai.verified_at IS NOT NULL AND ai.verified_at<>0''',(username,)).fetchone()
    if not row or len(password)>128 or not check_password_hash(row['password_hash'],password):
        raise ValueError('Confirme a senha atual de uma conta ativada por e-mail.')


def _revoke(conn, username):
    conn.execute('''INSERT INTO auth_versions(username,version) VALUES(?,1)
        ON CONFLICT(username) DO UPDATE SET version=auth_versions.version+1''',(username,))


def begin(username,password):
    protector=cipher()
    secret=pyotp.random_base32()
    with db.connection() as conn:
        _password(conn,username,password)
        conn.execute('INSERT INTO account_mfa(username) VALUES(?) ON CONFLICT(username) DO NOTHING',(username,))
        changed=conn.execute('''UPDATE account_mfa SET pending_ciphertext=?,pending_until=?
            WHERE username=? AND enabled=FALSE''',(protector.encrypt(secret.encode()).decode(),int(time.time())+600,username))
        if changed.rowcount!=1:
            raise ValueError('Seu autenticador já está ativo.')


def pending(username):
    with db.connection() as conn:
        row=conn.execute('''SELECT pending_ciphertext FROM account_mfa WHERE username=? AND enabled=FALSE
            AND pending_until>=?''',(username,int(time.time()))).fetchone()
    if not row or not row['pending_ciphertext']:
        return None
    try:
        return cipher().decrypt(row['pending_ciphertext'].encode()).decode()
    except InvalidToken:
        raise ValueError('Não foi possível abrir a configuração. Confira a chave privada do servidor.') from None


def provisioning(secret,username):
    uri=pyotp.TOTP(secret).provisioning_uri(name=username,issuer_name='FaeHub+')
    output=BytesIO()
    qrcode.make(uri).save(output,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()


def _counter(secret,code):
    if not re.fullmatch(r'\d{6}',code,flags=re.ASCII):
        return None
    counter=int(time.time())//30
    totp=pyotp.TOTP(secret)
    for tick in (counter,counter-1,counter+1):
        if secrets.compare_digest(totp.at(tick*30),code):
            return tick
    return None


def _codes(conn, username):
    conn.execute('DELETE FROM mfa_recovery_codes WHERE username=?',(username,))
    codes=['-'.join(re.findall('.{4}',secrets.token_hex(8))) for _ in range(10)]
    conn.executemany('INSERT INTO mfa_recovery_codes(username,code_hash) VALUES(?,?)',
        [(username,hashlib.sha256(code.encode()).hexdigest()) for code in codes])
    return codes


def activate(username,code):
    with db.connection() as conn:
        current=conn.execute('SELECT pending_ciphertext FROM account_mfa WHERE username=?',(username,)).fetchone()
        ciphertext=current['pending_ciphertext'] if current else None
        try:
            secret=cipher().decrypt(ciphertext.encode()).decode() if ciphertext else None
        except InvalidToken:
            raise ValueError('Confira a chave privada do servidor antes de ativar.') from None
        tick=_counter(secret,code.strip()) if secret else None
        if tick is None:
            raise ValueError('Código inválido ou configuração expirada. Confira o relógio do celular e tente novamente.')
        row=conn.execute('''UPDATE account_mfa SET secret_ciphertext=pending_ciphertext,
            pending_ciphertext=NULL,pending_until=NULL,enabled=TRUE,last_counter=?
            WHERE username=? AND enabled=FALSE AND pending_until>=? AND pending_ciphertext=?''',
            (tick,username,int(time.time()),ciphertext))
        if row.rowcount!=1:
            raise ValueError('A configuração mudou. Recomece antes de ativar.')
        codes=_codes(conn,username)
        _revoke(conn,username)
        conn.execute('INSERT INTO activity_log(username,action,details) VALUES(?,?,?)',(username,'mfa_ativado','Autenticador confirmado.'))
    return codes


def verify(username,code,recovery=False):
    with db.connection() as conn:
        return _verify(conn,username,code,recovery)


def _verify(conn,username,code,recovery=False):
    code=code.strip().lower()
    if len(code)>64:
        return False
    row=conn.execute('SELECT secret_ciphertext,last_counter FROM account_mfa WHERE username=? AND enabled=TRUE',(username,)).fetchone()
    if not row:
        return False
    if recovery:
        # Hash the exact normalized code; codes cannot reset somebody else's MFA.
        changed=conn.execute('''UPDATE mfa_recovery_codes SET used_at=CURRENT_TIMESTAMP
            WHERE username=? AND code_hash=? AND used_at IS NULL AND EXISTS
            (SELECT 1 FROM account_mfa WHERE username=? AND enabled=TRUE)''',
            (username,hashlib.sha256(code.encode()).hexdigest(),username))
        return changed.rowcount==1
    try:
        secret=cipher().decrypt(row['secret_ciphertext'].encode()).decode()
    except InvalidToken:
        raise ValueError('Autenticador indisponível. Use um código de recuperação ou contate o proprietário.') from None
    tick=_counter(secret,code)
    if tick is None:
        return False
    return conn.execute('''UPDATE account_mfa SET last_counter=? WHERE username=? AND enabled=TRUE
        AND last_counter<? AND secret_ciphertext=?''',(tick,username,tick,row['secret_ciphertext'])).rowcount==1


def manage(username,password,code,action,*,recovery=False):
    with db.connection() as conn:
        _password(conn,username,password)
        if not _verify(conn,username,code,recovery):
            raise ValueError('Código inválido ou já utilizado. Aguarde um novo código no autenticador.')
        if action=='regenerate':
            codes=_codes(conn,username)
        elif action=='disable':
            conn.execute('UPDATE account_mfa SET enabled=FALSE,secret_ciphertext=NULL WHERE username=?',(username,))
            conn.execute('DELETE FROM mfa_recovery_codes WHERE username=?',(username,))
            codes=None
        else:
            raise ValueError('Ação inválida.')
        _revoke(conn,username)
        conn.execute('INSERT INTO activity_log(username,action,details) VALUES(?,?,?)',(username,'mfa_'+action,'Alteração confirmada pelo titular.'))
        return codes
