import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import database as db
from app import app


class TeacherStudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.patch=patch.object(db,'DB_PATH',Path(cls.temp.name)/'test.db')
        cls.patch.start()
        db.init_db(); db.seed_teacher_assignments()

    @classmethod
    def tearDownClass(cls):
        cls.patch.stop();cls.temp.cleanup()

    def setUp(self):
        self.client=app.test_client();self.login('aline','professor')

    def login(self,user,role):
        with self.client.session_transaction() as s:
            s.clear();s.update(username=user,role=role,display_name='Teste',aluno_id='23081',
                              studio_token='token',message_token='token',exercise_token='token')

    def test_teacher_pages(self):
        for path in ('avisos','exercicios','mensagens'):
            r=self.client.get('/'+path)
            self.assertEqual(r.status_code,200,path)
            self.assertIn(b'CAMPUS DOCENTE',r.data)

    def test_notice_lifecycle_and_student_visibility(self):
        r=self.client.post('/avisos',data=dict(token='token',action='create',class_name='3110',title='Aviso de teste',body='Conteúdo publicado',priority='importante'))
        self.assertEqual(r.status_code,302)
        item=next(n for n in db.get_notices() if n['title']=='Aviso de teste')
        self.login('thiago.zotti','aluno')
        self.assertIn(b'Aviso de teste',self.client.get('/avisos').data)
        self.login('aline','professor')
        self.assertEqual(self.client.post('/avisos',data=dict(token='token',action='archive',id=item['id'])).status_code,302)
        self.login('thiago.zotti','aluno')
        self.assertNotIn(b'Aviso de teste',self.client.get('/avisos').data)
        self.login('aline','professor')
        self.client.post('/avisos',data=dict(token='token',action='restore',id=item['id']))
        self.assertFalse(next(n for n in db.get_notices() if n['id']==item['id'])['archived'])

    def test_exercise_delivery_review_and_archive(self):
        r=self.client.post('/exercicios',data=dict(token='token',action='create',class_name='3110',discipline='LP3',title='Atividade de teste',description='Explique sua solução',due_date='2026-09-20'))
        self.assertEqual(r.status_code,302)
        item=next(e for e in db.get_exercises() if e['title']=='Atividade de teste')
        self.login('thiago.zotti','aluno')
        self.client.post('/exercicios',data=dict(token='token',exercise_id=item['id'],answer='Minha solução'))
        submission=next(s for s in db.get_submissions() if s['exercise_id']==item['id'])
        self.login('aline','professor')
        review=dict(token='token',action='review',id=item['id'],submission_id=submission['id'],answer_snapshot='Minha solução',score='8.5',feedback='Boa solução!')
        self.assertEqual(self.client.post('/exercicios',data=review).status_code,302)
        self.login('thiago.zotti','aluno')
        self.assertIn(b'Boa solu',self.client.get('/exercicios').data)
        self.client.post('/exercicios',data=dict(token='token',exercise_id=item['id'],answer='Resposta revisada'))
        self.login('aline','professor')
        self.assertEqual(self.client.post('/exercicios',data=review).status_code,422)
        self.client.post('/exercicios',data=dict(token='token',action='archive',id=item['id']))
        self.assertNotIn(item['id'],[e['id'] for e in db.get_exercises()])
        self.assertIn(submission['id'],[s['id'] for s in db.get_submissions()])

    def test_ownership_and_validation(self):
        for path in ('avisos','exercicios'):
            self.assertEqual(self.client.post('/'+path,data=dict(token='bad')).status_code,400)
        r=self.client.post('/exercicios',data=dict(token='token',class_name='3110',discipline='Não vinculada',title='x',description='x',due_date='2026-09-20'))
        self.assertEqual(r.status_code,422)
        db.create_user('outro_docente','test-password','Outro','professor')
        db.create_exercise('outro_docente','Privado','Descrição','LP3','3110','2026-09-20')
        item=next(e for e in db.get_exercises() if e['teacher']=='outro_docente')
        self.assertNotIn(b'Privado',self.client.get('/exercicios').data)
        self.assertEqual(self.client.post('/exercicios',data=dict(token='token',action='archive',id=item['id'])).status_code,422)

    def test_messages_send_and_read(self):
        self.assertEqual(self.client.post('/mensagens',data=dict(token='token',recipient='thiago.zotti',subject='Orientação',body='Vamos revisar?')).status_code,302)
        msg=db.get_messages('thiago.zotti')[0]
        self.login('thiago.zotti','aluno')
        self.client.post('/mensagens',data=dict(token='token',action='read',message_id=msg['id']))
        self.assertEqual(db.get_messages('aline')[0]['is_read'],1)

if __name__=='__main__':unittest.main()
