"""Self-service recovery, exclusively through the verified mailbox."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app
from werkzeug.security import generate_password_hash
import database as db
import account_enrollment as enrollment

NEUTRAL = 'Se este e-mail estiver confirmado em uma conta ativa, você receberá as instruções. Confira também o spam.'


def verified_account(conn, email):
    return conn.execute('''SELECT u.username FROM users u
        JOIN account_identities ai ON ai.username=u.username
        WHERE ai.email=? AND ai.verified_at IS NOT NULL AND ai.verified_at<>0 AND u.active=TRUE''', (email,)).fetchone()


def request_recovery(email, purpose, remote):
    email = enrollment.normalize_email(email)
    if purpose not in ('password', 'username'):
        raise ValueError('Escolha recuperar a senha ou o usuário.')
    if not enrollment.consume_rate_limit('recovery-mail-ip', remote, limit=10):
        raise ValueError('Muitas solicitações. Aguarde 15 minutos para tentar novamente.')
    if not enrollment.consume_rate_limit('recovery-mail-' + purpose, email, limit=3):
        return NEUTRAL
    if not enrollment.mail_configured():
        raise ValueError('O envio de e-mails está indisponível. Tente novamente mais tarde.')
    with db.connection() as conn:
        account = verified_account(conn, email)
        if not account:
            return NEUTRAL
        username = account['username']
        code = secrets.token_urlsafe(24) if purpose == 'password' else None
        digest = hashlib.sha256(code.encode()).hexdigest() if code else secrets.token_hex(32)
        if code:
            # Not usable until the mail provider accepts delivery.
            row = conn.execute('''INSERT INTO password_recovery_requests(username,token_hash,status,expires_at)
                VALUES(?,?,'expired',?) RETURNING id''',
                (username, digest, (datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat())).fetchone()
            request_id = row['id']
    subject = 'Redefina sua senha do FaeHub+' if code else 'Seu usuário do FaeHub+'
    text = ('Use este código no FaeHub+ para criar uma nova senha: ' + code +
            '\nVálido por 30 minutos e uma única utilização. O autenticador continua ativo.' if code else
            'Seu usuário do FaeHub+ é: ' + username + '\nVocê também pode entrar com seu e-mail confirmado.')
    text += '\n\nSe não solicitou esta mensagem, ignore. Nunca compartilhe códigos ou senhas.'
    html = current_app.jinja_env.get_template('emails/recovery.html').render(code=code, username=None if code else username)
    enrollment.send_account_email(email, subject, text, html, 'recovery-' + digest)
    if code:
        with db.connection() as conn:
            current = verified_account(conn, email)
            if not current or current['username'] != username:
                return NEUTRAL
            conn.execute("UPDATE password_recovery_requests SET status='expired' WHERE username=? AND status='issued'", (username,))
            conn.execute("UPDATE password_recovery_requests SET status='issued' WHERE id=? AND status='expired'", (request_id,))
    return NEUTRAL


def reset_password(email, code, password, confirmation, remote):
    email = enrollment.normalize_email(email)
    if not enrollment.consume_rate_limit('recovery-reset-ip', remote, limit=30):
        raise ValueError('Muitas tentativas. Aguarde 15 minutos.')
    if not enrollment.consume_rate_limit('recovery-reset', email, limit=5):
        raise ValueError('Muitas tentativas. Aguarde 15 minutos.')
    enrollment.validate_password(password, confirmation)
    if not 1 <= len(code) <= 128:
        raise ValueError('Código inválido ou expirado. Solicite um novo código por e-mail.')
    digest = hashlib.sha256(code.strip().encode()).hexdigest()
    with db.connection() as conn:
        account = verified_account(conn, email)
        row = conn.execute('''UPDATE password_recovery_requests SET status='used',used_at=CURRENT_TIMESTAMP
            WHERE username=? AND token_hash=? AND status='issued' AND issued_by IS NULL AND expires_at>=?
            RETURNING id''', (account['username'] if account else '', digest, datetime.now(timezone.utc).isoformat())).fetchone()
        if not row:
            raise ValueError('Código inválido ou expirado. Solicite um novo código por e-mail.')
        username = account['username']
        conn.execute('UPDATE users SET password_hash=? WHERE username=?', (generate_password_hash(password), username))
        conn.execute('''INSERT INTO auth_versions(username,version) VALUES(?,1)
            ON CONFLICT(username) DO UPDATE SET version=auth_versions.version+1''', (username,))
        conn.execute("UPDATE password_recovery_requests SET status='expired' WHERE username=? AND status IN ('requested','issued')", (username,))
        # MFA configuration/recovery codes and school permissions are untouched.
