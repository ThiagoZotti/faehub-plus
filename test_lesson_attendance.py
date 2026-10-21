import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from html.parser import HTMLParser
from unittest.mock import patch

import database as db
import academic_core
import lesson_attendance as attendance
from app import app
from director import init_director,access_version
from academic import attendance_calendar


class LessonAttendanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.base=Path(cls.temp.name)/'base.db'
        with patch.object(db,'DB_PATH',cls.base):
            db.init_db();init_director();db.seed_teacher_assignments();academic_core.sync_teacher_assignments()
            with db.connection() as conn:
                conn.execute("UPDATE teacher_subjects SET valid_from='2026-01-01'")

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.path=Path(self.temp.name)/'case.db';shutil.copyfile(self.base,self.path)
        self.override=patch.object(db,'DB_PATH',self.path);self.override.start()
        self.addCleanup(self.override.stop)
        self.subject=attendance.subjects_for('aline','2026-09-01')[0]
        self.data=dict(data='2026-09-01',class_subject_id=self.subject['id'],inicio='07:00',fim='07:50',revision='0')
        with db.connection() as conn:
            self.students=attendance.roster(conn,self.subject['class_id'],'2026-09-01')
        self.marks={s['id']:'presente' for s in self.students}

    def tearDown(self):self.override.stop()

    def save(self,**changes):
        return attendance.save('aline',dict(self.data,**changes),self.marks,
            now=datetime.fromisoformat('2026-10-16T12:00:00-03:00'))

    def test_two_lessons_same_day_and_correction_are_independent(self):
        self.save();self.marks[self.students[0]['id']]='ausente';self.save(inicio='08:00',fim='08:50')
        records=db.student_attendance(self.students[0]['id'])
        self.assertEqual(len(records),2);self.assertEqual({r['status'] for r in records},{'presente','ausente'})
        self.assertTrue(all(r['discipline'] and r['time_label'] for r in records))
        with self.assertRaisesRegex(ValueError,'outra janela'):self.save()
        self.save(revision='1')
        self.assertEqual([r['status'] for r in db.student_attendance(self.students[0]['id'])],['ausente','ausente'])

    def test_closed_period_future_and_scope(self):
        for changes in (dict(data='2026-03-02'),dict(data='2026-11-10'),dict(class_subject_id='999999')):
            with self.assertRaises(ValueError):self.save(**changes)
        with self.assertRaisesRegex(ValueError,'vínculo'):
            attendance.save('gilberto',self.data,self.marks)

    def test_roster_and_invalid_status_fail_without_partial_rows(self):
        for marks in ({},dict(self.marks,bad='presente'),dict(self.marks,**{self.students[0]['id']:'late'})):
            with self.assertRaises(ValueError):attendance.save('aline',self.data,marks)
        with db.connection() as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM lessons').fetchone()[0],0)

    def test_overlap_and_time_change_rejected(self):
        self.save()
        with self.assertRaisesRegex(ValueError,'sobreposta'):self.save(inicio='07:30',fim='08:30')
        with self.assertRaisesRegex(ValueError,'outro término'):self.save(fim='08:00',revision='1')

    def test_enrollment_interval_excludes_new_student_and_former_teacher(self):
        with db.connection() as conn:
            conn.execute('UPDATE enrollments SET enrolled_on=? WHERE id=?',('2026-09-02',self.students[0]['enrollment_id']))
        with self.assertRaisesRegex(ValueError,'todos os alunos'):self.save()
        self.marks.pop(self.students[0]['id']);self.save()
        with db.connection() as conn:
            conn.execute("UPDATE teacher_subjects SET valid_until='2026-08-31' WHERE teacher_username='aline'")
        with self.assertRaisesRegex(ValueError,'vínculo'):self.save(revision='1')

    def test_legacy_kept_separate_and_calendar_mixed(self):
        sid=self.students[0]['id'];db.save_attendance(sid,'2026-08-31','ausente')
        self.assertEqual(db.student_attendance(sid)[0]['count_unit'],'dia')
        self.save();self.marks[sid]='ausente';self.save(inicio='08:00',fim='08:50')
        self.assertEqual(len(db.student_attendance(sid)),2)
        with db.connection() as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM attendance WHERE student_id=?',(sid,)).fetchone()[0],1)
        cal=attendance_calendar(db.student_attendance(sid),'2026-09')
        self.assertEqual(next(d for week in cal['weeks'] for d in week if d and d['day']==1)['status'],'mixed')
        exported=attendance.export_records('2026-08-31','2026-09-01')
        self.assertEqual(len([r for r in exported if r['count_unit']=='aula']),68)
        self.assertEqual(len([r for r in exported if r['count_unit']=='dia']),1)
        self.assertEqual(len(attendance.export_records('2026-09-02','2026-09-03')),0)

    def test_http_real_save_and_csrf(self):
        client=app.test_client()
        with client.session_transaction() as session:
            session.update(username='aline',role='professor',auth_version=access_version('aline'),teacher_token='csrf')
        payload=dict(self.data,turma='3110',token='bad',**{'presenca_'+sid:value for sid,value in self.marks.items()})
        self.assertEqual(client.post('/chamada',data=payload).status_code,400)
        payload['token']='csrf'
        result=client.post('/chamada',data=payload,follow_redirects=True)
        self.assertEqual(result.status_code,200)
        self.assertIn('registros salvos'.encode(),result.data)
        self.assertEqual(len(db.student_attendance(self.students[0]['id'])),1)
        # Stale failures preserve the stale revision instead of silently making
        # a second identical submit overwrite a newer teacher edit.
        stale=client.post('/chamada',data=payload)
        self.assertEqual(stale.status_code,422)
        self.assertIn(b'name="revision" value="0"',stale.data)
        self.assertNotIn(b'tw-primary" type="submit" disabled',stale.data)

    def teacher_client(self):
        client=app.test_client()
        with client.session_transaction() as session:
            session.update(username='aline',role='professor',auth_version=access_version('aline'),teacher_token='csrf')
        return client

    def test_initial_form_can_mark_and_save_without_a_hidden_consultation_gate(self):
        class Controls(HTMLParser):
            def __init__(self):super().__init__();self.form=None;self.controls=[]
            def handle_starttag(self,tag,attrs):
                attrs=dict(attrs)
                if tag=='form':self.form=attrs.get('id')
                if tag in ('input','select','button'):self.controls.append((self.form,tag,attrs))
            def handle_endtag(self,tag):
                if tag=='form':self.form=None
        result=self.teacher_client().get('/chamada?turma=3110&data=2026-09-01')
        self.assertEqual(result.status_code,200)
        parsed=Controls();parsed.feed(result.get_data(as_text=True))
        marks=[attrs for form,tag,attrs in parsed.controls if attrs.get('name','').startswith('presenca_')]
        self.assertEqual(len(marks),len(self.students)*2)
        self.assertTrue(all('disabled' not in attrs for attrs in marks))
        for name in ('class_subject_id','inicio','fim'):
            fields=[(form,attrs) for form,tag,attrs in parsed.controls if attrs.get('name')==name]
            self.assertEqual(len(fields),1)
            self.assertEqual(fields[0][0],'attendanceForm')
            self.assertIn('required',fields[0][1])
        save=next(attrs for form,tag,attrs in parsed.controls if attrs.get('value')=='salvar')
        self.assertNotIn('disabled',save)

    def test_http_consultation_does_not_save_or_require_marks(self):
        client=self.teacher_client()
        result=client.post('/chamada',data=dict(self.data,turma='3110',token='csrf',action='consultar'),follow_redirects=True)
        self.assertEqual(result.status_code,200)
        with db.connection() as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM lessons').fetchone()[0],0)
        self.save()
        result=client.post('/chamada',data=dict(self.data,turma='3110',token='csrf',action='consultar'),follow_redirects=True)
        self.assertEqual(result.status_code,200)
        self.assertIn(b'name="revision" value="1"',result.data)
        self.assertIn(b'value="presente" checked',result.data)
        with db.connection() as conn:
            self.assertEqual(conn.execute('SELECT attendance_revision FROM lessons').fetchone()[0],1)

    def test_missing_time_preserves_marks_and_explains_error_without_saving(self):
        payload=dict(self.data,turma='3110',token='csrf',fim='',action='salvar',
                     **{'presenca_'+sid:value for sid,value in self.marks.items()})
        result=self.teacher_client().post('/chamada',data=payload)
        self.assertEqual(result.status_code,422)
        self.assertIn('Informe início e fim'.encode(),result.data)
        self.assertEqual(result.data.count(b'value="presente" checked'),len(self.students))
        with db.connection() as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM lessons').fetchone()[0],0)

    def test_revision_is_bound_to_the_consulted_lesson(self):
        self.save();self.save(inicio='08:00',fim='08:50')
        wrong_key='|'.join((str(self.subject['id']),'2026-09-01','07:00','07:50'))
        payload=dict(self.data,turma='3110',token='csrf',inicio='08:00',fim='08:50',revision='1',revision_key=wrong_key,
                     **{'presenca_'+sid:'ausente' for sid in self.marks})
        client=self.teacher_client()
        result=client.post('/chamada',data=payload)
        self.assertEqual(result.status_code,422)
        self.assertIn('A aula selecionada mudou'.encode(),result.data)
        self.assertTrue(all(row['status']=='presente' for row in db.student_attendance(self.students[0]['id'])))
        payload['revision_key']='|'.join((str(self.subject['id']),'2026-09-01','08:00','08:50'))
        self.assertEqual(client.post('/chamada',data=payload).status_code,302)
        self.assertEqual({row['status'] for row in db.student_attendance(self.students[0]['id'])},{'presente','ausente'})

    def test_missing_binding_is_actionable_instead_of_a_disabled_roll(self):
        with db.connection() as conn:
            conn.execute("UPDATE teacher_subjects SET valid_until='2026-08-31' WHERE teacher_username='aline'")
        result=self.teacher_client().get('/chamada?turma=3110&data=2026-09-01')
        self.assertEqual(result.status_code,200)
        self.assertIn('Nenhuma disciplina vinculada nesta data'.encode(),result.data)
        self.assertNotIn(b'id="attendanceForm"',result.data)


if __name__=='__main__':unittest.main()
