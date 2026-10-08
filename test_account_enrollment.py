import hashlib
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import database as db
import account_enrollment as enrollment
from app import app, ROSTER
from director import init_director, access_version


class EnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db_patch=patch.object(db,'DB_PATH',Path(self.temp.name)/'enrollment.db');self.db_patch.start()
        db.init_db();init_director()
        self.client=app.test_client();self.admin=app.test_client()
        with self.admin.session_transaction() as s:
            s.update(username='gilberto',role='admin',display_name='Direção',director_token='admin-csrf',auth_version=access_version('gilberto'))

    def tearDown(self):
        self.db_patch.stop();self.temp.cleanup()

    def draft(self,username='invited.teacher',email='teacher@example.com',role='professor',sid=None):
        return enrollment.create_invitation('gilberto',username,email,name='Pessoa Convidada',role=role,student_id=sid,roster=ROSTER)

    def delivered(self,username='invited.teacher',email='teacher@example.com',role='professor',sid=None):
        invitation_id=self.draft(username,email,role,sid)
        with patch.object(enrollment,'mail_configured',return_value=True),patch.object(enrollment,'send_invitation_email') as send:
            enrollment.deliver_invitation('gilberto',invitation_id)
        token=send.call_args.args[1]
        return invitation_id,token,hashlib.sha256(token.encode()).hexdigest()

    def csrf(self):
        self.client.get('/ativar')
        with self.client.session_transaction() as s:return s['enrollment_token']

    def test_draft_cannot_login_and_mail_absent_is_honest(self):
        with patch.object(enrollment,'mail_configured',return_value=False),patch.object(enrollment,'authorize_invitation_actor'):
            response=self.admin.post('/usuarios',data=dict(token='admin-csrf',action='invite',username='draft.teacher',name='Professor Real',role='professor',email='draft@example.com',current_password='direcao@123'),follow_redirects=True)
        self.assertEqual(response.status_code,200);self.assertIn('nenhum e-mail foi enviado'.encode(),response.data)
        self.assertIsNone(db.authenticate('draft.teacher','direcao@123'))
        row=enrollment.invitation_directory()['draft.teacher'];self.assertEqual(row['status'],'draft');self.assertFalse(row['verified_at'])
        self.assertEqual(self.admin.post('/usuarios',data=dict(token='admin-csrf',action='status',username='draft.teacher',active='1')).status_code,422)

    def test_full_activation_email_login_and_school_role_locked(self):
        _,token,digest=self.delivered();csrf=self.csrf()
        self.assertEqual(self.client.post('/ativar',data=dict(token=csrf,action='open',invitation=token)).status_code,302)
        self.assertIn(b'teacher@example.com',self.client.get('/ativar').data)
        password='Minha frase exclusiva 2026'
        response=self.client.post('/ativar',data=dict(token=csrf,action='complete',password=password,confirmation=password,role='diretor',student_id='23081'))
        self.assertEqual(response.status_code,302)
        with self.client.session_transaction() as s:self.assertNotIn('username',s)
        account=db.authenticate('teacher@example.com',password);self.assertEqual(account['username'],'invited.teacher');self.assertEqual(account['role'],'professor')
        self.client.get('/')
        with self.client.session_transaction() as s:login_token=s['login_token']
        response=self.client.post('/entrar',data=dict(token=login_token,usuario='TEACHER@EXAMPLE.COM',senha=password),headers={'X-Campus-Login':'1'})
        self.assertEqual(response.status_code,200)
        with self.client.session_transaction() as s:self.assertEqual(s['username'],'invited.teacher')
        self.assertEqual(self.client.get('/usuarios').status_code,403)
        with self.assertRaises(ValueError):enrollment.complete_invitation(digest,password,password)

    def test_token_is_hashed_and_not_in_admin_html_or_logs(self):
        invitation_id,token,digest=self.delivered()
        with db.connection() as conn:
            row=conn.execute('SELECT * FROM account_invitations WHERE id=?',(invitation_id,)).fetchone()
            self.assertEqual(row['token_hash'],digest);self.assertNotIn(token,str(dict(row)))
            self.assertFalse(any(token in str(dict(r)) for r in conn.execute('SELECT * FROM activity_log')))
        self.assertNotIn(token.encode(),self.admin.get('/usuarios').data)
        self.assertEqual(self.client.get('/ativar').headers['Referrer-Policy'],'no-referrer')

    def test_bad_password_does_not_consume(self):
        _,_,digest=self.delivered()
        for password,confirm in [('short','short'),('a long password phrase','a different phrase')]:
            with self.assertRaises(ValueError):enrollment.complete_invitation(digest,password,confirm)
            self.assertIsNotNone(enrollment.invitation_by_digest(digest))

    def test_expiry_and_account_block_cancel_activation(self):
        invitation_id,_,digest=self.delivered()
        with db.connection() as conn:conn.execute('UPDATE account_invitations SET expires_at=0 WHERE id=?',(invitation_id,))
        self.assertIsNone(enrollment.invitation_by_digest(digest))
        with self.assertRaises(ValueError):enrollment.complete_invitation(digest,'a long secure passphrase','a long secure passphrase')
        with db.connection() as conn:conn.execute('UPDATE account_invitations SET expires_at=? WHERE id=?',(int(time.time())+100,invitation_id))
        with patch.object(enrollment,'authorize_invitation_actor'):
            self.assertEqual(self.admin.post('/usuarios',data=dict(token='admin-csrf',action='status',username='invited.teacher',active='0')).status_code,302)
        self.assertIsNone(enrollment.invitation_by_digest(digest))

    def test_resend_rotates_token_and_enforces_cooldown(self):
        invitation_id,_,old_digest=self.delivered()
        with patch.object(enrollment,'mail_configured',return_value=True),patch.object(enrollment,'send_invitation_email') as sender:
            with self.assertRaises(ValueError):enrollment.deliver_invitation('gilberto',invitation_id)
            sender.assert_not_called()
            with db.connection() as conn:conn.execute('UPDATE account_invitations SET last_sent_at=0 WHERE id=?',(invitation_id,))
            enrollment.deliver_invitation('gilberto',invitation_id)
        self.assertIsNone(enrollment.invitation_by_digest(old_digest))
        self.assertIsNotNone(enrollment.invitation_by_digest(hashlib.sha256(sender.call_args.args[1].encode()).hexdigest()))

    def test_sender_failure_does_not_release_link(self):
        invitation_id=self.draft()
        with patch.object(enrollment,'mail_configured',return_value=True),patch.object(enrollment,'send_invitation_email',side_effect=ValueError('Envio indisponível')):
            with self.assertRaises(ValueError):enrollment.deliver_invitation('gilberto',invitation_id)
        with db.connection() as conn:
            row=conn.execute('SELECT status,token_hash FROM account_invitations WHERE id=?',(invitation_id,)).fetchone()
            self.assertEqual(row['status'],'failed');self.assertIsNone(row['token_hash'])

    def test_csrf_permissions_duplicates_and_legacy_create_rejected(self):
        self.assertEqual(self.client.post('/ativar',data=dict(action='open',invitation='x'*43)).status_code,400)
        self.assertEqual(self.admin.post('/usuarios',data=dict(action='invite')).status_code,400)
        self.assertEqual(self.admin.post('/usuarios',data=dict(token='admin-csrf',action='create',username='bad.user',password='public-pass')).status_code,422)
        with self.assertRaises(ValueError):self.draft(role='admin')
        self.draft()
        with self.assertRaises(ValueError):self.draft('another.teacher','teacher@example.com')
        with self.admin.session_transaction() as s:s.update(username='aline',role='professor',auth_version=access_version('aline'))
        self.assertEqual(self.admin.post('/usuarios',data=dict(token='admin-csrf',action='invite')).status_code,403)

    def test_guardian_link_and_student_uniqueness(self):
        _,_,digest=self.delivered('real.guardian','guardian@example.com','responsavel','23081')
        enrollment.complete_invitation(digest,'a very secure family phrase','a very secure family phrase')
        self.assertEqual(db.authenticate('guardian@example.com','a very secure family phrase')['role'],'responsavel')
        with db.connection() as conn:
            links=conn.execute('SELECT student_id FROM guardian_links WHERE guardian_username=?',('real.guardian',)).fetchall()
            self.assertEqual([r['student_id'] for r in links],['23081'])
        with self.assertRaises(ValueError):self.draft('another.thiago','another@example.com','aluno','23081')

    def test_demo_retirement_requires_activated_director_and_survives_restart(self):
        with self.assertRaises(ValueError):enrollment.retire_demos('gilberto','direcao@123')
        _,_,digest=self.delivered('real.director','director@example.com','diretor');password='a private director passphrase'
        enrollment.complete_invitation(digest,password,password)
        with self.assertRaises(ValueError):enrollment.retire_demos('real.director','incorrect')
        enrollment.retire_demos('real.director',password);self.assertFalse(enrollment.demos_enabled())
        db.init_db()
        self.assertIsNone(db.authenticate('gilberto','direcao@123'));self.assertIsNone(db.authenticate('responsavel.thiago','responsavel@123'))
        self.assertIsNotNone(db.authenticate('director@example.com',password))
        self.assertNotIn(b'data-demo-password',self.client.get('/').data)
        # Known demos cannot regain the old credential through the status endpoint.
        with self.admin.session_transaction() as s:
            s.update(username='real.director',role='admin',auth_version=access_version('real.director'),director_token='admin-csrf')
        self.assertEqual(self.admin.post('/usuarios',data=dict(token='admin-csrf',action='status',username='aline',active='1')).status_code,422)
        # They can still be migrated to a legitimate identity through a fresh invite.
        invitation_id=enrollment.create_invitation('real.director','aline','aline@example.com')
        with patch.object(enrollment,'mail_configured',return_value=True),patch.object(enrollment,'send_invitation_email') as sender:
            enrollment.deliver_invitation('real.director',invitation_id)
        digest=hashlib.sha256(sender.call_args.args[1].encode()).hexdigest()
        enrollment.complete_invitation(digest,'a personal teacher passphrase','a personal teacher passphrase')
        self.assertIsNone(db.authenticate('aline','professora@123'))
        self.assertEqual(db.authenticate('aline@example.com','a personal teacher passphrase')['role'],'professor')

    def test_existing_demo_conversion_preserves_role_and_revokes_sessions(self):
        _,_,digest=self.delivered('gilberto','gilberto@example.com')
        password='a new director private phrase';enrollment.complete_invitation(digest,password,password)
        self.assertEqual(self.admin.get('/usuarios').status_code,302)
        self.assertIsNone(db.authenticate('gilberto','direcao@123'))
        enrollment.retire_demos('gilberto',password)
        self.assertIsNotNone(db.authenticate('gilberto@example.com',password))

    def test_rate_limit_is_persistent_and_identifiers_are_private(self):
        with app.test_request_context('/'):
            for _ in range(3):self.assertTrue(enrollment.consume_rate_limit('test','secret@example.com',limit=3))
        with app.test_request_context('/'):
            self.assertFalse(enrollment.consume_rate_limit('test','secret@example.com',limit=3))
        with db.connection() as conn:
            self.assertTrue(all('secret@example.com' not in r['key'] for r in conn.execute('SELECT * FROM auth_rate_limits')))

    def test_https_mail_transport_and_fragment_link(self):
        values=dict(FAEHUB_PUBLIC_URL='https://school.example.com',FAEHUB_MAIL_FROM='School <access@example.com>',FAEHUB_RESEND_API_KEY='fake-test-only')
        response=MagicMock();response.__enter__.return_value.read.return_value=b'{"id":"test-message-id"}'
        with patch.dict(os.environ,values),patch.object(enrollment,'urlopen',return_value=response) as transport:
            self.assertTrue(enrollment.mail_configured())
            enrollment.send_invitation_email('teacher@example.com','fake-bearer','fake-invitation')
        req=transport.call_args.args[0]
        self.assertEqual(req.full_url,'https://api.resend.com/emails')
        payload=json.loads(req.data)
        self.assertEqual(payload['to'],['teacher@example.com'])
        self.assertIn('https://school.example.com/ativar#convite=fake-bearer',payload['text'])
        self.assertEqual(transport.call_args.kwargs['timeout'],10)
        with patch.dict(os.environ,{**values,'FAEHUB_PUBLIC_URL':'http://untrusted.example.com'}):
            self.assertFalse(enrollment.mail_configured())

    def test_demo_director_cannot_grant_access_until_private_bootstrap(self):
        data=dict(token='admin-csrf',action='invite',username='attacker.director',name='Unauthorized',role='diretor',email='attacker@example.com',current_password='direcao@123')
        with patch.dict(os.environ,{'FAEHUB_BOOTSTRAP_ADMIN_EMAIL':'owner@example.com'}),patch.object(enrollment,'mail_configured',return_value=False):
            self.assertEqual(self.admin.post('/usuarios',data=data).status_code,422)
            data['username']='gilberto'
            self.assertEqual(self.admin.post('/usuarios',data=data).status_code,422)
            data['email']='owner@example.com'
            self.assertEqual(self.admin.post('/usuarios',data=data).status_code,302)
            self.assertEqual(self.admin.post('/usuarios',data=dict(token='admin-csrf',action='password',username='aline',password='a malicious new password')).status_code,422)
        with db.connection() as conn:
            self.assertIsNone(conn.execute("SELECT 1 FROM users WHERE username='attacker.director'").fetchone())
        invitation_id=enrollment.invitation_directory()['gilberto']['id']
        with patch.object(enrollment,'mail_configured',return_value=True),patch.object(enrollment,'send_invitation_email') as sender:
            enrollment.deliver_invitation('gilberto',invitation_id)
        password='a private verified director phrase'
        enrollment.complete_invitation(hashlib.sha256(sender.call_args.args[1].encode()).hexdigest(),password,password)
        with self.admin.session_transaction() as s:s['auth_version']=access_version('gilberto')
        data.update(username='real.newteacher',role='professor',name='Professor',email='teacher2@example.com',current_password=password)
        with patch.object(enrollment,'mail_configured',return_value=False):
            self.assertEqual(self.admin.post('/usuarios',data=data).status_code,302)

    def test_recovery_uses_verified_email_without_reducing_password_policy(self):
        import p1_operations as operations
        _,_,digest=self.delivered();enrollment.complete_invitation(digest,'a secure starting phrase','a secure starting phrase')
        username=enrollment.login_identifier('TEACHER@EXAMPLE.COM')
        self.assertEqual(username,'invited.teacher')
        operations.request_password_recovery(username)
        request_id=operations.list_recovery_requests()[0]['id']
        code=operations.issue_recovery_code(request_id,'gilberto')
        with self.assertRaises(ValueError):operations.use_recovery_code(username,code,'short-pass123')
        operations.use_recovery_code(username,code,'a new secure recovered phrase')
        self.assertIsNotNone(db.authenticate('teacher@example.com','a new secure recovered phrase'))


if __name__=='__main__':unittest.main()
