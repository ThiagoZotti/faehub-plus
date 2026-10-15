"""Persisted weekly timetable. No runtime fallback to a demonstration class."""
import json
import re
from datetime import date

import database as db

DAYS = ('Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom')


def init_timetable():
    with db.connection() as conn:
        if not db.using_postgres():
            columns = {row['name'] for row in conn.execute('PRAGMA table_info(schedule_slots)')}
            if 'active' not in columns:
                conn.execute('ALTER TABLE schedule_slots ADD COLUMN active INTEGER NOT NULL DEFAULT 1')
            if 'revision' not in columns:
                conn.execute('ALTER TABLE schedule_slots ADD COLUMN revision INTEGER NOT NULL DEFAULT 1')
        # The existing 3110 reference was supplied by the school/user. Adopt it
        # once, only for that original class and only if no schedule was managed.
        claimed = conn.execute("""INSERT INTO seed_markers(name) VALUES('school_timetable_reference_v1')
                                  ON CONFLICT(name) DO NOTHING RETURNING name""").fetchone()
        if not claimed:
            return
        klass = conn.execute("""SELECT c.id FROM classes c JOIN academic_years y ON y.id=c.academic_year_id
                                WHERE c.code='3110' AND y.name='2026'""").fetchone()
        if not klass or conn.execute('SELECT 1 FROM schedule_slots ss JOIN class_subjects cs ON cs.id=ss.class_subject_id WHERE cs.class_id=? LIMIT 1', (klass['id'],)).fetchone():
            return
        from school_schedule import SCHEDULE_3110
        subjects = {row['code']: row['id'] for row in conn.execute(
            'SELECT cs.id,s.code FROM class_subjects cs JOIN subjects s ON s.id=cs.subject_id WHERE cs.class_id=?', (klass['id'],))}
        aliases = {'Matemática': 'MAT', 'Física': 'FIS', 'Inglês': 'ING', 'Sociologia': 'SOC',
                   'Filosofia': 'FIL', 'Projeto Final': 'PF', 'Química': 'QUI', 'Biologia': 'BIO',
                   'História': 'HIS', 'Português': 'POR', 'Geografia': 'GEO'}
        for index, row in enumerate(SCHEDULE_3110['grade']):
            for weekday, subject in enumerate(row):
                cs_id = subjects.get(aliases.get(subject, subject))
                if cs_id:
                    conn.execute('INSERT INTO schedule_slots(class_subject_id,weekday,starts_at,ends_at) VALUES(?,?,?,?)',
                                 (cs_id, weekday, SCHEDULE_3110['horarios'][index], SCHEDULE_3110['fins'][index]))


def slots(*, class_id=None, student_id=None, teacher=None, include_archived=False):
    where, params = [], []
    if not include_archived:
        where += ["ss.active=TRUE", "c.status='active'", "y.status='active'"]
    if class_id is not None:
        where.append('c.id=?'); params.append(class_id)
    if student_id is not None:
        where.append("EXISTS (SELECT 1 FROM enrollments e JOIN students st ON st.id=e.student_id WHERE e.class_id=c.id AND e.status='active' AND st.registration=? AND st.active=TRUE)")
        params.append(db.canonical_student_id(student_id))
    if teacher is not None:
        where.append("EXISTS (SELECT 1 FROM teacher_subjects ts WHERE ts.class_subject_id=cs.id AND ts.teacher_username=? AND ts.valid_from<=CURRENT_DATE AND (ts.valid_until IS NULL OR ts.valid_until>=CURRENT_DATE))")
        params.append(teacher)
    with db.connection() as conn:
        rows = [dict(r) for r in conn.execute("""SELECT ss.*,cs.class_id,c.code class_name,c.room class_room,
                    s.code subject_code,s.name subject_name,y.id year_id,y.starts_on,y.ends_on,y.status year_status,c.status class_status
                    FROM schedule_slots ss JOIN class_subjects cs ON cs.id=ss.class_subject_id
                    JOIN classes c ON c.id=cs.class_id JOIN academic_years y ON y.id=c.academic_year_id
                    JOIN subjects s ON s.id=cs.subject_id""" + (' WHERE ' + ' AND '.join(where) if where else '') +
                    ' ORDER BY ss.weekday,ss.starts_at,ss.ends_at,ss.id', params)]
        bindings = [dict(r) for r in conn.execute("""SELECT ts.class_subject_id,u.name,ts.teacher_username,
                         ts.valid_from,ts.valid_until FROM teacher_subjects ts JOIN users u ON u.username=ts.teacher_username
                         WHERE u.active=TRUE AND u.role='professor' AND ts.valid_from<=CURRENT_DATE
                         AND (ts.valid_until IS NULL OR ts.valid_until>=CURRENT_DATE)""") ] if rows else []
    for row in rows:
        row['starts_at'], row['ends_at'] = str(row['starts_at'])[:5], str(row['ends_at'])[:5]
        row['subject'] = row['subject_code']
        row['teacher_names'] = ', '.join(sorted({b['name'] for b in bindings if b['class_subject_id'] == row['class_subject_id']}))
        row['room'] = row['room'] or row['class_room'] or ''
    return rows


