"""Private, fixed-client authorization-code bridge. No password leaves FaeHub."""
import base64
import hashlib
import os
import re
import secrets
import time
import uuid
from urllib.parse import urlencode

import database as db

CALLBACK = 'https://faenet.onrender.com/auth/faehub/callback'
ISSUER = 'https://faehub-plus.onrender.com'
DDL = '''
CREATE TABLE IF NOT EXISTS faenet_subjects (
 username TEXT PRIMARY KEY REFERENCES users(username), subject TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS faenet_grants (
 code_hash TEXT PRIMARY KEY, username TEXT NOT NULL REFERENCES users(username),
 auth_version BIGINT NOT NULL, challenge TEXT NOT NULL, expires_at BIGINT NOT NULL,
 token_hash TEXT UNIQUE, token_expires_at BIGINT);
'''


def init_sso():
    if not db.using_postgres():
        with db.connection() as conn:
            conn.executescript(DDL)


def configured():
    return len(os.getenv('FAEHUB_FAENET_CLIENT_SECRET', '')) >= 43


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def challenge(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()


def validate_authorization(args):
    if (args.get('client_id') != 'faenet' or args.get('redirect_uri') != CALLBACK
            or args.get('response_type') != 'code' or args.get('code_challenge_method') != 'S256'
            or not re.fullmatch(r'[A-Za-z0-9_-]{43}', args.get('code_challenge', ''))
            or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', args.get('state', ''))):
        raise ValueError('Pedido de acesso inválido. Reabra a FaeNet para tentar novamente.')
    return {k: args[k] for k in ('client_id', 'redirect_uri', 'response_type',
                                'code_challenge_method', 'code_challenge', 'state')}


def client_authenticated(header):
    expected = os.getenv('FAEHUB_FAENET_CLIENT_SECRET', '')
    return configured() and secrets.compare_digest(header, 'Bearer ' + expected)


def identity(conn, username, version):
    from director import account_access
    access = account_access(username)
    if not access or not access['active'] or access['auth_version'] != version:
        return None
    # Invitations must have been completed. Known-password demos are not identities.
    row = conn.execute('''SELECT u.name FROM users u JOIN account_identities ai ON ai.username=u.username
        WHERE u.username=? AND ai.verified_at IS NOT NULL AND ai.verified_at<>0''', (username,)).fetchone()
    if not row or access['role'] not in ('aluno', 'professor', 'diretor', 'responsavel'):
        return None
    subject_row = conn.execute('SELECT subject FROM faenet_subjects WHERE username=?', (username,)).fetchone()
    if not subject_row:
        conn.execute('INSERT INTO faenet_subjects(username,subject) VALUES(?,?) ON CONFLICT(username) DO NOTHING',
                     (username, str(uuid.uuid4())))
        subject_row = conn.execute('SELECT subject FROM faenet_subjects WHERE username=?', (username,)).fetchone()
    subject = subject_row['subject']
    return dict(sub=subject, name=row['name'], role=access['role'], owner=access['is_owner'],
                iss=ISSUER, aud='faenet')


def issue(username, version, args):
    code = secrets.token_urlsafe(32)
    with db.connection() as conn:
        if not identity(conn, username, version):
            raise ValueError('Ative sua conta pelo convite da escola antes de acessar a FaeNet.')
        conn.execute('''INSERT INTO faenet_grants(code_hash,username,auth_version,challenge,expires_at)
            VALUES(?,?,?,?,?)''', (digest(code), username, version, args['code_challenge'], int(time.time()) + 60))
    return CALLBACK + '?' + urlencode(dict(code=code, state=args['state'], iss=ISSUER))


def exchange(data):
    code, verifier = data.get('code', ''), data.get('code_verifier', '')
    if (data.get('grant_type') != 'authorization_code' or data.get('redirect_uri') != CALLBACK
            or not re.fullmatch(r'[A-Za-z0-9_-]{43}', code)
            or not re.fullmatch(r'[A-Za-z0-9._~-]{43,128}', verifier)):
        raise ValueError('Confirmação inválida ou expirada.')
    token = secrets.token_urlsafe(32)
    with db.connection() as conn:
        row = conn.execute('SELECT * FROM faenet_grants WHERE code_hash=?', (digest(code),)).fetchone()
        if not row or row['expires_at'] <= time.time() or not secrets.compare_digest(row['challenge'], challenge(verifier)):
            raise ValueError('Confirmação inválida ou expirada.')
        profile = identity(conn, row['username'], row['auth_version'])
        if not profile:
            raise ValueError('Acesso não autorizado pelo FaeHub.')
        changed = conn.execute('''UPDATE faenet_grants SET token_hash=?,token_expires_at=?
            WHERE code_hash=? AND token_hash IS NULL AND expires_at>?''',
            (digest(token), int(time.time()) + 43200, digest(code), int(time.time())))
        if changed.rowcount != 1:
            raise ValueError('Confirmação inválida ou já utilizada.')
    return dict(access_token=token, token_type='Bearer', expires_in=43200, profile=profile)


def introspect(token):
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        return dict(active=False)
    with db.connection() as conn:
        row = conn.execute('SELECT username,auth_version FROM faenet_grants WHERE token_hash=? AND token_expires_at>?',
                           (digest(token), int(time.time()))).fetchone()
        profile = identity(conn, row['username'], row['auth_version']) if row else None
        return dict(active=True, profile=profile) if profile else dict(active=False)
