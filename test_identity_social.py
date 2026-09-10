import unittest
from unittest.mock import patch
import tempfile
from pathlib import Path
from app import app
import database

class IdentitySocialTests(unittest.TestCase):
    def setUp(self):
        self.client=app.test_client()
        with self.client.session_transaction() as session:
            session.update(username='thiago.zotti', role='aluno', aluno_id='23081',
                           message_token='test-token', avatar_token='test-token')

    def test_pages(self):
        for path in ['/avatar','/mensagens']:
            self.assertEqual(self.client.get(path).status_code,200)

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

    @patch('app.log_action')
    @patch('app.save_avatar')
    def test_avatar_validation(self, save, log):
        data={'token':'test-token','skin':'#d7a27d','hair':'#172033','shirt':'#367cf6','accessory':'glasses'}
        self.client.post('/avatar',data={**data,'token':''})
        self.client.post('/avatar',data={**data,'skin':'invalid'})
        self.client.post('/avatar',data={**data,'skin':'#367cf6'})
        save.assert_not_called()
        self.client.post('/avatar',data=data)
        self.assertEqual(save.call_args.args[:5],('thiago.zotti','#d7a27d','#172033','#367cf6','glasses'))
        self.assertEqual(save.call_args.args[5]['hairstyle'],'short')

    @patch('app.log_action')
    @patch('app.save_avatar')
    def test_expanded_avatar_collection_is_accepted(self, save, log):
        data={'token':'test-token','skin':'#b87a55','hair':'#8a5b3d','shirt':'#cf315f',
              'accessory':'backpack','appearance':'feminine','hairstyle':'afro',
              'outfit':'varsity','bottom':'cargo','shoes':'hightop'}
        response=self.client.post('/avatar',data=data)
        self.assertEqual(response.status_code,302)
        save.assert_called_once_with('thiago.zotti','#b87a55','#8a5b3d','#cf315f','backpack',
                                     {'appearance':'feminine','hairstyle':'afro','outfit':'varsity',
                                      'bottom':'cargo','shoes':'hightop'})

    def test_new_wardrobe_persists_without_touching_user_data(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(database,'DB_PATH',Path(folder)/'avatar.db'):
                with database.connection() as db:
                    db.execute('CREATE TABLE avatar_profiles(username TEXT PRIMARY KEY,skin TEXT,hair TEXT,shirt TEXT,accessory TEXT,updated_at TEXT)')
                    db.execute('CREATE TABLE avatar_styles(username TEXT PRIMARY KEY,appearance TEXT,hairstyle TEXT,outfit TEXT,bottom TEXT,shoes TEXT)')
                style=dict(appearance='feminine',hairstyle='long',outfit='jacket',bottom='skirt',shoes='boots')
                database.save_avatar('test','#d7a27d','#172033','#367cf6','earrings',style)
                saved=database.get_avatar('test')
                for key,value in style.items():self.assertEqual(saved[key],value)
                self.assertEqual(saved['accessory'],'earrings')

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

if __name__ == '__main__':
    unittest.main()
