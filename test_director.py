import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import database as db
from app import app, ROSTER
from director import init_director, access_version
import account_enrollment as enrollment

class DirectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.patch=patch.object(db,'DB_PATH',Path(cls.temp.name)/'test.db');cls.patch.start()
        db.init_db();init_director();db.seed_teacher_assignments()

    @classmethod
    def tearDownClass(cls):cls.patch.stop();cls.temp.cleanup()

    def setUp(self):
        self.client=app.test_client();self.login()
        self.authorized=patch.object(enrollment,'authorize_invitation_actor');self.authorized.start()
        self.addCleanup(self.authorized.stop)

    def login(self,user='gilberto',role='admin'):
        with self.client.session_transaction() as s:
            s.clear();s.update(username=user,role=role,display_name='Direção',director_token='token',auth_version=access_version(user))

    def test_pages_and_real_totals(self):
        for page in ('painel','usuarios','turmas','relatorios','configuracoes','mensagens'):
            response=self.client.get('/'+page)
            self.assertEqual(response.status_code,200,page)
            self.assertIn('CAMPUS DIREÇÃO'.encode(),response.data)
        # Check visible metrics, not incidental digits inside static cache hashes.
        self.assertNotIn(b'<strong>812</strong>',self.client.get('/painel').data)

    def test_denies_other_roles_and_csrf(self):
        self.assertEqual(self.client.post('/usuarios',data=dict(action='create')).status_code,400)
        self.login('aline','professor')
        self.assertEqual(self.client.get('/usuarios').status_code,403)
        self.assertEqual(self.client.get('/relatorios?export=grades').status_code,403)

    def test_create_student_and_login_pages(self):
        sid=ROSTER[0]['id']
        # This test exercises enrollment with a director already authorized;
        # bootstrap constraints have their own dedicated test.
        with patch.object(enrollment,'mail_configured',return_value=False), patch.object(enrollment,'authorize_invitation_actor'):
            response=self.client.post('/usuarios',data=dict(token='token',action='invite',username='new.student',name='Novo Aluno',role='aluno',student_id=sid,email='novo@example.com',current_password='direcao@123'))
        self.assertEqual(response.status_code,302)
        self.assertIsNone(db.authenticate('new.student','strong-pass123'))
        invitation_id=enrollment.invitation_directory()['new.student']['id']
        with patch.object(enrollment,'mail_configured',return_value=True), patch.object(enrollment,'send_invitation_email') as sender:
            enrollment.deliver_invitation('gilberto',invitation_id)
        import hashlib
        enrollment.complete_invitation(hashlib.sha256(sender.call_args.args[1].encode()).hexdigest(),'a strong new passphrase','a strong new passphrase')
        self.login('new.student','aluno')
        with self.client.session_transaction() as s:s['aluno_id']=sid
        for page in ('painel','boletim','agenda','horario','exercicios','mensagens'):
            self.assertEqual(self.client.get('/'+page).status_code,200,page)
        self.assertEqual(self.client.get('/avatar').status_code,404)

    def test_disable_and_reactivate_revokes_session(self):
        db.create_user('temp.teacher','strong-pass123','Temporário','professor')
        teacher=app.test_client()
        with teacher.session_transaction() as s:s.update(username='temp.teacher',role='professor',auth_version=0)
        self.assertEqual(teacher.get('/painel').status_code,200)
        for active in ('0','1'):
            r=self.client.post('/usuarios',data=dict(token='token',action='status',username='temp.teacher',active=active))
            self.assertEqual(r.status_code,302)
        self.assertEqual(teacher.get('/painel').status_code,302)
        self.assertEqual(self.client.post('/usuarios',data=dict(token='token',action='status',username='gilberto',active='0')).status_code,422)

    def test_assignment_removal_stays_removed(self):
        data=dict(token='token',class_name='3110',teacher='aline',discipline='LP3',action='unassign')
        self.assertEqual(self.client.post('/turmas',data=data).status_code,302)
        db.seed_teacher_assignments()
        self.assertNotIn('LP3',[a['discipline'] for a in db.get_teacher_assignments('aline')])
        data['action']='assign'
        self.assertEqual(self.client.post('/turmas',data=data).status_code,302)
        self.assertIn('LP3',[a['discipline'] for a in db.get_teacher_assignments('aline')])

    def test_settings_capacity_and_reports(self):
        self.assertEqual(self.client.post('/turmas',data=dict(token='token',action='class',class_name='3110',capacity='10',shift='Manhã')).status_code,422)
        self.assertEqual(self.client.post('/turmas',data=dict(token='token',action='class',class_name='3110',capacity='40',shift='Manhã')).status_code,302)
        self.assertEqual(self.client.post('/configuracoes',data=dict(token='token',action='settings',institution_name='Escola teste',year='2026',contact='Secretaria')).status_code,302)
        self.assertIn(b'Escola teste',self.client.get('/painel').data)
        db.save_attendance('23081','2026-09-01','presente');db.save_attendance('23081','2026-09-02','ausente')
        response=self.client.get('/relatorios?export=attendance&start=2026-09-02&end=2026-09-02')
        self.assertEqual(response.status_code,200)
        self.assertIn(b'2026-09-02',response.data);self.assertNotIn(b'2026-09-01',response.data)
        self.assertEqual(self.client.get('/relatorios?start=bad').status_code,400)

    def test_password_reset(self):
        db.create_user('reset.teacher','old-pass123','Professor','professor')
        self.assertEqual(self.client.post('/usuarios',data=dict(token='token',action='password',username='reset.teacher',password='new-pass12345')).status_code,302)
        self.assertIsNone(db.authenticate('reset.teacher','old-pass123'))
        self.assertIsNotNone(db.authenticate('reset.teacher','new-pass12345'))
        self.assertEqual(access_version('reset.teacher'),1)

if __name__=='__main__':unittest.main()
