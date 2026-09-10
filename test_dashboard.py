import unittest
from datetime import datetime
from dashboard import student_summary, upcoming_lessons, CAMPUS_TZ


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 6, 12, tzinfo=CAMPUS_TZ)
        self.schedule = {'dias': ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB'],
                         'horarios': ['07:00'], 'grade': [['Web'] * 6]}

    def test_sunday_advances_to_monday(self):
        lesson = upcoming_lessons(self.schedule, self.now)[0]
        self.assertEqual(lesson['date'], '07/09')
        self.assertEqual(lesson['day'], 'Amanhã')

    def test_class_submission_and_deadline(self):
        exercises = [dict(id=1, class_name='3110', due_date='2026-09-01'),
                     dict(id=2, class_name='3110', due_date='2026-09-02'),
                     dict(id=3, class_name='1210', due_date='2026-09-01')]
        result = student_summary({'turma': '3110', 'grades': []}, exercises,
                                 [{'exercise_id': 1}], [], self.schedule, self.now)
        self.assertEqual(result['pending_count'], 1)
        self.assertEqual(result['overdue'], 1)
        self.assertEqual(result['completion'], 50)
        self.assertEqual(result['total'], 2)

    def test_empty_state(self):
        result = student_summary({'turma': '3110', 'grades': []}, [], [], [],
                                 self.schedule, self.now)
        self.assertEqual(result['completion'], 0)
        self.assertIsNone(result['best'])
        self.assertEqual(result['message_count'], 0)


if __name__ == '__main__':
    unittest.main()
