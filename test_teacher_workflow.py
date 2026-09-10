import unittest
from unittest.mock import patch
from datetime import date
from app import app, ROSTER
from teacher_workflow import validated_grades, validated_attendance, scoped_roster

ASSIGN=[dict(class_name='3110',discipline='LP3')]

class TeacherWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.client=app.test_client()
        with self.client.session_transaction() as s:
            s.update(role='professor',username='aline',display_name='Profa. Aline',teacher_token='test-token')

    def test_full_roster_on_three_pages(self):
        self.assertEqual(len(scoped_roster(ASSIGN,ROSTER,'3110')),34)
        for page in ('turmas','chamada','notas'):
            response=self.client.get('/'+page)
            self.assertEqual(response.status_code,200,page)
            self.assertEqual(response.data.count(b'data-student='),34,page)

    def test_grade_validation(self):
        sid=ROSTER[0]['id']
        self.assertEqual(validated_grades(ASSIGN,ROSTER,'3110','LP3',sid,'7,5','8'),[7.5,8])
        for val in ('nan','inf','-1','11',''):
            with self.assertRaises(ValueError):validated_grades(ASSIGN,ROSTER,'3110','LP3',sid,val,8)
        with self.assertRaises(ValueError):validated_grades(ASSIGN,ROSTER,'3110','LP3','bad',7,8)
        with self.assertRaises(ValueError):validated_grades(ASSIGN,ROSTER,'3110','other',sid,7,8)

    def test_attendance_validation(self):
        with self.assertRaises(ValueError):validated_attendance(ROSTER,'2026-09-01',{},date(2026,9,3))
        with self.assertRaises(ValueError):validated_attendance(ROSTER,'2027-01-01',{},date(2026,9,3))

    @patch('app.log_action')
    @patch('app.save_attendance_batch')
    def test_attendance_post(self,save,log):
        data=dict(token='test-token',turma='3110',data='2026-09-01')
        self.assertEqual(self.client.post('/chamada',data=data).status_code,422)
        save.assert_not_called()
        data.update({'presenca_'+s['id']:'presente' for s in ROSTER})
        self.assertEqual(self.client.post('/chamada',data=data).status_code,302)
        self.assertEqual(len(save.call_args.args[1]),34)
        save.assert_called_once()

    @patch('app.log_action')
    @patch('app.apply_persisted_grades')
    @patch('app.save_grade')
    def test_grade_post_and_csrf(self,save,apply,log):
        data=dict(token='bad',turma='3110',disciplina='LP3',aluno_id=ROSTER[0]['id'],n1='7.5',n2='8')
        self.assertEqual(self.client.post('/notas',data=data).status_code,400)
        save.assert_not_called()
        data['token']='test-token'
        self.assertEqual(self.client.post('/notas',data=data).status_code,302)
        save.assert_called_once_with(ROSTER[0]['id'],'LP3',7.5,8.0)

    def test_scope_rejected(self):
        self.assertEqual(self.client.get('/turmas?turma=9999').status_code,403)
        self.assertEqual(self.client.get('/notas?disciplina=Outra').status_code,403)

if __name__=='__main__':unittest.main()
