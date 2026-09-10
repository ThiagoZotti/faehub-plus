import unittest
from unittest.mock import patch
from datetime import datetime
from dashboard import upcoming_lessons, CAMPUS_TZ
from school_schedule import SCHEDULE_3110
from app import app

class ModuleTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session.update(username='thiago.zotti', role='aluno', aluno_id='23081', exercise_token='test-token')

    def test_schedule_skips_vacant_slot(self):
        next_lesson = upcoming_lessons(SCHEDULE_3110, datetime(2026,9,8,8,45,tzinfo=CAMPUS_TZ))[0]
        self.assertEqual((next_lesson['subject'], next_lesson['time']), ('Biologia','10:40'))

    def test_three_pages(self):
        for path in ['/horario','/avisos','/exercicios']:
            self.assertEqual(self.client.get(path).status_code, 200)

    @patch('app.log_action')
    @patch('app.submit_exercise')
    @patch('app.get_exercises', return_value=[{'id':42,'class_name':'3110'}])
    def test_submission_validation(self, exercises, save, log):
        for data in [
            {'exercise_id':'42','answer':'Resposta'},
            {'token':'test-token','exercise_id':'42','answer':'   '},
            {'token':'test-token','exercise_id':'99','answer':'Resposta'},
            {'token':'test-token','exercise_id':'invalid','answer':'Resposta'}]:
            self.client.post('/exercicios',data=data)
        save.assert_not_called()
        self.client.post('/exercicios',data={'token':'test-token','exercise_id':'42','answer':'Minha resposta'})
        save.assert_called_once_with(42,'thiago.zotti','Minha resposta')

if __name__ == '__main__':
    unittest.main()
