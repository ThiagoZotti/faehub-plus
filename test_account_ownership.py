import hashlib
import re
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import database as db
import account_enrollment as enrollment
import account_ownership as ownership
import p1_operations as operations
from app import app, ROSTER
from director import account_access, access_version, init_director


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(db, 'DB_PATH', Path(self.temp.name) / 'owner.db')
        self.db_patch.start()
        db.init_db()
        init_director()
        db.create_user('school.director', 'Diretor com senha pessoal', 'Diretor da escola', 'diretor')
        with db.connection() as conn:
            conn.executemany('INSERT INTO enrollment_settings(key,value) VALUES(?,?)', [
                ('system_owner_username', 'gilberto'), ('system_owner_email', 'owner@example.com'),
                ('bootstrap_admin_email', 'owner@example.com')])
            conn.execute("INSERT INTO account_identities VALUES('gilberto','owner@example.com',NULL)")
            conn.execute("INSERT INTO account_identities VALUES('school.director','director@example.com',?)", (int(time.time()),))
        self.owner = self.client('gilberto')
        self.director = self.client('school.director')

    def tearDown(self):
        self.db_patch.stop()
        self.temp.cleanup()

    def client(self, username):
        client = app.test_client()
        with client.session_transaction() as session:
            session.update(username=username, role='admin', display_name='Gestão',
                           director_token='csrf', auth_version=access_version(username))
        return client

    def draft(self):
        return enrollment.create_invitation('gilberto', 'gilberto', 'owner@example.com')

    def test_director_cannot_mutate_owner_via_any_account_action(self):
        invitation_id = self.draft()
        actions = [dict(action='update', name='Invadido'), dict(action='status', active='0'),
                   dict(action='password', password='Senha roubada longa'),
                   dict(action='invite', email='attacker@example.com', current_password='Diretor com senha pessoal'),
                   dict(action='send_invite', invitation_id=invitation_id),
                   dict(action='cancel_invite', invitation_id=invitation_id)]
        for action in actions:
            with self.subTest(action=action['action']):
                response = self.director.post('/usuarios', data=dict(token='csrf', username='gilberto', **action))
                self.assertEqual(response.status_code, 422)
                self.assertIn('proprietário'.encode(), response.data)
        self.assertEqual(enrollment.invitation_directory()['gilberto']['email'], 'owner@example.com')
        self.assertEqual(enrollment.invitation_directory()['gilberto']['status'], 'draft')
        self.assertTrue(db.authenticate('gilberto', 'direcao@123'))

    def test_service_and_legacy_mutations_protect_owner(self):
        invitation_id = self.draft()
        with self.assertRaises(ValueError):
            enrollment.create_invitation('school.director', 'gilberto', 'owner@example.com')
        with patch.object(enrollment, 'mail_configured', return_value=True), patch.object(enrollment, 'send_invitation_email') as send:
            with self.assertRaises(ValueError):
                enrollment.deliver_invitation('school.director', invitation_id)
            send.assert_not_called()
        with self.assertRaises(ValueError):
            enrollment.cancel_invitation('school.director', invitation_id)
        with self.assertRaises(ValueError):
            db.toggle_user('gilberto')
        self.assertEqual(self.director.post('/usuarios/gilberto/alternar').status_code, 400)

    def test_pending_owner_cannot_gain_authority_or_change_pinned_email(self):
        self.assertFalse(account_access('gilberto')['is_owner'])
        with self.owner.session_transaction() as session:
            session['is_owner'] = True  # Even signed stale metadata isn't authority.
        with self.assertRaises(ValueError):
            enrollment.create_invitation('gilberto', 'gilberto', 'attacker@example.com')
        with self.assertRaises(ValueError):
            enrollment.authorize_invitation_actor('gilberto', 'invite', username='other', email='other@example.com')
        response = self.owner.post('/usuarios', data=dict(token='csrf', action='update', username='gilberto', name='Alterado'))
        self.assertEqual(response.status_code, 422)
        self.assertIn('Propriedade pendente'.encode(), self.owner.get('/usuarios').data)

    def test_owner_activation_without_matricula_revokes_old_session(self):
        invitation_id = self.draft()
        with patch.object(enrollment, 'mail_configured', return_value=True), patch.object(enrollment, 'send_invitation_email') as send:
            enrollment.deliver_invitation('gilberto', invitation_id)
        digest = hashlib.sha256(send.call_args.args[1].encode()).hexdigest()
        self.assertEqual(enrollment.invitation_by_digest(digest)['role'], 'proprietario')
        password = 'Minha propriedade segura 2026'
        enrollment.complete_invitation(digest, password, password)
        self.assertTrue(account_access('gilberto')['is_owner'])
        self.assertIsNone(db.authenticate('owner@example.com', password)['student_id'])
        self.assertEqual(self.owner.get('/usuarios').status_code, 302)
        self.owner = self.client('gilberto')
        self.assertIn('Proprietário do sistema'.encode(), self.owner.get('/painel').data)
        self.assertEqual(self.owner.post('/usuarios', data=dict(token='csrf', action='update', username='gilberto', name='Proprietário')).status_code, 302)
        # Owner inherits institution management, including ordinary directors.
        self.assertEqual(self.owner.post('/usuarios', data=dict(token='csrf', action='status', username='school.director', active='0')).status_code, 302)
        with self.assertRaises(ValueError):
            enrollment.complete_invitation(digest, password, password)

    def test_legacy_recovery_cannot_take_over_owner(self):
        operations.request_password_recovery('gilberto')
        with db.connection() as conn:
            self.assertIsNone(conn.execute("SELECT id FROM password_recovery_requests WHERE username='gilberto'").fetchone())
            request_id = conn.execute("INSERT INTO password_recovery_requests(username) VALUES('gilberto') RETURNING id").fetchone()['id']
        with self.assertRaises(ValueError):
            operations.issue_recovery_code(request_id, 'school.director')
        with db.connection() as conn:
            conn.execute("UPDATE password_recovery_requests SET status='issued',token_hash=?,expires_at='2099-01-01T00:00:00+00:00' WHERE id=?", (hashlib.sha256(b'old-code').hexdigest(), request_id))
        with self.assertRaises(ValueError):
            operations.use_recovery_code('gilberto', 'old-code', 'Tentativa de senha roubada')
        self.assertTrue(db.authenticate('gilberto', 'direcao@123'))

    def test_demos_retirement_preserves_pending_owner(self):
        enrollment.retire_demos('school.director', 'Diretor com senha pessoal')
        self.assertTrue(account_access('gilberto')['active'])
        self.assertFalse(account_access('gilberto')['is_owner'])
        self.assertFalse(account_access('aline')['active'])

    def test_owner_cannot_be_created_or_selected_by_directors(self):
        with self.assertRaises(ValueError):
            enrollment.create_invitation('school.director', 'forged.owner', 'forged@example.com', name='Forjado', role='proprietario', roster=ROSTER)
        html = self.director.get('/usuarios').get_data(as_text=True)
        role_select = re.search(r'<select[^>]*id="identityRole"[^>]*>(.*?)</select>', html, re.S).group(1)
        self.assertNotIn('value="proprietario"', role_select)
        protected_dialog = next(dialog for dialog in re.findall(r'<dialog\b.*?</dialog>', html, re.S)
                                if 'GILBERTO / PROPRIETÁRIO' in dialog.upper())
        self.assertNotIn('<form', protected_dialog)
        self.assertIn('Responsável pelo aluno', html)

    def test_mismatched_owner_invitation_and_verified_identity_fail_closed(self):
        invitation_id = self.draft()
        with db.connection() as conn:
            conn.execute("UPDATE account_invitations SET email='wrong@example.com',status='sent',token_hash='obsolete',expires_at=? WHERE id=?", (int(time.time()) + 600, invitation_id))
            conn.execute("UPDATE account_identities SET email='wrong@example.com',verified_at=? WHERE username='gilberto'", (int(time.time()),))
        self.assertFalse(account_access('gilberto')['is_owner'])
        self.assertIsNone(enrollment.invitation_by_digest('obsolete'))
        with self.assertRaises(ValueError):
            enrollment.complete_invitation('obsolete', 'Frase segura e muito longa', 'Frase segura e muito longa')
