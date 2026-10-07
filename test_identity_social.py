import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import app
import database

class IdentitySocialTests(unittest.TestCase):
    def setUp(self):
        self.client=app.test_client()
        with self.client.session_transaction() as session:
            session.update(username='thiago.zotti', role='aluno', aluno_id='23081',
                           message_token='test-token')

    def test_pages(self):
        response = self.client.get('/mensagens')
        self.assertEqual(response.status_code,200)
        self.assertIn('Conversas do campus'.encode(), response.data)
        self.assertIn(b'class="dm-shell"', response.data)
        self.assertNotIn('Caixa de entrada'.encode(), response.data)
        self.assertEqual(self.client.get('/avatar').status_code,404)

    @patch('app.db.mark_thread_read')
    @patch('app.get_messages', return_value=[{
        'id': 7, 'sender': 'aline', 'sender_name': 'Profa. Aline',
        'recipient': 'thiago.zotti', 'recipient_name': 'Thiago Zotti',
        'subject': 'Mensagem direta', 'body': 'Aula confirmada',
        'created_at': '2026-09-28 10:00:00', 'is_read': 0,
    }])
    @patch('app.list_users', return_value=[{'username': 'aline', 'name': 'Profa. Aline', 'role': 'professor', 'active': 1}])
    def test_opening_thread_marks_only_that_conversation(self, users, messages, mark_thread):
        response = self.client.post('/mensagens', data={
            'token': 'test-token', 'action': 'read_thread', 'participant': 'aline',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/mensagens?with=aline', response.headers['Location'])
        mark_thread.assert_called_once_with('thiago.zotti', 'aline')

    @patch('app.log_action')
    @patch('app.send_message')
    @patch('app.list_users',return_value=[{'username':'aline','active':1}])
    def test_send_validation(self, users, send, log):
        valid={'token':'test-token','recipient':'aline','subject':'Dúvida','body':'Olá!'}
        for update in [{'token':''},{'recipient':'unknown'},{'body':' '},{'subject':'x'*161}]:
            self.client.post('/mensagens',data={**valid,**update})
        send.assert_not_called()
        self.client.post('/mensagens',data=valid)
        send.assert_called_once_with('thiago.zotti','aline','Dúvida','Olá!')

    def test_read_is_scoped_to_recipient(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(database,'DB_PATH',Path(folder)/'test.db'):
                with database.connection() as db:
                    db.execute('CREATE TABLE messages(id INTEGER PRIMARY KEY, recipient TEXT, is_read INTEGER)')
                    db.execute("INSERT INTO messages VALUES(1,'thiago.zotti',0)")
                database.mark_message_read(1,'pablo.sousa')
                with database.connection() as db:
                    self.assertEqual(db.execute('SELECT is_read FROM messages').fetchone()[0],0)
                database.mark_message_read(1,'thiago.zotti')
                with database.connection() as db:
                    self.assertEqual(db.execute('SELECT is_read FROM messages').fetchone()[0],1)

    @patch('app.get_messages', return_value=[])
    @patch('app.operations.guardian_students', return_value=[{'student_id': '23081'}])
    @patch('app.list_users', return_value=[
        {'username': 'thiago.zotti', 'name': 'Thiago', 'role': 'aluno', 'student_id': '23081', 'active': 1},
        {'username': 'pablo.sousa', 'name': 'Pablo', 'role': 'aluno', 'student_id': '23104', 'active': 1},
        {'username': 'aline', 'name': 'Profa. Aline', 'role': 'professor', 'student_id': None, 'active': 1},
        {'username': 'gilberto', 'name': 'Gilberto', 'role': 'diretor', 'student_id': None, 'active': 1},
    ])
    def test_guardian_only_lists_linked_student_and_staff(self, users, links, messages):
        with self.client.session_transaction() as session:
            session.update(username='responsavel.thiago', role='responsavel',
                           display_name='Responsável de Thiago', message_token='test-token')
        response = self.client.get('/mensagens')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Thiago', response.data)
        self.assertIn(b'Profa. Aline', response.data)
        self.assertIn(b'Gilberto', response.data)
        self.assertNotIn(b'Pablo', response.data)

    @patch('app.log_action')
    @patch('app.send_message')
    @patch('app.get_messages', return_value=[])
    @patch('app.operations.guardian_students', return_value=[{'student_id': '23081'}])
    @patch('app.list_users', return_value=[
        {'username': 'thiago.zotti', 'name': 'Thiago', 'role': 'aluno', 'student_id': '23081', 'active': 1},
        {'username': 'pablo.sousa', 'name': 'Pablo', 'role': 'aluno', 'student_id': '23104', 'active': 1},
    ])
    def test_guardian_cannot_post_to_unlinked_student(self, users, links, messages, send, log):
        with self.client.session_transaction() as session:
            session.update(username='responsavel.thiago', role='responsavel',
                           display_name='Responsável de Thiago', message_token='test-token')
        self.client.post('/mensagens', data={
            'token': 'test-token', 'recipient': 'pablo.sousa', 'body': 'Olá',
        })
        send.assert_not_called()

    def test_message_delete_and_restore_are_author_scoped(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(database, 'DB_PATH', Path(folder) / 'test.db'):
                with database.connection() as db:
                    db.execute('''CREATE TABLE messages(
                        id INTEGER PRIMARY KEY, sender TEXT, recipient TEXT,
                        deleted_at TEXT, deleted_by TEXT)''')
                    db.execute("INSERT INTO messages VALUES(1,'thiago.zotti','aline',NULL,NULL)")
                self.assertFalse(database.soft_delete_message(1, 'aline'))
                self.assertTrue(database.soft_delete_message(1, 'thiago.zotti'))
                self.assertFalse(database.restore_message(1, 'aline'))
                self.assertTrue(database.restore_message(1, 'thiago.zotti'))

if __name__ == '__main__':
    unittest.main()
