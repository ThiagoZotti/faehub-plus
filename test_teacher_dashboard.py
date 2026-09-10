import unittest
from datetime import datetime
from teacher_dashboard import teacher_overview
from dashboard import CAMPUS_TZ
from school_schedule import SCHEDULE_3110
from app import app

class TeacherDashboardTests(unittest.TestCase):
    def overview(self, assignments, **kwargs):
        return teacher_overview('aline',assignments,SCHEDULE_3110,[],kwargs.get('exercises',[]),
                                kwargs.get('submissions',[]),[],kwargs.get('messages',[]),
                                datetime(2026,9,4,9,20,tzinfo=CAMPUS_TZ))

    def test_aline_only_teaches_assigned_subjects(self):
        result=self.overview([dict(class_name='3110',discipline='LP3'),dict(class_name='3110',discipline='Projeto Final')])
        self.assertTrue(result['lessons'][0]['live'])
        self.assertEqual(result['lessons'][0]['subject'],'LP3')
        self.assertTrue(all(l['subject'] in ['LP3','Projeto Final'] for l in result['lessons']))

    def test_no_assignments_no_borrowed_classes(self):
        result=self.overview([])
        self.assertEqual(result['classes'],[])
        self.assertEqual(result['lessons'],[])

    def test_owned_submissions_only(self):
        result=self.overview([],exercises=[dict(id=1,teacher='aline'),dict(id=2,teacher='outro')],
                             submissions=[dict(exercise_id=1),dict(exercise_id=2)],
                             messages=[dict(recipient='aline',is_read=0),dict(recipient='outro',is_read=0)])
        self.assertEqual(result['submission_count'],1)
        self.assertEqual(result['unread'],1)

    def test_teacher_shell_and_student_shell(self):
        client=app.test_client()
        with client.session_transaction() as session:session.update(role='professor',username='aline',display_name='Profa. Aline')
        response=client.get('/painel')
        self.assertEqual(response.status_code,200)
        self.assertIn(b'CAMPUS DOCENTE',response.data)
        self.assertNotIn(b'id="sidebar"',response.data)
        self.assertNotIn(b'3210',response.data)
        with client.session_transaction() as session:session.update(role='aluno',username='thiago.zotti',aluno_id='23081')
        self.assertIn(b'CAMPUS LOBBY',client.get('/painel').data)

if __name__=='__main__':unittest.main()
