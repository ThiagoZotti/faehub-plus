import unittest
from app import app

class RealSubjectTests(unittest.TestCase):
    def test_student_report_uses_schedule_subjects(self):
        client=app.test_client()
        with client.session_transaction() as session:
            session.update(username='thiago.zotti',role='aluno',aluno_id='23081')
        response=client.get('/boletim')
        self.assertEqual(response.status_code,200)
        for subject in ('Matemática','BD','PDM','Física','Biologia'):
            self.assertIn(subject.encode(),response.data)
        for removed in ('Redes de Computadores','Engenharia de Software','Matemática Aplicada'):
            self.assertNotIn(removed.encode(),response.data)

if __name__=='__main__':unittest.main()
