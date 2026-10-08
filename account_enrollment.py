"""Invitation-only enrollment, portable to Supabase and isolated test databases.

School roles and academic links remain owned by the existing authorization layer.
Only a successfully delivered invitation can verify an address or activate access.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
import database as db

DEMO_USERS = ('gilberto', 'aline', 'thiago.zotti', 'jonathan.samuel',
              'pablo.sousa', 'marlon.eduardo', 'responsavel.thiago')


def init_enrollment(conn):
    if db.using_postgres():
        return  # Production schema is installed only by versioned migrations.
    conn.executescript('''
      CREATE TABLE IF NOT EXISTS account_identities (
        username TEXT PRIMARY KEY REFERENCES users(username) ON DELETE CASCADE,
        email TEXT NOT NULL UNIQUE, verified_at INTEGER
      );
      CREATE TABLE IF NOT EXISTS account_invitations (
        id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE REFERENCES users(username),
        email TEXT NOT NULL, token_hash TEXT UNIQUE, expires_at INTEGER,
        status TEXT NOT NULL DEFAULT 'draft'
          CHECK(status IN ('draft','sending','sent','failed','used','revoked')),
        created_by TEXT NOT NULL REFERENCES users(username), created_at INTEGER NOT NULL,
        last_sent_at INTEGER, used_at INTEGER
      );
      CREATE TABLE IF NOT EXISTS enrollment_settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS auth_rate_limits (
        key TEXT NOT NULL, bucket_window INTEGER NOT NULL, attempts INTEGER NOT NULL,
        PRIMARY KEY(key,bucket_window)
      );
    ''')


def demos_enabled(conn=None):
    if conn is None:
        with db.connection() as connection:
            return demos_enabled(connection)
    row = conn.execute("SELECT value FROM enrollment_settings WHERE key='demos_disabled'").fetchone()
    return not row or row['value'] != '1'


def normalize_email(value):
    email = value.strip().lower()
    if len(email) > 254 or '..' in email or email.startswith('.') or '.@' in email or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}", email):
        raise ValueError('Informe um e-mail válido, como nome@escola.com.br.')
    return email


def validate_password(password, confirmation):
    if not 15 <= len(password) <= 128:
        raise ValueError('Use uma senha entre 15 e 128 caracteres. Uma frase longa é uma boa opção.')
    if password != confirmation:
        raise ValueError('As senhas não coincidem. Digite a mesma senha nos dois campos.')


def mail_configured():
    """HTTPS transport works on Render Free, unlike outbound SMTP ports."""
    base = os.getenv('FAEHUB_PUBLIC_URL', '').rstrip('/')
    parsed = urlsplit(base)
    return bool(os.getenv('FAEHUB_RESEND_API_KEY') and os.getenv('FAEHUB_MAIL_FROM')
                and parsed.scheme == 'https' and parsed.netloc and not parsed.username
                and not parsed.query and not parsed.fragment and parsed.path in ('', '/'))


def send_invitation_email(email, token, invitation_id):
    if not mail_configured():
        raise ValueError('O envio de e-mails ainda não está configurado. O convite permanece pendente.')
    link = os.environ['FAEHUB_PUBLIC_URL'].rstrip('/') + '/ativar#convite=' + token
    payload = json.dumps({
        'from': os.environ['FAEHUB_MAIL_FROM'], 'to': [email],
        'subject': 'Ative seu acesso ao FaeHub+',
        'text': 'A escola autorizou seu acesso ao FaeHub+.\n\n'
                'Abra o link abaixo para confirmar este e-mail e criar sua senha:\n' + link +
                '\n\nO convite vale por 48 horas e só pode ser usado uma vez. '
                'Seu perfil e seus vínculos foram definidos pela escola. '
                'Se não esperava este convite, ignore esta mensagem. Nunca compartilhe o link.'
    }).encode('utf-8')
    # No request payload, token, email-provider response or API key is logged.
    req = Request('https://api.resend.com/emails', data=payload, method='POST', headers={
        'Authorization': 'Bearer ' + os.environ['FAEHUB_RESEND_API_KEY'],
        'Content-Type': 'application/json', 'User-Agent': 'FaeHub/1.0',
        'Idempotency-Key': 'invitation-' + invitation_id + '-' + hashlib.sha256(token.encode()).hexdigest()
    })
    try:
        with urlopen(req, timeout=10) as response:
            result = json.loads(response.read(16384))
            if not isinstance(result, dict) or not isinstance(result.get('id'), str) or not result['id']:
                raise ValueError('O serviço de e-mail não confirmou o envio. Tente novamente mais tarde.')
    except (URLError, HTTPError, TimeoutError, OSError, json.JSONDecodeError):
        raise ValueError('O serviço de e-mail não confirmou o envio. O link não foi liberado; tente novamente mais tarde.') from None


def authorize_invitation_actor(actor, action, *, username=None, email=None, invitation_id=None):
    """Public demo passwords must never grant arbitrary real identities.

    The initial director can only convert their own account through a mailbox
    explicitly authorized in the private server configuration. After that,
    invitations are issued by verified, active directors.
    """
    with db.connection() as conn:
        user = conn.execute('''SELECT u.active,COALESCE(ar.role,u.role) role,ai.verified_at
                               FROM users u LEFT JOIN account_roles ar ON ar.username=u.username
                               LEFT JOIN account_identities ai ON ai.username=u.username WHERE u.username=?''', (actor,)).fetchone()
        if not user or not user['active'] or user['role'] != 'diretor':
            raise ValueError('Somente a direção ativa pode autorizar convites.')
        if user['verified_at']:
            return
        if invitation_id:
            row = conn.execute('SELECT username,email FROM account_invitations WHERE id=?', (invitation_id,)).fetchone()
            if not row:
                raise ValueError('Convite não encontrado.')
            username, email = row['username'], row['email']
        allowed = os.getenv('FAEHUB_BOOTSTRAP_ADMIN_EMAIL', '').strip().lower()
        if not allowed or username != actor or (email or '').strip().lower() != allowed:
            raise ValueError('Ative primeiro sua conta de diretor pelo e-mail autorizado na configuração privada do servidor. A direção demo não pode criar contas reais para outras pessoas.')
        # A validated address is still confirmed only by receiving the mailed bearer.
        normalize_email(allowed)


def create_invitation(actor, username, email, *, name=None, role=None, student_id=None, roster=()):
    email = normalize_email(email)
    username = username.strip().lower()
    if not re.fullmatch(r'[a-z0-9_.-]{3,50}', username):
        raise ValueError('Identificação: 3 a 50 letras sem acento, números, ponto, hífen ou sublinhado.')
    with db.connection() as conn:
        existing = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        identity = conn.execute('SELECT * FROM account_identities WHERE username=?', (username,)).fetchone()
        if identity and identity['verified_at']:
            raise ValueError('Esta conta já foi ativada. O titular deve usar a recuperação de senha.')
        reserved = conn.execute('SELECT username FROM account_identities WHERE email=?', (email,)).fetchone()
        if reserved and reserved['username'] != username:
            raise ValueError('Este e-mail já está vinculado a outra conta. Confira o cadastro escolar.')
        if not existing:
            if not name or not name.strip() or len(name.strip()) > 160:
                raise ValueError('Informe o nome completo, com até 160 caracteres.')
            if role not in ('aluno', 'professor', 'diretor', 'responsavel'):
                raise ValueError('Selecione um perfil válido.')
            if role in ('aluno', 'responsavel') and student_id not in {s['id'] for s in roster}:
                raise ValueError('Selecione uma matrícula cadastrada para vincular o acesso.')
            if role == 'aluno' and conn.execute('SELECT 1 FROM users WHERE student_id=?', (student_id,)).fetchone():
                raise ValueError('Esta matrícula já tem uma conta. Convide a conta existente.')
            stored_role = 'aluno' if role == 'responsavel' else role
            # Unusable random password + inactive: pending users cannot log in.
            conn.execute('''INSERT INTO users(username,password_hash,name,role,student_id,active)
                            VALUES(?,?,?,?,?,FALSE)''',
                         (username, generate_password_hash(secrets.token_urlsafe(48)), name.strip(),
                          stored_role, student_id if role == 'aluno' else None))
            if role == 'responsavel':
                conn.execute('INSERT INTO account_roles(username,role) VALUES(?,?)', (username, role))
                conn.execute('''INSERT INTO guardian_links(guardian_username,student_id,relationship)
                                VALUES(?,?,'Responsável legal')''', (username, student_id))
        elif not existing['active'] and not identity:
            if username not in DEMO_USERS or demos_enabled(conn):
                raise ValueError('Esta conta está desativada. Revise o bloqueio antes de convidá-la.')
        conn.execute('''INSERT INTO account_identities(username,email) VALUES(?,?)
                        ON CONFLICT(username) DO UPDATE SET email=excluded.email''', (username, email))
        invitation_id = secrets.token_hex(16)
        conn.execute('''INSERT INTO account_invitations(id,username,email,created_by,created_at)
                        VALUES(?,?,?,?,?) ON CONFLICT(username) DO UPDATE SET
                        email=excluded.email,token_hash=NULL,expires_at=NULL,status='draft',
                        created_by=excluded.created_by,created_at=excluded.created_at,last_sent_at=NULL,used_at=NULL''',
                     (invitation_id, username, email, actor, int(time.time())))
        saved = conn.execute('SELECT id FROM account_invitations WHERE username=?', (username,)).fetchone()
        conn.execute('INSERT INTO activity_log(username,action,details) VALUES(?,?,?)',
                     (actor, 'convite_preparado', username))
    return saved['id']


def deliver_invitation(actor, invitation_id):
    if not mail_configured():
        raise ValueError('Configure o serviço de e-mail para enviar este convite. O cadastro já está salvo e permanece pendente.')
    now = int(time.time())
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode()).hexdigest()
    with db.connection() as conn:
        # Atomic cooldown across workers. No provider call while holding a lock.
        row = conn.execute('''UPDATE account_invitations SET status='sending',token_hash=?,
                              expires_at=?,last_sent_at=? WHERE id=? AND status IN ('draft','failed','sent','sending')
                              AND (last_sent_at IS NULL OR last_sent_at<=?) RETURNING username,email''',
                           (digest, now + 172800, now, invitation_id, now - 60)).fetchone()
        if not row:
            raise ValueError('Convite indisponível ou envio recente. Aguarde um minuto antes de reenviar.')
        conn.commit()  # Persist before a non-transactional external effect.
    try:
        send_invitation_email(row['email'], token, invitation_id)
    except ValueError:
        with db.connection() as conn:
            conn.execute("UPDATE account_invitations SET status='failed',token_hash=NULL WHERE id=? AND token_hash=? AND status='sending'", (invitation_id, digest))
            conn.commit()
        raise
    with db.connection() as conn:
        changed = conn.execute("UPDATE account_invitations SET status='sent' WHERE id=? AND token_hash=? AND status='sending'", (invitation_id, digest))
        conn.execute('INSERT INTO activity_log(username,action,details) VALUES(?,?,?)',
                     (actor, 'convite_enviado', row['username']))
        conn.commit()
        if changed.rowcount != 1:
            raise ValueError('O convite foi cancelado durante o envio. O link não pode ser utilizado.')


def invitation_by_digest(digest):
    with db.connection() as conn:
        row = conn.execute('''SELECT i.*,u.name,COALESCE(ar.role,u.role) role FROM account_invitations i
                              JOIN users u ON u.username=i.username
                              LEFT JOIN account_roles ar ON ar.username=u.username
                              WHERE i.token_hash=? AND i.status='sent' AND i.expires_at>?''',
                           (digest, int(time.time()))).fetchone()
    return dict(row) if row else None


def complete_invitation(digest, password, confirmation):
    validate_password(password, confirmation)
    if not invitation_by_digest(digest):
        raise ValueError('Convite inválido, expirado ou já utilizado. Peça um novo convite à escola.')
    hashed_password = generate_password_hash(password)
    with db.connection() as conn:
        # Compare-and-swap is the serialization point: concurrent/replayed submissions fail.
        row = conn.execute('''UPDATE account_invitations SET status='used',used_at=?
                              WHERE token_hash=? AND status='sent' AND expires_at>?
                              RETURNING username,email''', (int(time.time()), digest, int(time.time()))).fetchone()
        if not row:
            raise ValueError('Convite inválido, expirado ou já utilizado. Peça um novo convite à escola.')
        identity = conn.execute('SELECT email,verified_at FROM account_identities WHERE username=?', (row['username'],)).fetchone()
        if not identity or identity['email'] != row['email'] or identity['verified_at']:
            conn.rollback()
            raise ValueError('O cadastro mudou. Peça um novo convite à escola.')
        conn.execute('UPDATE account_identities SET verified_at=? WHERE username=?', (int(time.time()), row['username']))
        conn.execute('UPDATE users SET active=TRUE,password_hash=? WHERE username=?', (hashed_password, row['username']))
        conn.execute('''INSERT INTO auth_versions(username,version) VALUES(?,1)
                        ON CONFLICT(username) DO UPDATE SET version=auth_versions.version+1''', (row['username'],))
        conn.execute('INSERT INTO activity_log(username,action,details) VALUES(?,?,?)',
                     (row['username'], 'conta_ativada', 'E-mail confirmado; sessões anteriores revogadas.'))
    return row['username']


def cancel_invitation(actor, invitation_id):
    with db.connection() as conn:
        row = conn.execute("UPDATE account_invitations SET status='revoked',token_hash=NULL WHERE id=? AND status!='used' RETURNING username", (invitation_id,)).fetchone()
        if not row:
            raise ValueError('Convite não encontrado ou já utilizado.')
        conn.execute('INSERT INTO activity_log(username,action,details) VALUES(?,?,?)', (actor, 'convite_cancelado', row['username']))


def invitation_directory():
    with db.connection() as conn:
        result = {r['username']: dict(r) for r in conn.execute('''SELECT ai.username,ai.email,ai.verified_at,
                  i.id,i.status,i.expires_at,i.last_sent_at FROM account_identities ai
                  LEFT JOIN account_invitations i ON i.username=ai.username''')}
    for row in result.values():
        if row['status'] == 'sent' and row['expires_at'] and row['expires_at'] <= int(time.time()):
            row['status'] = 'expired'  # Display only; the database still permits issuing a fresh token.
    return result


def login_identifier(value):
    identifier = value.strip().lower()
    if '@' not in identifier:
        return identifier
    with db.connection() as conn:
        row = conn.execute('SELECT username FROM account_identities WHERE email=? AND verified_at IS NOT NULL', (identifier,)).fetchone()
    return row['username'] if row else identifier


def consume_rate_limit(scope, identifier, *, limit=12):
    # HMAC avoids storing raw account identifiers or IPs in the limiter table.
    key = hmac.new(str(current_app.secret_key).encode(), (scope + ':' + identifier).encode(), hashlib.sha256).hexdigest()
    window = int(time.time()) // 900
    with db.connection() as conn:
        row = conn.execute('''INSERT INTO auth_rate_limits(key,bucket_window,attempts) VALUES(?,?,1)
                              ON CONFLICT(key,bucket_window) DO UPDATE SET attempts=auth_rate_limits.attempts+1
                              RETURNING attempts''', (key, window)).fetchone()
        conn.execute('DELETE FROM auth_rate_limits WHERE bucket_window<?', (window - 2,))
    return row['attempts'] <= limit


def retire_demos(actor, password):
    """Only an activated director can end demo access; academic records survive."""
    with db.connection() as conn:
        user = conn.execute('''SELECT u.password_hash,u.active,u.role,ai.verified_at FROM users u
                               JOIN account_identities ai ON ai.username=u.username WHERE u.username=?''', (actor,)).fetchone()
        if not user or not user['active'] or user['role'] != 'diretor' or not user['verified_at'] or not check_password_hash(user['password_hash'], password):
            raise ValueError('Ative sua conta de diretor por e-mail e confirme sua senha atual para encerrar as demonstrações.')
        for username in DEMO_USERS:
            identity = conn.execute('SELECT verified_at FROM account_identities WHERE username=?', (username,)).fetchone()
            if identity and identity['verified_at']:
                continue  # A former demo converted to a real account is no longer a demo.
            conn.execute('UPDATE users SET active=FALSE WHERE username=?', (username,))
            conn.execute("UPDATE account_invitations SET status='revoked',token_hash=NULL WHERE username=? AND status!='used'", (username,))
            conn.execute('''INSERT INTO auth_versions(username,version) SELECT username,1 FROM users WHERE username=?
                            ON CONFLICT(username) DO UPDATE SET version=auth_versions.version+1''', (username,))
        conn.execute("INSERT INTO enrollment_settings(key,value) VALUES('demos_disabled','1') ON CONFLICT(key) DO UPDATE SET value='1'")
        conn.execute('INSERT INTO activity_log(username,action,details) VALUES(?,?,?)',
                     (actor, 'demos_encerradas', 'Acessos não ativados encerrados; registros preservados.'))
