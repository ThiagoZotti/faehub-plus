import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database as db
from app import app, NAV
from director import access_version, init_director


class FaeNetPortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db_patch = patch.object(db, 'DB_PATH', Path(cls.temp.name) / 'portal.db')
        cls.db_patch.start()
        db.init_db()
        init_director()

    @classmethod
    def tearDownClass(cls):
        cls.db_patch.stop()
        cls.temp.cleanup()

    def client(self, username, role):
        client = app.test_client()
        with client.session_transaction() as session:
            session.update(username=username, role=role, auth_version=access_version(username))
            if role == 'aluno':
                session['aluno_id'] = '23104'
        return client

    def test_portal_shared_by_all_existing_profiles(self):
        for username, role in [('pablo.sousa','aluno'), ('aline','professor'),
                               ('gilberto','admin'), ('responsavel.thiago','responsavel')]:
            with self.subTest(role=role):
                html = self.client(username,role).get('/faenet')
                self.assertEqual(html.status_code,200)
                text = html.get_data(as_text=True)
                self.assertIn('<title>FaeNet · FaeHub+</title>',text)
                self.assertIn('faenet-portal',text)
                self.assertIn('campus-electric view-faenet',text)
                self.assertEqual(text.count('target="_blank" rel="noopener noreferrer"'),6)
                for path in ('/feed','/messages','/explore','/faemap'):
                    self.assertIn('https://faenet.onrender.com'+path,text)
                self.assertIn('acessos independentes',text)
                self.assertEqual(sum(item[0]=='faenet' for item in NAV[role]),1)

    def test_portal_requires_active_login_and_does_not_expand_permissions(self):
        self.assertEqual(app.test_client().get('/faenet').status_code,302)
        student=self.client('pablo.sousa','aluno')
        self.assertEqual(student.get('/faenet').status_code,200)
        self.assertEqual(student.get('/usuarios').status_code,403)
        self.assertEqual(student.post('/faenet').status_code,405)
        with db.connection() as conn:
            conn.execute("UPDATE users SET active=FALSE WHERE username='pablo.sousa'")
        try:
            self.assertEqual(student.get('/faenet').status_code,302)
        finally:
            with db.connection() as conn:
                conn.execute("UPDATE users SET active=TRUE WHERE username='pablo.sousa'")

    def test_family_theme_only_changes_on_portal(self):
        client=self.client('responsavel.thiago','responsavel')
        self.assertNotIn('campus-electric view-painel',client.get('/painel').get_data(as_text=True))
        self.assertIn('campus-electric view-faenet',client.get('/faenet').get_data(as_text=True))

    def test_delivery_uses_shared_attachment_trigger(self):
        html=self.client('pablo.sousa','aluno').get('/exercicios').get_data(as_text=True)
        self.assertIn('data-delivery-attachment',html)
        self.assertIn('Adicionar arquivo',html)
        self.assertIn('class="dm-dialog-upload"',html)
        self.assertIn('name="attachment" type="file"',html)
        self.assertIn('data-delivery-remove',html)
        self.assertIn('enctype="multipart/form-data" novalidate',html)


if __name__ == '__main__':
    unittest.main()
