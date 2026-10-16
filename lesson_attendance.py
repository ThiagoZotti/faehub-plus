"""Attendance is an actual lesson + enrollment, never a student/date overwrite."""
from datetime import date, datetime, timedelta, timezone
import json
import re

import database as db

CAMPUS_TZ = timezone(timedelta(hours=-3))


def init_lesson_attendance():
    if db.using_postgres():
        return  # Production DDL is versioned in supabase/migrations.
    with db.connection() as conn:
        columns = {r['name'] for r in conn.execute('PRAGMA table_info(lessons)')}
        if 'attendance_revision' not in columns:
            conn.execute('ALTER TABLE lessons ADD COLUMN attendance_revision INTEGER NOT NULL DEFAULT 0')
        conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS lessons_subject_start_idx ON lessons(class_subject_id,starts_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS attendance_enrollment_idx ON attendance_records(enrollment_id,lesson_id)')


def subjects_for(teacher, on_date):
    with db.connection() as conn:
        return [dict(r) for r in conn.execute("""SELECT cs.id,c.id class_id,c.code class_name,
            s.name subject_name,s.code subject_code,y.name academic_year
            FROM class_subjects cs JOIN classes c ON c.id=cs.class_id
            JOIN subjects s ON s.id=cs.subject_id JOIN academic_years y ON y.id=c.academic_year_id
            WHERE c.status='active' AND y.status='active' AND s.active=TRUE
            AND y.starts_on<=? AND y.ends_on>=? AND EXISTS (
              SELECT 1 FROM teacher_subjects ts WHERE ts.class_subject_id=cs.id
              AND ts.teacher_username=? AND ts.valid_from<=? AND (ts.valid_until IS NULL OR ts.valid_until>=?))
            ORDER BY c.code,s.name""", (on_date,on_date,teacher,on_date,on_date))]


def lesson_key(data):
    try:
        day = date.fromisoformat(data.get('data', ''))
        subject_id = int(data.get('class_subject_id', 0))
    except (ValueError, TypeError):
        raise ValueError('Selecione uma disciplina e uma data válidas.') from None
    start, end = data.get('inicio', ''), data.get('fim', '')
    if not all(re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', x) for x in (start, end)) or start >= end:
        raise ValueError('Informe início e fim da aula no mesmo dia, com término depois do início.')
    starts = datetime.fromisoformat(f'{day}T{start}').replace(tzinfo=CAMPUS_TZ)
    ends = datetime.fromisoformat(f'{day}T{end}').replace(tzinfo=CAMPUS_TZ)
    return subject_id, day.isoformat(), starts.isoformat(), ends.isoformat()


def roster(conn, class_id, day):
    # Historical enrollments remain eligible only during their actual interval.
    return [dict(r) for r in conn.execute("""SELECT s.registration id,s.full_name nome,e.id enrollment_id
        FROM enrollments e JOIN students s ON s.id=e.student_id WHERE e.class_id=?
        AND e.status<>'cancelled' AND e.enrolled_on<=? AND (e.ended_on IS NULL OR e.ended_on>=?)
        ORDER BY s.full_name,s.registration""", (class_id,day,day))]


def context(teacher, data):
    subject_id, day, starts, ends = lesson_key(data)
    subject = next((s for s in subjects_for(teacher,day) if s['id']==subject_id), None)
    if not subject:
        raise ValueError('Disciplina ou turma sem vínculo docente vigente nesta data.')
    with db.connection() as conn:
        students = roster(conn,subject['class_id'],day)
        lesson = conn.execute('SELECT * FROM lessons WHERE class_subject_id=? AND starts_at=?', (subject_id,starts)).fetchone()
        saved_rows = conn.execute("""SELECT s.registration,a.status FROM attendance_records a
            JOIN enrollments e ON e.id=a.enrollment_id JOIN students s ON s.id=e.student_id
            WHERE a.lesson_id=?""", (lesson['id'],)).fetchall() if lesson else []
        saved = {r['registration']:{'present':'presente','absent':'ausente'}.get(r['status']) for r in saved_rows}
        return dict(subject=subject,roster=students,attendance=saved,
                    revision=lesson['attendance_revision'] if lesson else 0,
                    registered=len(saved),lesson=dict(lesson) if lesson else None)


def save(teacher, data, marks, now=None):
    subject_id, day, starts, ends = lesson_key(data)
    now = now or datetime.now(CAMPUS_TZ)
    if datetime.fromisoformat(starts) > now:
        raise ValueError('Não é possível registrar presença em uma aula futura.')
    try:
        revision = int(data.get('revision', -1))
    except (TypeError, ValueError):
        raise ValueError('Recarregue a chamada antes de salvar.') from None
    with db.connection() as conn:
        # Structure writes and attendance serialize, including first creation.
        if db.using_postgres():
            conn.execute('SELECT pg_advisory_xact_lock(31102026)')
        else:
            conn.execute('UPDATE lessons SET id=id WHERE id=-1')
        ctx = context(teacher,data)
        subject = ctx['subject']
        lock=' FOR SHARE OF p,c,y' if db.using_postgres() else ''
        periods = conn.execute("""SELECT p.status FROM academic_periods p JOIN classes c
            ON c.academic_year_id=p.academic_year_id JOIN academic_years y ON y.id=c.academic_year_id
            WHERE c.id=? AND c.status='active' AND y.status='active' AND p.starts_on<=? AND p.ends_on>=?"""+lock,
            (subject['class_id'],day,day)).fetchall()
        if len(periods)!=1 or periods[0]['status']!='open':
            raise ValueError('O período desta aula não está aberto. Solicite revisão à coordenação.')
        bindings=conn.execute('''SELECT id FROM teacher_subjects WHERE teacher_username=? AND class_subject_id=?
            AND valid_from<=? AND (valid_until IS NULL OR valid_until>=?)'''+(' FOR SHARE' if db.using_postgres() else ''),
            (teacher,subject_id,day,day)).fetchall()
        if not bindings:
            raise ValueError('O vínculo docente mudou. Consulte a aula novamente.')
        expected = {s['id'] for s in ctx['roster']}
        if not expected or set(marks)!=expected or any(v not in ('presente','ausente') for v in marks.values()):
            raise ValueError('Marque presente ou ausente para todos os alunos desta aula.')
        lesson = ctx['lesson']
        if lesson and (lesson['teacher_username']!=teacher or lesson['status']=='cancelled'):
            raise ValueError('Esta aula pertence a outro professor ou foi cancelada.')
        if ctx['revision']!=revision:
            raise ValueError('A chamada foi alterada em outra janela. Consulte os registros antes de salvar novamente.')
        if lesson and datetime.fromisoformat(str(lesson['ends_at'])) != datetime.fromisoformat(ends):
            raise ValueError('Este início já identifica uma aula com outro término. Consulte a aula original.')
        overlap = conn.execute("""SELECT 1 FROM lessons l JOIN class_subjects cs ON cs.id=l.class_subject_id
            WHERE cs.class_id=? AND l.status<>'cancelled' AND l.starts_at<? AND l.ends_at>?
            AND l.id<>? LIMIT 1""", (subject['class_id'],ends,starts,lesson['id'] if lesson else -1)).fetchone()
        if overlap:
            raise ValueError('Já existe outra aula sobreposta nesta turma. Confira os horários.')
        if not lesson:
            lesson = conn.execute("""INSERT INTO lessons(class_subject_id,teacher_username,starts_at,ends_at,status)
                VALUES(?,?,?,?,'completed') RETURNING id""", (subject_id,teacher,starts,ends)).fetchone()
        updated = conn.execute("""UPDATE lessons SET attendance_revision=attendance_revision+1,status='completed'
            WHERE id=? AND attendance_revision=?""", (lesson['id'],revision))
        if updated.rowcount != 1:
            raise ValueError('A chamada mudou. Consulte os registros antes de salvar novamente.')
        conn.executemany("""INSERT INTO attendance_records(lesson_id,enrollment_id,status) VALUES(?,?,?)
            ON CONFLICT(lesson_id,enrollment_id) DO UPDATE SET status=excluded.status,recorded_at=CURRENT_TIMESTAMP""",
            [(lesson['id'],s['enrollment_id'],{'presente':'present','ausente':'absent'}[marks[s['id']]]) for s in ctx['roster']])
        conn.execute('INSERT INTO activity_log(username,action,details) VALUES(?,?,?)',
            (teacher,'chamada_por_aula',json.dumps(dict(lesson_id=lesson['id'],before=ctx['attendance'],after=marks),ensure_ascii=False)))
        return lesson['id']


def records_for_student(student_id):
    with db.connection() as conn:
        rows = conn.execute("""SELECT l.starts_at,l.ends_at,s.name discipline,a.status,l.id lesson_id
            FROM attendance_records a JOIN lessons l ON l.id=a.lesson_id
            JOIN enrollments e ON e.id=a.enrollment_id JOIN students st ON st.id=e.student_id
            JOIN class_subjects cs ON cs.id=l.class_subject_id JOIN subjects s ON s.id=cs.subject_id
            WHERE st.registration=? AND l.status<>'cancelled' ORDER BY l.starts_at DESC,l.id DESC""", (student_id,)).fetchall()
    result=[]
    for row in rows:
        start=datetime.fromisoformat(str(row['starts_at'])).astimezone(CAMPUS_TZ)
        end=datetime.fromisoformat(str(row['ends_at'])).astimezone(CAMPUS_TZ)
        result.append(dict(row,status={'present':'presente','absent':'ausente'}.get(row['status'],row['status']),
                           class_date=start.date().isoformat(),time_label=f'{start:%H:%M}–{end:%H:%M}',count_unit='aula'))
    return result


def export_records(start='',end=''):
    with db.connection() as conn:
        where=["l.status<>'cancelled'"];params=[]
        if start:
            where.append('l.starts_at>=?');params.append(start+'T00:00:00-03:00')
        if end:
            where.append('l.starts_at<?');params.append((date.fromisoformat(end)+timedelta(days=1)).isoformat()+'T00:00:00-03:00')
        rows=conn.execute('''SELECT student_id,CAST(class_date AS TEXT) class_date,status,'dia' count_unit,
            '' discipline,'' starts_at,'' ends_at FROM attendance WHERE (?='' OR class_date>=?) AND (?='' OR class_date<=?)
            UNION ALL SELECT st.registration,NULL,a.status,'aula',s.name,CAST(l.starts_at AS TEXT),CAST(l.ends_at AS TEXT)
            FROM attendance_records a JOIN lessons l ON l.id=a.lesson_id JOIN enrollments e ON e.id=a.enrollment_id
            JOIN students st ON st.id=e.student_id JOIN class_subjects cs ON cs.id=l.class_subject_id
            JOIN subjects s ON s.id=cs.subject_id WHERE '''+' AND '.join(where),[start,start,end,end,*params]).fetchall()
    result=[]
    for row in rows:
        if row['count_unit']=='dia':
            result.append(dict(row,time_label=''))
            continue
        starts=datetime.fromisoformat(str(row['starts_at'])).astimezone(CAMPUS_TZ)
        ends=datetime.fromisoformat(str(row['ends_at'])).astimezone(CAMPUS_TZ)
        result.append(dict(row,class_date=starts.date().isoformat(),time_label=f'{starts:%H:%M}–{ends:%H:%M}',
                           status={'present':'presente','absent':'ausente'}.get(row['status'],row['status']),count_unit='aula'))
    return sorted(result,key=lambda r:(r['class_date'],r['time_label']),reverse=True)
