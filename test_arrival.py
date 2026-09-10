import unittest
from unittest.mock import patch
from pathlib import Path
from app import app

class ArrivalTests(unittest.TestCase):
    def setUp(self):
        self.client=app.test_client()
        self.client.get('/')
        with self.client.session_transaction() as session:
            self.token=session['login_token']

    @patch('app.log_action')
    @patch('app.authenticate')
    def test_each_role_uses_account_not_selected_role(self, authenticate, log):
        for role, expected in [('aluno','aluno'),('professor','professor'),('diretor','admin')]:
            client=app.test_client()
            client.get('/')
            with client.session_transaction() as session: token=session['login_token']
            authenticate.return_value={'role':role,'name':'Pessoa Teste','student_id':'23081'}
            result=client.post('/entrar',data={'token':token,'usuario':'teste','senha':'test','role':'diretor'},
                               headers={'X-Campus-Login':'1'})
            self.assertEqual(result.status_code,200)
            self.assertEqual(result.json['role'],role)
            with client.session_transaction() as session:self.assertEqual(session['role'],expected)

    @patch('app.authenticate',return_value=None)
    def test_invalid_password_preserves_username_without_echoing_password(self, authenticate):
        result=self.client.post('/entrar',data={'token':self.token,'usuario':'aluno.teste','senha':'secret-test'})
        self.assertEqual(result.status_code,401)
        self.assertIn(b'aluno.teste',result.data)
        self.assertNotIn(b'secret-test',result.data)

    @patch('app.authenticate')
    def test_invalid_token_blocks_authentication(self, authenticate):
        result=self.client.post('/entrar',data={'usuario':'teste'},headers={'X-Campus-Login':'1'})
        self.assertEqual(result.status_code,400)
        authenticate.assert_not_called()

    @patch('app.authenticate',return_value=None)
    def test_json_error(self, authenticate):
        result=self.client.post('/entrar',data={'token':self.token,'usuario':'teste','senha':'x'},headers={'X-Campus-Login':'1'})
        self.assertEqual(result.status_code,401)
        self.assertIn('error',result.json)

    def test_authenticated_session_does_not_skip_entrance(self):
        with self.client.session_transaction() as session:
            session.update(role='aluno',aluno_id='23081',username='thiago.zotti')
        result=self.client.get('/')
        self.assertEqual(result.status_code,200)
        self.assertIn(b'enterCampus',result.data)

    def test_cinematic_background_is_one_optimized_priority_asset(self):
        result=self.client.get('/')
        asset=b'campus-login-cinematic-v3.webp'
        self.assertEqual(result.data.count(asset),1)
        self.assertIn(b'fetchpriority="high"',result.data)
        self.assertNotIn(b'rel="preload"',result.data)
        self.assertLess(Path('static/campus-login-cinematic-v3.webp').stat().st_size,300_000)

if __name__=='__main__':unittest.main()
