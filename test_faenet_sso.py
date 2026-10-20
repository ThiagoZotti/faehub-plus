import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs

import database as db
from app import app
from director import init_director
import faenet_sso as sso


class FaeNetSsoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)/'base.db'
        with patch.object(db, 'DB_PATH', cls.base):
            db.init_db(); init_director()
            with db.connection() as conn:
                conn.execute("INSERT INTO account_identities(username,email,verified_at) VALUES('thiago.zotti','fixture@example.com',1) ON CONFLICT(username) DO UPDATE SET verified_at=1")

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def setUp(self):
        self.path = Path(self.temp.name)/'case.db'; shutil.copyfile(self.base, self.path)
        self.db_patch = patch.object(db, 'DB_PATH', self.path); self.db_patch.start(); self.addCleanup(self.db_patch.stop)
        key_patch=patch.dict(os.environ, FAEHUB_FAENET_CLIENT_SECRET='a'*64);key_patch.start();self.addCleanup(key_patch.stop)
        self.client=app.test_client(); self.verifier='b'*64
        self.args=dict(client_id='faenet',redirect_uri=sso.CALLBACK,response_type='code',code_challenge_method='S256',code_challenge=sso.challenge(self.verifier),state='c'*43)
        self.headers={'Authorization':'Bearer '+'a'*64}

    def login(self, username='thiago.zotti'):
        with self.client.session_transaction() as session:
            session.update(username=username,role='aluno',auth_version=0,mfa_verified=True)

    def grant(self):
        self.login()
        result=self.client.get('/sso/faenet/authorize',query_string=self.args)
        self.assertEqual(result.status_code,302)
        return parse_qs(urlsplit(result.location).query)['code'][0]

    def exchange(self,code,**updates):
        data=dict(grant_type='authorization_code',code=code,code_verifier=self.verifier,redirect_uri=sso.CALLBACK);data.update(updates)
        return self.client.post('/sso/faenet/token',data=data,headers=self.headers)

    def test_code_is_single_use_pkce_and_server_private(self):
        code=self.grant()
        self.assertEqual(self.exchange(code,code_verifier='wrong'*12).status_code,400)
        result=self.exchange(code);self.assertEqual(result.status_code,200)
        self.assertEqual(result.json['profile']['role'],'aluno')
        self.assertNotIn('email',result.json['profile']);self.assertNotIn('student_id',result.json['profile'])
        token=result.json['access_token']
        self.assertEqual(self.exchange(code).status_code,400)
        with db.connection() as conn:
            saved=str([dict(r) for r in conn.execute('SELECT * FROM faenet_grants')])
            self.assertNotIn(code,saved);self.assertNotIn(token,saved)
        self.assertTrue(self.client.post('/sso/faenet/introspect',data=dict(token=token),headers=self.headers).json['active'])

    def test_block_and_auth_version_revoke_existing_tokens(self):
        token=self.exchange(self.grant()).json['access_token']
        with db.connection() as conn: conn.execute("UPDATE users SET active=FALSE WHERE username='thiago.zotti'")
        self.assertFalse(self.client.post('/sso/faenet/introspect',data=dict(token=token),headers=self.headers).json['active'])
        with db.connection() as conn:
            conn.execute("UPDATE users SET active=TRUE WHERE username='thiago.zotti'")
            conn.execute("INSERT INTO auth_versions(username,version) VALUES('thiago.zotti',1)")
        self.assertFalse(self.client.post('/sso/faenet/introspect',data=dict(token=token),headers=self.headers).json['active'])

    def test_fixed_callback_unverified_demo_secret_and_expiration(self):
        self.login()
        self.assertEqual(self.client.get('/sso/faenet/authorize',query_string=dict(self.args,redirect_uri='https://evil.example')).status_code,400)
        self.assertEqual(self.client.post('/sso/faenet/token',data={}).status_code,401)
        self.login('aline')
        self.assertEqual(self.client.get('/sso/faenet/authorize',query_string=self.args).status_code,302)  # wrong role requires login
        code=self.grant()
        with patch('faenet_sso.time.time',return_value=time.time()+61): self.assertEqual(self.exchange(code).status_code,400)
        with db.connection() as conn: conn.execute("UPDATE account_identities SET verified_at=NULL WHERE username='thiago.zotti'")
        self.assertEqual(self.client.get('/sso/faenet/authorize',query_string=self.args).status_code,403)

    def test_login_resume_preserved_and_mfa_not_bypassed(self):
        result=self.client.get('/sso/faenet/authorize',query_string=self.args)
        self.assertEqual(result.location,'/')
        self.client.get('/')
        with self.client.session_transaction() as session: csrf=session['login_token']
        result=self.client.post('/entrar',data=dict(token=csrf,usuario='thiago.zotti',senha='aluno@123'),headers={'X-Campus-Login':'1'})
        self.assertEqual(result.json['destination'],'/sso/faenet/authorize')
        self.assertEqual(self.client.get(result.json['destination']).status_code,302)
        with db.connection() as conn: conn.execute("INSERT INTO account_mfa(username,enabled) VALUES('thiago.zotti',TRUE)")
        with self.client.session_transaction() as session: session['mfa_verified']=False
        self.assertEqual(self.client.get('/sso/faenet/authorize',query_string=self.args).location,'/')

    def test_mfa_recovery_confirmation_resumes_the_same_sso_request(self):
        import account_mfa as mfa
        import pyotp
        from cryptography.fernet import Fernet
        with patch.dict(os.environ,FAEHUB_MFA_ENCRYPTION_KEY=Fernet.generate_key().decode()):
            mfa.begin('thiago.zotti','aluno@123')
            codes=mfa.activate('thiago.zotti',pyotp.TOTP(mfa.pending('thiago.zotti')).now())
            self.client.get('/sso/faenet/authorize',query_string=self.args);self.client.get('/')
            with self.client.session_transaction() as session:csrf=session['login_token']
            result=self.client.post('/entrar',data=dict(token=csrf,usuario='thiago.zotti',senha='aluno@123'),headers={'X-Campus-Login':'1'})
            self.assertTrue(result.json['mfa_required'])
            with self.client.session_transaction() as session:csrf=session['mfa_token'];self.assertIn('sso_resume',session)
            result=self.client.post('/entrar/autenticador',data=dict(token=csrf,method='recovery',code=codes[0]))
            self.assertIn(b'/sso/faenet/authorize',result.data)
            self.assertTrue(self.client.get('/sso/faenet/authorize').location.startswith(sso.CALLBACK+'?'))

    def test_all_four_verified_roles_are_eligible(self):
        for role in ('aluno','professor','diretor','responsavel'):
            with self.subTest(role=role):
                with db.connection() as conn:
                    conn.execute("DELETE FROM account_roles WHERE username='thiago.zotti'")
                    conn.execute("UPDATE users SET role=? WHERE username='thiago.zotti'",('aluno' if role=='responsavel' else role,))
                    if role=='responsavel':
                        conn.execute("INSERT INTO account_roles(username,role) VALUES('thiago.zotti',?)",(role,))
                with self.client.session_transaction() as session:
                    session.update(username='thiago.zotti',role='admin' if role=='diretor' else role,auth_version=0,mfa_verified=True)
                code=parse_qs(urlsplit(self.client.get('/sso/faenet/authorize',query_string=self.args).location).query)['code'][0]
                self.assertEqual(self.exchange(code).json['profile']['role'],role)
