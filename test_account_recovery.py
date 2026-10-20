import hashlib
import unittest
from unittest.mock import patch
import account_enrollment as enrollment
import account_recovery as recovery
import database as db
import p1_operations as operations
from app import app
import test_faenet_sso as fixtures


class EmailRecoveryTests(unittest.TestCase):
    setUpClass=classmethod(fixtures.FaeNetSsoTests.setUpClass.__func__)
    tearDownClass=classmethod(fixtures.FaeNetSsoTests.tearDownClass.__func__)
    setUp=fixtures.FaeNetSsoTests.setUp
    login=fixtures.FaeNetSsoTests.login
    grant=fixtures.FaeNetSsoTests.grant
    exchange=fixtures.FaeNetSsoTests.exchange
    def request_mail(self, purpose='password', email='fixture@example.com'):
        with app.app_context(), patch.object(enrollment,'mail_configured',return_value=True), patch.object(enrollment,'send_account_email') as sender:
            message=recovery.request_recovery(email,purpose,'fixture-ip')
        return message,sender

    def test_email_only_password_one_use_revokes_social_and_preserves_mfa(self):
        token=self.exchange(self.grant()).json['access_token']
        with db.connection() as conn:conn.execute("INSERT INTO account_mfa(username,enabled) VALUES('thiago.zotti',TRUE)")
        message,sender=self.request_mail()
        code=sender.call_args.args[2].split(': ',1)[1].split('\n',1)[0]
        self.assertNotIn(code,message)
        with db.connection() as conn:
            row=conn.execute('SELECT * FROM password_recovery_requests').fetchone()
            self.assertEqual(row['token_hash'],hashlib.sha256(code.encode()).hexdigest())
            self.assertIsNone(row['issued_by'])
        with app.app_context():
            recovery.reset_password('FIXTURE@example.com',code,'Pass123!','Pass123!','fixture-ip')
            with self.assertRaises(ValueError):recovery.reset_password('fixture@example.com',code,'NewPass!','NewPass!','fixture-ip')
        self.assertIsNotNone(db.authenticate('fixture@example.com','Pass123!'))
        self.assertFalse(self.client.post('/sso/faenet/introspect',data=dict(token=token),headers=self.headers).json['active'])
        with db.connection() as conn:self.assertTrue(conn.execute("SELECT enabled FROM account_mfa WHERE username='thiago.zotti'").fetchone()['enabled'])

    def test_username_sent_only_to_verified_mailbox_neutral_public_response(self):
        message,sender=self.request_mail('username')
        self.assertEqual(message,recovery.NEUTRAL);self.assertIn('thiago.zotti',sender.call_args.args[2])
        unknown,none=self.request_mail('username','unknown@example.com')
        self.assertEqual(unknown,message);none.assert_not_called()
        with db.connection() as conn:conn.execute("UPDATE users SET active=FALSE WHERE username='thiago.zotti'")
        _,none=self.request_mail();none.assert_not_called()

    def test_mail_failure_expiry_and_direction_cannot_override_verified_identity(self):
        with app.app_context(),patch.object(enrollment,'mail_configured',return_value=True),patch.object(enrollment,'send_account_email',side_effect=ValueError('mail unavailable')):
            with self.assertRaises(ValueError):recovery.request_recovery('fixture@example.com','password','fixture-ip')
        with db.connection() as conn:
            row=conn.execute('SELECT * FROM password_recovery_requests').fetchone()
            self.assertEqual(row['status'],'expired')
            conn.execute("UPDATE password_recovery_requests SET status='requested' WHERE id=?",(row['id'],))
        with self.assertRaises(ValueError):operations.issue_recovery_code(row['id'],'gilberto')
        _,sender=self.request_mail();code=sender.call_args.args[2].split(': ',1)[1].split('\n',1)[0]
        with db.connection() as conn:conn.execute("UPDATE password_recovery_requests SET expires_at='2000-01-01' WHERE status='issued'")
        with app.app_context(),self.assertRaises(ValueError):recovery.reset_password('fixture@example.com',code,'Pass123!','Pass123!','fixture-ip')

    def test_public_route_rejects_username_and_requires_csrf(self):
        self.client.get('/recuperar-senha')
        with self.client.session_transaction() as session:csrf=session['recovery_token']
        self.assertEqual(self.client.post('/recuperar-senha',data=dict(action='request',email='fixture@example.com')).status_code,400)
        result=self.client.post('/recuperar-senha',data=dict(token=csrf,action='request',email='thiago.zotti'))
        self.assertEqual(result.status_code,422);self.assertIn(b'no-store',result.headers['Cache-Control'].encode())
        self.assertNotIn(b'Emitir c',result.data)

    def test_resend_rotates_and_failed_attempts_are_limited(self):
        _,first=self.request_mail();code1=first.call_args.args[2].split(': ',1)[1].split('\n',1)[0]
        _,second=self.request_mail();code2=second.call_args.args[2].split(': ',1)[1].split('\n',1)[0]
        self.assertNotEqual(code1,code2)
        with app.app_context():
            with self.assertRaises(ValueError):recovery.reset_password('fixture@example.com',code1,'Pass123!','Pass123!','fixture-ip')
            for _ in range(4):
                with self.assertRaises(ValueError):recovery.reset_password('fixture@example.com','wrong','Pass123!','Pass123!','fixture-ip')
            with self.assertRaisesRegex(ValueError,'Muitas tentativas'):recovery.reset_password('fixture@example.com',code2,'Pass123!','Pass123!','fixture-ip')