def grid(rows):
    rows = list(rows)
    times = sorted({(r['starts_at'], r['ends_at']) for r in rows})
    cells = {(r['weekday'], r['starts_at'], r['ends_at']): r for r in rows}
    return dict(dias=list(DAYS), horarios=[t[0] for t in times], fins=[t[1] for t in times], slots=rows,
                grade=[[cells.get((day, start, end), {}).get('subject', '') for day in range(7)] for start, end in times],
                professores=[[cells.get((day, start, end), {}).get('teacher_names', '') for day in range(7)] for start, end in times])


def _time(value):
    value = str(value or '').strip()
    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
        raise ValueError('Informe os horários no formato HH:MM.')
    return value


def _lock(conn):
    if db.using_postgres():
        conn.execute('SELECT pg_advisory_xact_lock(31102026)')
    else:
        conn.execute('UPDATE schedule_slots SET revision=revision WHERE id=-1')


def validate_teacher_binding(conn, teacher, cs_id, valid_from):
    """A later teacher assignment must not bypass timetable conflict checks."""
    _lock(conn)
    date.fromisoformat(valid_from)
    if not conn.execute("SELECT 1 FROM users WHERE username=? AND role='professor' AND active=TRUE", (teacher,)).fetchone():
        raise ValueError('Selecione um professor ativo.')
    rows = [dict(r) for r in conn.execute("""SELECT ss.*,y.starts_on,y.ends_on FROM schedule_slots ss
                JOIN class_subjects cs ON cs.id=ss.class_subject_id JOIN classes c ON c.id=cs.class_id
                JOIN academic_years y ON y.id=c.academic_year_id WHERE ss.active=TRUE
                AND c.status IN ('planning','active') AND y.status IN ('planning','active')""")]
    bindings = conn.execute('SELECT class_subject_id,valid_from,valid_until FROM teacher_subjects WHERE teacher_username=?', (teacher,)).fetchall()
    for mine in (r for r in rows if r['class_subject_id'] == cs_id):
        for binding in bindings:
            if binding['class_subject_id'] == cs_id:
                continue
            for other in (r for r in rows if r['class_subject_id'] == binding['class_subject_id']):
                if mine['weekday'] != other['weekday'] or str(mine['starts_at']) >= str(other['ends_at']) or str(mine['ends_at']) <= str(other['starts_at']):
                    continue
                first = max(str(mine['starts_on']), str(other['starts_on']), valid_from, str(binding['valid_from']))
                last = min(str(mine['ends_on']), str(other['ends_on']), str(binding['valid_until'] or '9999-12-31'))
                if first <= last:
                    raise ValueError('O docente já tem aula nesse intervalo. Ajuste a grade antes de criar o vínculo.')


