import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet
import pyotp
import account_mfa as mfa
import database as db
from app import app
from director import access_version,init_director


class MfaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.base=Path(cls.temp.name)/'base.db'
        with patch.object(db,'DB_PATH',cls.base):
            db.init_db();init_director()
            with db.connection() as conn:
                conn.execute("INSERT INTO account_identities(username,email,verified_at) VALUES('thiago.zotti','person@example.com',1) ON CONFLICT(username) DO UPDATE SET verified_at=1")

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.path=Path(self.temp.name)/'case.db';shutil.copyfile(self.base,self.path)
        self.db_patch=patch.object(db,'DB_PATH',self.path);self.db_patch.start()
        self.keys=patch.dict(os.environ,{'FAEHUB_MFA_ENCRYPTION_KEY':Fernet.generate_key().decode()});self.keys.start()
        self.clock=patch('account_mfa.time.time',return_value=1900000000);self.time_mock=self.clock.start()
        self.client=app.test_client();self.username='thiago.zotti';self.password='aluno@123'

    def tearDown(self):self.clock.stop();self.keys.stop();self.db_patch.stop()

    def activate(self):
        mfa.begin(self.username,self.password);self.secret=mfa.pending(self.username)
        return mfa.activate(self.username,pyotp.TOTP(self.secret).at(1900000000))

    def login(self):
        self.client.get('/')
        with self.client.session_transaction() as s:token=s['login_token']
        return self.client.post('/entrar',data=dict(token=token,usuario=self.username,senha=self.password),headers={'X-Campus-Login':'1'})

    def test_requires_password_verified_identity_and_key(self):
        for username,password in ((self.username,'bad'),('aline','professora@123')):
            with self.assertRaises(ValueError):mfa.begin(username,password)
        with patch.dict(os.environ,{'FAEHUB_MFA_ENCRYPTION_KEY':''}):
            self.assertFalse(mfa.configured())
            with self.assertRaises(ValueError):mfa.begin(self.username,self.password)
        self.assertFalse(mfa.enabled(self.username))

    def test_setup_not_active_until_verified_and_no_plaintext_at_rest(self):
        mfa.begin(self.username,self.password);secret=mfa.pending(self.username)
        self.assertFalse(mfa.enabled(self.username))
        with self.assertRaises(ValueError):mfa.activate(self.username,'not-code')
        codes=mfa.activate(self.username,pyotp.TOTP(secret).at(1900000000))
        self.assertEqual(len(codes),10);self.assertTrue(mfa.enabled(self.username))
        with db.connection() as conn:
            self.assertNotIn(secret,str(dict(conn.execute('SELECT * FROM account_mfa').fetchone())))
            self.assertNotIn(codes[0],str([dict(r) for r in conn.execute('SELECT * FROM mfa_recovery_codes')]))
        self.assertFalse(mfa.verify(self.username,pyotp.TOTP(secret).at(1900000000)))

    def test_login_cannot_access_any_page_before_second_factor(self):
        self.activate();result=self.login();self.assertTrue(result.json['mfa_required'])
        with self.client.session_transaction() as s:
            self.assertNotIn('role',s);token=s['mfa_token']
        self.assertEqual(self.client.get('/painel').status_code,302)
        self.assertEqual(self.client.post('/entrar/autenticador',data=dict(token='bad',code='123456')).status_code,400)
        self.time_mock.return_value=1900000030
        response=self.client.post('/entrar/autenticador',data=dict(token=token,code=pyotp.TOTP(self.secret).at(1900000030)))
        self.assertEqual(response.status_code,200);self.assertIn(b'Entrar no campus',response.data)
        self.assertEqual(self.client.get('/painel').status_code,200)

    def test_single_use_recovery_can_disable_lost_authenticator(self):
        codes=self.activate()
        self.assertTrue(mfa.verify(self.username,codes[0],recovery=True))
        self.assertFalse(mfa.verify(self.username,codes[0],recovery=True))
        mfa.manage(self.username,self.password,codes[1],'disable',recovery=True)
        self.assertFalse(mfa.enabled(self.username));self.assertFalse(mfa.verify(self.username,codes[2],True))

    def test_expired_pending_changed_version_and_revoked_session(self):
        codes=self.activate();self.login()
        with self.client.session_transaction() as s:token=s['mfa_token']
        with db.connection() as conn:conn.execute('UPDATE auth_versions SET version=version+1 WHERE username=?',(self.username,))
        self.assertEqual(self.client.post('/entrar/autenticador',data=dict(token=token,method='recovery',code=codes[0])).status_code,302)
        with self.client.session_transaction() as s:self.assertNotIn('role',s)
        self.assertTrue(mfa.verify(self.username,codes[0],True))

    def test_rate_limit_and_expiration(self):
        codes=self.activate();self.login()
        with self.client.session_transaction() as s:token=s['mfa_token']
        for _ in range(10):self.assertEqual(self.client.post('/entrar/autenticador',data=dict(token=token,code='bad')).status_code,422)
        self.assertEqual(self.client.post('/entrar/autenticador',data=dict(token=token,method='recovery',code=codes[0])).status_code,422)
        self.assertTrue(mfa.verify(self.username,codes[0],True))

    def test_failed_settings_passwords_are_still_rate_limited(self):
        self.login();self.client.get('/conta/seguranca')
        with self.client.session_transaction() as s:token=s['security_token']
        for _ in range(15):
            self.assertEqual(self.client.post('/conta/seguranca',data=dict(token=token,action='begin',password='bad')).status_code,422)
        response=self.client.post('/conta/seguranca',data=dict(token=token,action='begin',password=self.password))
        self.assertEqual(response.status_code,422)
        self.assertIn('Muitas tentativas'.encode(),response.data)
        self.assertIsNone(mfa.pending(self.username))


if __name__=='__main__':unittest.main()
