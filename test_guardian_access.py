import hashlib
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import account_enrollment as enrollment
import account_recovery
import database as db
import faenet_sso
from app import app
from director import access_version, init_director


class GuardianAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temp.cleanup)
        override = patch.object(db, 'DB_PATH', Path(temp.name) / 'profiles.db')
        override.start()
        cls.addClassCleanup(override.stop)
        db.init_db()
        init_director()
        with db.connection() as conn:
            conn.execute("INSERT INTO account_identities(username,email,verified_at) VALUES('responsavel.thiago','family@example.com',1)")

    def test_guardian_login_and_recovery_are_blocked_without_deleting_account(self):
        client = app.test_client()
        html = client.get('/').get_data(as_text=True)
        self.assertNotIn('data-role="responsavel"', html)
        for role in ('aluno', 'professor', 'diretor'):
            self.assertIn(f'data-role="{role}"', html)
        with client.session_transaction() as session:
            token = session['login_token']
        for alias in ('responsavel.thiago', 'family@example.com'):
            response = client.post('/entrar', data=dict(token=token, usuario=alias, senha='responsavel@123', role='aluno'),
                                   headers={'X-Campus-Login': '1'})
            self.assertEqual(response.status_code, 401)
        with db.connection() as conn:
            self.assertTrue(conn.execute("SELECT active FROM users WHERE username='responsavel.thiago'").fetchone()['active'])
            self.assertIsNotNone(conn.execute("SELECT 1 FROM guardian_links WHERE guardian_username='responsavel.thiago'").fetchone())
            self.assertIsNone(account_recovery.verified_account(conn, 'family@example.com'))
            self.assertIsNone(faenet_sso.identity(conn, 'responsavel.thiago', access_version('responsavel.thiago')))

    def test_existing_sessions_and_pending_mfa_are_rejected(self):
        for path in ('/painel', '/secretaria', '/faenet', '/api/mensagens/estado'):
            client = app.test_client()
            with client.session_transaction() as session:
                session.update(username='responsavel.thiago', role='responsavel',
                               auth_version=access_version('responsavel.thiago'), mfa_verified=True)
            self.assertEqual(client.get(path).location, '/')
            with client.session_transaction() as session:
                self.assertNotIn('username', session)
        with db.connection() as conn:
            conn.execute("INSERT INTO account_mfa(username,enabled) VALUES('responsavel.thiago',TRUE)")
        self.addCleanup(self.clear_mfa_fixture)
        with client.session_transaction() as session:
            session.update(mfa_pending_user='responsavel.thiago', mfa_pending_until=int(time.time()) + 300,
                           mfa_pending_version=access_version('responsavel.thiago'))
        self.assertEqual(client.get('/entrar/autenticador').location, '/')

    @staticmethod
    def clear_mfa_fixture():
        with db.connection() as conn:
            conn.execute("DELETE FROM account_mfa WHERE username='responsavel.thiago'")

    def test_invitation_cannot_create_or_activate_hidden_role(self):
        with self.assertRaisesRegex(ValueError, 'perfil está indisponível'):
            enrollment.create_invitation('gilberto', 'new.guardian', 'new@example.com',
                                         name='Pessoa Exemplo', role='responsavel')
        digest = hashlib.sha256(b'old-guardian-invitation').hexdigest()
        with db.connection() as conn:
            conn.execute("""INSERT INTO account_invitations(id,username,email,created_by,created_at,
                         token_hash,expires_at,status) VALUES(?,?,?,?,?,?,?,'sent')""",
                         ('old-guardian', 'responsavel.thiago', 'family@example.com', 'gilberto',
                          int(time.time()), digest, int(time.time()) + 300))
        self.assertIsNone(enrollment.invitation_by_digest(digest))

    def test_directory_does_not_offer_hidden_role(self):
        client = app.test_client()
        with client.session_transaction() as session:
            session.update(username='gilberto', role='admin', auth_version=access_version('gilberto'))
        for path in ('/usuarios', '/calendario', '/notificacoes'):
            response = client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(b'value="responsavel"', response.data)
            self.assertNotIn(b'responsavel.thiago', response.data)
