import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import database as db
from app import app

class RealSubjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(db, 'DB_PATH', Path(self.temp.name) / 'subjects.db')
        self.db_patch.start()
        db.init_db()

    def tearDown(self):
        self.db_patch.stop()
        self.temp.cleanup()

    def test_student_report_uses_schedule_subjects(self):
        # These are explicit isolated fixtures, not hard-coded scores in the app.
        for subject in ('Matemática','BD','PDM','Física','Biologia'):
            db.save_grade('23081', subject, 7, 8)
        client=app.test_client()
        with client.session_transaction() as session:
            session.update(username='thiago.zotti',role='aluno',aluno_id='23081')
        response=client.get('/boletim')
        self.assertEqual(response.status_code,200)
        for subject in ('Matemática','BD','PDM','Física','Biologia'):
            self.assertIn(subject.encode(),response.data)
        for removed in ('Redes de Computadores','Engenharia de Software','Matemática Aplicada'):
            self.assertNotIn(removed.encode(),response.data)

    def test_no_scores_are_invented_for_ungraded_student(self):
        from app import student_profile
        self.assertEqual(student_profile('23081')['grades'], [])

if __name__=='__main__':unittest.main()