def save_slot(data, actor):
    """Serialize writers, validate conflicts, and retain before/after audit data."""
    action = data.get('action', 'schedule_save')
    with db.connection() as conn:
        _lock(conn)
        slot_id = int(data.get('slot_id') or 0)
        previous = conn.execute('SELECT * FROM schedule_slots WHERE id=?', (slot_id,)).fetchone() if slot_id else None
        if slot_id and (not previous or previous['revision'] != int(data.get('revision') or 0)):
            raise ValueError('Este horário mudou em outra janela. Atualize a página antes de tentar novamente.')
        cs_id = int(previous['class_subject_id'] if action in {'schedule_archive', 'schedule_restore'} and previous else data.get('class_subject_id') or 0)
        klass = conn.execute("""SELECT cs.class_id,c.room,c.status,y.status year_status,y.starts_on,y.ends_on,s.active subject_active
                   FROM class_subjects cs JOIN classes c ON c.id=cs.class_id JOIN subjects s ON s.id=cs.subject_id
                   JOIN academic_years y ON y.id=c.academic_year_id WHERE cs.id=?""", (cs_id,)).fetchone()
        if not klass or klass['status'] not in {'planning', 'active'} or klass['year_status'] not in {'planning', 'active'}:
            raise ValueError('Escolha uma turma de um ano em planejamento ou ativo. Horários encerrados são preservados.')
        if action not in {'schedule_save', 'schedule_archive', 'schedule_restore'} or (action != 'schedule_save' and not previous):
            raise ValueError('Ação de horário inválida.')
        source = dict(previous) if action in {'schedule_archive', 'schedule_restore'} else data
        weekday = int(source.get('weekday', -1))
        raw_start, raw_end = str(source.get('starts_at', '')), str(source.get('ends_at', ''))
        start, end = _time(raw_start[:5] if action != 'schedule_save' else raw_start), _time(raw_end[:5] if action != 'schedule_save' else raw_end)
        room = str(source.get('room') or '').strip()[:80]
        active = action != 'schedule_archive'
        if not 0 <= weekday <= 6 or start >= end:
            raise ValueError('Escolha um dia válido e um término posterior ao início.')
        if active and not klass['subject_active']:
            raise ValueError('Ative a disciplina antes de publicar seu horário.')
        if active:
            others = conn.execute("""SELECT ss.*,cs.class_id,c.room class_room,y.starts_on,y.ends_on
                FROM schedule_slots ss JOIN class_subjects cs ON cs.id=ss.class_subject_id
                JOIN classes c ON c.id=cs.class_id JOIN academic_years y ON y.id=c.academic_year_id
                WHERE ss.active=TRUE AND ss.id<>? AND ss.weekday=? AND ss.starts_at<? AND ss.ends_at>?
                AND c.status IN ('planning','active') AND y.status IN ('planning','active')
                AND y.starts_on<=? AND y.ends_on>=?""", (slot_id, weekday, end, start, klass['ends_on'], klass['starts_on'])).fetchall()
            bindings = [dict(r) for r in conn.execute('SELECT * FROM teacher_subjects')]
            for other in others:
                if other['class_id'] == klass['class_id']:
                    raise ValueError('A turma já tem uma aula nesse intervalo. Escolha outro horário.')
                other_room = str(other['room'] or other['class_room'] or '').strip().casefold()
                if (room or klass['room'] or '').strip().casefold() and (room or klass['room'] or '').strip().casefold() == other_room:
                    raise ValueError('A sala já está ocupada nesse intervalo.')
                for mine in (b for b in bindings if b['class_subject_id'] == cs_id):
                    for theirs in (b for b in bindings if b['class_subject_id'] == other['class_subject_id'] and b['teacher_username'] == mine['teacher_username']):
                        first = max(str(klass['starts_on']), str(other['starts_on']), str(mine['valid_from']), str(theirs['valid_from']))
                        last = min(str(klass['ends_on']), str(other['ends_on']), str(mine['valid_until'] or '9999-12-31'), str(theirs['valid_until'] or '9999-12-31'))
                        if first <= last:
                            raise ValueError('Um docente vinculado já tem aula nesse intervalo.')
        if previous:
            changed = conn.execute('UPDATE schedule_slots SET class_subject_id=?,weekday=?,starts_at=?,ends_at=?,room=?,active=?,revision=revision+1 WHERE id=? AND revision=?',
                         (cs_id, weekday, start, end, room or None, active, slot_id, previous['revision'])).rowcount
            if changed != 1:
                raise ValueError('O horário foi atualizado por outra pessoa. Recarregue a página.')
        else:
            conn.execute('INSERT INTO schedule_slots(class_subject_id,weekday,starts_at,ends_at,room,active,revision) VALUES(?,?,?,?,?,?,1)',
                         (cs_id, weekday, start, end, room or None, active))
        details = dict(before=dict(previous) if previous else None,
                       after=dict(class_subject_id=cs_id, weekday=weekday, starts_at=start, ends_at=end, room=room, active=active))
        conn.execute('INSERT INTO activity_log(username,action,details) VALUES(?,?,?)',
                     (actor, action, json.dumps(details, ensure_ascii=False, default=str)))
