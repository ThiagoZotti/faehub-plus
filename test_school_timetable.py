import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import academic_core
import database as db
import school_timetable as timetable
from app import app, live_roster, student_profile
from dashboard import CAMPUS_TZ, upcoming_lessons
from director import access_version, init_director
from teacher_dashboard import teacher_overview


class SchoolTimetableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name) / 'base.db'
        with patch.object(db, 'DB_PATH', cls.base):
            db.init_db(); init_director(); db.seed_teacher_assignments()
            academic_core.sync_teacher_assignments()
            with db.connection() as conn:
                year = conn.execute("SELECT id FROM academic_years WHERE name='2026'").fetchone()['id']
                subject = conn.execute("SELECT id FROM subjects WHERE code='MAT'").fetchone()['id']
                for code, room in [('4201', 'Laboratório A'), ('4202', 'Laboratório B'), ('4203', 'Laboratório C')]:
                    klass = conn.execute("INSERT INTO classes(academic_year_id,code,shift,room,capacity,status) VALUES(?,?,'Tarde',?,40,'active') RETURNING id", (year, code, room)).fetchone()['id']
                    conn.execute('INSERT INTO class_subjects(class_id,subject_id) VALUES(?,?)', (klass, subject))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.path = Path(self.temp.name) / 'case.db'
        shutil.copyfile(self.base, self.path)
        self.db_patch = patch.object(db, 'DB_PATH', self.path)
        self.db_patch.start()
        with db.connection() as conn:
            self.classes = {r['code']: r['id'] for r in conn.execute('SELECT id,code FROM classes')}
            self.subjects = {r['code']: r['id'] for r in conn.execute('SELECT c.code,cs.id FROM class_subjects cs JOIN classes c ON c.id=cs.class_id JOIN subjects s ON s.id=cs.subject_id WHERE s.code=\'MAT\'')}
        self.client = app.test_client()
        self.login()

    def tearDown(self):
        self.db_patch.stop()

    def login(self, username='gilberto', role='admin'):
        with self.client.session_transaction() as session:
            session.clear()
            session.update(username=username, role=role, display_name='Teste', auth_version=access_version(username), p0_token='test-token')
            if role == 'aluno':
                session['aluno_id'] = '23081'

    def payload(self, code='4201', **changes):
        return dict(action='schedule_save', class_subject_id=self.subjects[code], weekday='6',
                    starts_at='14:00', ends_at='15:00', room='', **changes)

    def save(self, code='4201', **changes):
        values = self.payload(code)
        values.update(changes)
        timetable.save_slot(values, 'gilberto')
        return timetable.slots(class_id=self.classes[code], include_archived=True)[-1]

    def bind(self, code):
        with db.connection() as conn:
            conn.execute("INSERT INTO teacher_subjects(teacher_username,class_subject_id,valid_from) VALUES('aline',?,'2026-01-01')", (self.subjects[code],))

    def test_create_edit_archive_restore_and_audit(self):
        row = self.save()
        self.save(slot_id=row['id'], revision=row['revision'], starts_at='15:00', ends_at='16:00')
        row = timetable.slots(class_id=self.classes['4201'])[0]
        self.assertEqual(row['starts_at'], '15:00')
        for action, active in [('schedule_archive', False), ('schedule_restore', True)]:
            timetable.save_slot(dict(action=action, slot_id=row['id'], revision=row['revision']), 'gilberto')
            row = timetable.slots(class_id=self.classes['4201'], include_archived=True)[0]
            self.assertEqual(bool(row['active']), active)
        with db.connection() as conn:
            logs = conn.execute("SELECT details FROM activity_log WHERE action LIKE 'schedule_%'").fetchall()
        self.assertEqual(len(logs), 4)
        self.assertEqual(json.loads(logs[1]['details'])['before']['starts_at'], '14:00')

    def test_class_overlap_and_adjacent_boundaries(self):
        self.save()
        with self.assertRaisesRegex(ValueError, 'turma'):
            self.save(starts_at='14:30', ends_at='15:30')
        self.save(starts_at='15:00', ends_at='16:00')
        self.assertEqual(len(timetable.slots(class_id=self.classes['4201'])), 2)

    def test_room_overlap_is_case_insensitive(self):
        self.save(room='Laboratório A')
        with self.assertRaisesRegex(ValueError, 'sala'):
            self.save('4202', room=' laboratório a ')

    def test_teacher_overlap_and_validity(self):
        self.bind('4201'); self.bind('4202')
        self.save()
        with self.assertRaisesRegex(ValueError, 'docente'):
            self.save('4202')
        with db.connection() as conn:
            conn.execute("UPDATE teacher_subjects SET valid_until='2025-12-31' WHERE class_subject_id=?", (self.subjects['4202'],))
        self.save('4202')

    def test_later_teacher_binding_also_checks_existing_schedule(self):
        self.save(); self.save('4202')
        self.bind('4201')
        with self.assertRaisesRegex(ValueError, 'docente'):
            academic_core.mutate('teacher_bind', dict(teacher_username='aline', class_subject_id=self.subjects['4202'], valid_from='2026-01-01'), 'gilberto')
        with db.connection() as conn:
            self.assertFalse(conn.execute('SELECT 1 FROM teacher_subjects WHERE class_subject_id=?', (self.subjects['4202'],)).fetchone())

    def test_bad_input_and_nonexistent_subject_do_not_write(self):
        for changes in [dict(starts_at='26:00'), dict(starts_at='14:00junk'), dict(ends_at='13:00'), dict(weekday='7'), dict(class_subject_id='-1')]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.save(**changes)
        self.assertEqual(timetable.slots(class_id=self.classes['4201']), [])

    def test_stale_edit_and_restore_conflict_are_rejected(self):
        row = self.save()
        timetable.save_slot(dict(action='schedule_archive', slot_id=row['id'], revision=row['revision']), 'gilberto')
        with self.assertRaisesRegex(ValueError, 'outra janela'):
            self.save(slot_id=row['id'], revision=row['revision'])
        self.save('4202', room='Laboratório A')
        with self.assertRaisesRegex(ValueError, 'sala'):
            timetable.save_slot(dict(action='schedule_restore', slot_id=row['id'], revision=2), 'gilberto')
        self.assertFalse(timetable.slots(class_id=self.classes['4201'], include_archived=True)[0]['active'])

    def test_closed_year_is_read_only(self):
        row = self.save()
        with db.connection() as conn:
            conn.execute("UPDATE academic_years SET status='closed'")
        with self.assertRaisesRegex(ValueError, 'encerrados'):
            timetable.save_slot(dict(action='schedule_archive', slot_id=row['id'], revision=row['revision']), 'gilberto')

    def test_student_schedule_uses_enrollment_and_true_empty_state(self):
        self.save()
        self.assertFalse(any(r['class_name']=='4201' for r in timetable.slots(student_id='23081')))
        with db.connection() as conn:
            conn.execute("UPDATE enrollments SET class_id=? WHERE student_id=(SELECT id FROM students WHERE registration='23081') AND status='active'", (self.classes['4201'],))
        self.assertEqual(student_profile('23081')['turma'], '4201')
        rows = timetable.slots(student_id='23081')
        self.assertEqual([r['class_name'] for r in rows], ['4201'])
        schedule = timetable.grid(rows)
        lessons = upcoming_lessons(schedule, datetime(2026,10,18,13,tzinfo=CAMPUS_TZ))
        self.assertEqual(lessons[0]['time'], '14:00')
        with db.connection() as conn:
            conn.execute("UPDATE enrollments SET status='completed' WHERE status='active'")
        self.assertEqual(live_roster(), [])
        self.assertEqual(timetable.slots(student_id='23081'), [])

    def test_teacher_schedule_is_scoped_and_has_actual_class(self):
        self.save(); self.save('4202', starts_at='16:00', ends_at='17:00')
        self.bind('4201')
        rows = timetable.slots(teacher='aline')
        self.assertTrue(any(r['class_name']=='4201' for r in rows))
        self.assertFalse(any(r['class_name']=='4202' for r in rows))
        result = teacher_overview('aline', [dict(class_name='4201', discipline='MAT')], timetable.grid(rows), [], [], [], [], [], datetime(2026,10,18,14,10,tzinfo=CAMPUS_TZ))
        self.assertEqual(result['lessons'][0]['class_name'], '4201')
        self.assertTrue(result['lessons'][0]['live'])

    def test_initial_reference_is_not_reseeded_after_archiving(self):
        rows = timetable.slots(class_id=self.classes['3110'], include_archived=True)
        self.assertTrue(rows)
        with db.connection() as conn:
            conn.execute('UPDATE schedule_slots SET active=FALSE WHERE id=?', (rows[0]['id'],))
        timetable.init_timetable(); timetable.init_timetable()
        again = timetable.slots(class_id=self.classes['3110'], include_archived=True)
        self.assertEqual(len(rows), len(again))
        self.assertEqual(sum(bool(r['active']) for r in again), len(rows)-1)

    def test_http_flow_permissions_csrf_and_preserved_input(self):
        path = '/estrutura?view=schedule&class_id=' + str(self.classes['4201'])
        self.assertEqual(self.client.get(path).status_code, 200)
        data = self.payload()
        data.update(token='bad', return_view='schedule', filter_class_id=self.classes['4201'])
        self.assertEqual(self.client.post(path, data=data).status_code, 400)
        data['token'] = 'test-token'
        response = self.client.post(path, data=data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('view=schedule', response.location)
        self.assertEqual(self.client.get(response.location).status_code, 200)
        data['starts_at'] = '14:30'
        response = self.client.post(path, data=data)
        self.assertEqual(response.status_code, 422)
        self.assertIn(b'coreRetry', response.data)
        self.login('aline', 'professor')
        self.assertEqual(self.client.post(path, data=data).status_code, 403)
        self.login('thiago.zotti', 'aluno')
        self.assertEqual(self.client.get(path).status_code, 403)
        self.assertEqual(self.client.get('/horario').status_code, 200)

    def test_new_registration_and_guardian_are_not_limited_to_demo_profiles(self):
        with db.connection() as conn:
            sid = conn.execute("INSERT INTO students(registration,full_name,active) VALUES('new-900','Nome Escolar Real',TRUE) RETURNING id").fetchone()['id']
            conn.execute("INSERT INTO enrollments(student_id,class_id,status,enrolled_on) VALUES(?,?,'active','2026-09-01')", (sid, self.classes['4203']))
            conn.execute("INSERT INTO guardian_links(guardian_username,student_id,relationship) VALUES('responsavel.thiago','new-900','Responsável')")
        profile = student_profile('new-900')
        self.assertEqual(profile['nome'], 'Nome Escolar Real')
        self.assertEqual(profile['turma'], '4203')
        self.assertEqual(profile['grades'], [])
        self.login('responsavel.thiago', 'responsavel')
        response = self.client.get('/painel')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Nome Escolar Real', response.data)


if __name__ == '__main__':
    unittest.main()
