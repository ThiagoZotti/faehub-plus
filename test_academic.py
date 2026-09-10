import unittest
from datetime import date
from academic import attendance_calendar

class CalendarTests(unittest.TestCase):
    def test_leap_year_and_week_alignment(self):
        result = attendance_calendar([], '2024-02')
        days = [d for week in result['weeks'] for d in week if d]
        self.assertEqual(len(days), 29)
        self.assertIsNone(result['weeks'][0][0])
        self.assertEqual(result['weeks'][0][3]['day'], 1)
        self.assertTrue(all(d['status'] == 'unrecorded' for d in days))

    def test_records_are_not_invented_or_counted_across_months(self):
        records = [{'class_date':'2026-09-01','status':'presente'},
                   {'class_date':'2026-09-02','status':'ausente'},
                   {'class_date':'2026-08-31','status':'presente'}]
        result = attendance_calendar(records, '2026-09')
        self.assertEqual((result['present'], result['absent']), (1, 1))
        self.assertEqual(len(result['rows']), 2)

    def test_invalid_month_falls_back(self):
        for value in ['bad', '2026-13', '0001-01']:
            self.assertEqual(attendance_calendar([], value, date(2026, 9, 3))['month'], '2026-09')

if __name__ == '__main__':
    unittest.main()
