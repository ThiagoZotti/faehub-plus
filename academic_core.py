"""Normalized academic foundation shared by SQLite and Supabase PostgreSQL."""

from __future__ import annotations

from datetime import date

import database as db
from school_roster import ROSTER


SUBJECT_SEED = (
    ("MAT", "Matemática"), ("FIS", "Física"), ("ING", "Inglês"),
    ("SOC", "Sociologia"), ("FIL", "Filosofia"), ("POE", "POE"),
    ("BD", "Banco de Dados"), ("PF", "Projeto Final"), ("QUI", "Química"),
    ("LP3", "Linguagem de Programação III"), ("SMAS", "SMAS"),
    ("PDM", "Programação para Dispositivos Móveis"), ("BIO", "Biologia"),
    ("HIS", "História"), ("POR", "Português"), ("GEO", "Geografia"),
)


def init_academic_core():
    """Create the normalized model locally and seed the real 3110 foundation."""
    with db.connection() as conn:
        if not db.using_postgres():
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS academic_years (
              id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE,
              starts_on TEXT NOT NULL,ends_on TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'planning'
              CHECK(status IN ('planning','active','closed','archived')),CHECK(ends_on>=starts_on));
            CREATE TABLE IF NOT EXISTS academic_periods (
              id INTEGER PRIMARY KEY AUTOINCREMENT,academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
              name TEXT NOT NULL,period_number INTEGER NOT NULL,starts_on TEXT NOT NULL,ends_on TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'planning' CHECK(status IN ('planning','open','closed')),
              UNIQUE(academic_year_id,period_number),CHECK(ends_on>=starts_on));
            CREATE TABLE IF NOT EXISTS courses (
              id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT NOT NULL UNIQUE,name TEXT NOT NULL,
              description TEXT,active INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS subjects (
              id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT NOT NULL UNIQUE,name TEXT NOT NULL,
              workload_minutes INTEGER,active INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS classes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,academic_year_id INTEGER NOT NULL REFERENCES academic_years(id),
              course_id INTEGER REFERENCES courses(id),code TEXT NOT NULL,grade_label TEXT,shift TEXT NOT NULL,
              room TEXT,capacity INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'active'
              CHECK(status IN ('planning','active','closed','archived')),UNIQUE(academic_year_id,code));
            CREATE TABLE IF NOT EXISTS class_subjects (
              id INTEGER PRIMARY KEY AUTOINCREMENT,class_id INTEGER NOT NULL REFERENCES classes(id),
              subject_id INTEGER NOT NULL REFERENCES subjects(id),workload_minutes INTEGER,
              UNIQUE(class_id,subject_id));
            CREATE TABLE IF NOT EXISTS students (
              id INTEGER PRIMARY KEY AUTOINCREMENT,registration TEXT NOT NULL UNIQUE,
              user_username TEXT UNIQUE REFERENCES users(username),full_name TEXT NOT NULL,birth_date TEXT,
              active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS enrollments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,student_id INTEGER NOT NULL REFERENCES students(id),
              class_id INTEGER NOT NULL REFERENCES classes(id),status TEXT NOT NULL DEFAULT 'active'
              CHECK(status IN ('active','transferred','withdrawn','completed','cancelled')),
              enrolled_on TEXT NOT NULL DEFAULT CURRENT_DATE,ended_on TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              CHECK(ended_on IS NULL OR ended_on>=enrolled_on));
            CREATE UNIQUE INDEX IF NOT EXISTS enrollments_one_active_student_idx
              ON enrollments(student_id) WHERE status='active';
            CREATE INDEX IF NOT EXISTS enrollments_class_idx ON enrollments(class_id,status);
            CREATE TABLE IF NOT EXISTS teacher_subjects (
              id INTEGER PRIMARY KEY AUTOINCREMENT,teacher_username TEXT NOT NULL REFERENCES users(username),
              class_subject_id INTEGER NOT NULL REFERENCES class_subjects(id),valid_from TEXT NOT NULL DEFAULT CURRENT_DATE,
              valid_until TEXT,UNIQUE(teacher_username,class_subject_id,valid_from));
            CREATE TABLE IF NOT EXISTS schedule_slots (
              id INTEGER PRIMARY KEY AUTOINCREMENT,class_subject_id INTEGER NOT NULL REFERENCES class_subjects(id),
              weekday INTEGER NOT NULL,starts_at TEXT NOT NULL,ends_at TEXT NOT NULL,room TEXT,
              UNIQUE(class_subject_id,weekday,starts_at));
            CREATE TABLE IF NOT EXISTS assessments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,class_subject_id INTEGER NOT NULL REFERENCES class_subjects(id),
              academic_period_id INTEGER NOT NULL REFERENCES academic_periods(id),title TEXT NOT NULL,
              assessment_type TEXT NOT NULL,max_score REAL NOT NULL DEFAULT 10,weight REAL NOT NULL DEFAULT 1,
              due_on TEXT,published_at TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(class_subject_id,academic_period_id,title));
            CREATE TABLE IF NOT EXISTS assessment_scores (
              id INTEGER PRIMARY KEY AUTOINCREMENT,assessment_id INTEGER NOT NULL REFERENCES assessments(id),
              enrollment_id INTEGER NOT NULL REFERENCES enrollments(id),score REAL,status TEXT NOT NULL DEFAULT 'pending',
              feedback TEXT,published_at TEXT,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(assessment_id,enrollment_id));
            CREATE TABLE IF NOT EXISTS lessons (
              id INTEGER PRIMARY KEY AUTOINCREMENT,class_subject_id INTEGER NOT NULL REFERENCES class_subjects(id),
              teacher_username TEXT REFERENCES users(username),starts_at TEXT NOT NULL,ends_at TEXT NOT NULL,
              topic TEXT,status TEXT NOT NULL DEFAULT 'scheduled');
            CREATE TABLE IF NOT EXISTS attendance_records (
              id INTEGER PRIMARY KEY AUTOINCREMENT,lesson_id INTEGER NOT NULL REFERENCES lessons(id),
              enrollment_id INTEGER NOT NULL REFERENCES enrollments(id),status TEXT NOT NULL,note TEXT,
              recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,UNIQUE(lesson_id,enrollment_id));
            """)
        _seed(conn)


def _seed(conn):
    # Claim the initial load once, in the same transaction as its data. Existing
    # installations adopt the marker without reapplying demo data to managed rows.
    conn.execute("CREATE TABLE IF NOT EXISTS seed_markers (name TEXT PRIMARY KEY)")
    claimed = conn.execute(
        """INSERT INTO seed_markers(name) VALUES('academic_core_initial_v1')
           ON CONFLICT(name) DO NOTHING RETURNING name"""
    ).fetchone()
    if not claimed:
        return
    if (conn.execute("SELECT 1 FROM students LIMIT 1").fetchone()
            or conn.execute("SELECT 1 FROM enrollments LIMIT 1").fetchone()):
        return
    conn.execute("""INSERT INTO academic_years(name,starts_on,ends_on,status)
                    VALUES('2026','2026-02-02','2026-12-18','active') ON CONFLICT(name) DO NOTHING""")
    year = conn.execute("SELECT id FROM academic_years WHERE name='2026'").fetchone()["id"]
    periods = ((1, "1º trimestre", "2026-02-02", "2026-05-15", "closed"),
               (2, "2º trimestre", "2026-05-18", "2026-08-28", "closed"),
               (3, "3º trimestre", "2026-08-31", "2026-12-18", "open"))
    for number, name, starts, ends, status in periods:
        conn.execute("""INSERT INTO academic_periods(academic_year_id,name,period_number,starts_on,ends_on,status)
                        VALUES(?,?,?,?,?,?) ON CONFLICT(academic_year_id,period_number) DO NOTHING""",
                     (year, name, number, starts, ends, status))
    conn.execute("""INSERT INTO courses(code,name,description,active)
                    VALUES('DS','Desenvolvimento de Sistemas','Curso técnico integrado da ETESC/FAETEC.',TRUE)
                    ON CONFLICT(code) DO NOTHING""")
    for code, name in SUBJECT_SEED:
        conn.execute("INSERT INTO subjects(code,name,active) VALUES(?,?,TRUE) ON CONFLICT(code) DO NOTHING", (code, name))
    course = conn.execute("SELECT id FROM courses WHERE code='DS'").fetchone()["id"]
    conn.execute("""INSERT INTO classes(academic_year_id,course_id,code,grade_label,shift,capacity,status)
                    VALUES(?,?,'3110','3º ano','Manhã',40,'active')
                    ON CONFLICT(academic_year_id,code) DO NOTHING""", (year, course))
    class_id = conn.execute("SELECT id FROM classes WHERE academic_year_id=? AND code='3110'", (year,)).fetchone()["id"]
    for row in conn.execute("SELECT id FROM subjects WHERE active=TRUE"):
        conn.execute("INSERT INTO class_subjects(class_id,subject_id) VALUES(?,?) ON CONFLICT(class_id,subject_id) DO NOTHING", (class_id, row["id"]))
    for person in ROSTER:
        username = conn.execute("SELECT username FROM users WHERE student_id=?", (person["id"],)).fetchone()
        conn.execute("""INSERT INTO students(registration,user_username,full_name,active)
                        VALUES(?,?,?,TRUE) ON CONFLICT(registration) DO NOTHING""",
                     (person["id"], username["username"] if username else None, person["nome"]))
        student_id = conn.execute("SELECT id FROM students WHERE registration=?", (person["id"],)).fetchone()["id"]
        if not conn.execute("SELECT 1 FROM enrollments WHERE student_id=? AND status='active'", (student_id,)).fetchone():
            conn.execute("INSERT INTO enrollments(student_id,class_id,status,enrolled_on) VALUES(?,?,'active','2026-02-02')", (student_id, class_id))


def roster(active_only=True, year_id=None):
    where = ["e.status='active'"] if active_only else []
    params = []
    if year_id:
        where.append("y.id=?"); params.append(year_id)
    clause = "WHERE " + " AND ".join(where) if where else ""
    with db.connection() as conn:
        rows = conn.execute(f"""SELECT s.registration id,s.full_name nome,c.code turma,y.name academic_year,
                               e.status enrollment_status,e.id enrollment_id,s.active
                               FROM enrollments e JOIN students s ON s.id=e.student_id
                               JOIN classes c ON c.id=e.class_id JOIN academic_years y ON y.id=c.academic_year_id
                               {clause} ORDER BY s.full_name""", tuple(params)).fetchall()
    return [dict(row, nota=0, freq=0) for row in rows]


def structure_snapshot():
    with db.connection() as conn:
        years = [dict(r) for r in conn.execute("SELECT * FROM academic_years ORDER BY starts_on DESC")]
        periods = [dict(r) for r in conn.execute("SELECT * FROM academic_periods ORDER BY academic_year_id,period_number")]
        courses = [dict(r) for r in conn.execute("SELECT * FROM courses ORDER BY name")]
        subjects = [dict(r) for r in conn.execute("SELECT * FROM subjects ORDER BY name")]
        classes = [dict(r) for r in conn.execute("""SELECT c.*,y.name academic_year,co.name course_name,
                    (SELECT COUNT(*) FROM enrollments e WHERE e.class_id=c.id AND e.status='active') student_count
                    FROM classes c JOIN academic_years y ON y.id=c.academic_year_id
                    LEFT JOIN courses co ON co.id=c.course_id ORDER BY y.starts_on DESC,c.code""")]
        class_subjects = [dict(r) for r in conn.execute("""SELECT cs.id,cs.class_id,cs.subject_id,s.code,s.name,c.code class_code,y.name academic_year
                    FROM class_subjects cs JOIN subjects s ON s.id=cs.subject_id JOIN classes c ON c.id=cs.class_id
                    JOIN academic_years y ON y.id=c.academic_year_id ORDER BY y.starts_on DESC,c.code,s.name""")]
        students = [dict(r) for r in conn.execute("SELECT * FROM students ORDER BY full_name")]
        enrollments = [dict(r) for r in conn.execute("""SELECT e.*,s.registration,s.full_name,c.code class_code,y.name academic_year
                    FROM enrollments e JOIN students s ON s.id=e.student_id JOIN classes c ON c.id=e.class_id
                    JOIN academic_years y ON y.id=c.academic_year_id ORDER BY y.starts_on DESC,s.full_name""")]
        teachers = [dict(r) for r in conn.execute("SELECT username,name FROM users WHERE role='professor' AND active=TRUE ORDER BY name")]
        bindings = [dict(r) for r in conn.execute("""SELECT ts.*,u.name teacher_name,s.name subject_name,s.code subject_code,
                    c.code class_code,y.name academic_year FROM teacher_subjects ts
                    JOIN users u ON u.username=ts.teacher_username JOIN class_subjects cs ON cs.id=ts.class_subject_id
                    JOIN subjects s ON s.id=cs.subject_id JOIN classes c ON c.id=cs.class_id
                    JOIN academic_years y ON y.id=c.academic_year_id
                    WHERE ts.valid_until IS NULL ORDER BY y.starts_on DESC,c.code,s.name""")]
    return dict(years=years, periods=periods, courses=courses, subjects=subjects, classes=classes,
                class_subjects=class_subjects, students=students, enrollments=enrollments,
                teachers=teachers, bindings=bindings)


def _required(data, name, maximum=160):
    value = str(data.get(name, "")).strip()
    if not value or len(value) > maximum:
        raise ValueError("Preencha os campos obrigatórios dentro dos limites indicados.")
    return value


def _iso(data, name):
    value = _required(data, name, 10)
    try: date.fromisoformat(value)
    except ValueError as exc: raise ValueError("Informe uma data válida.") from exc
    return value


def mutate(action, data, actor):
    """Apply one auditable academic-structure mutation; records are never hard-deleted."""
    with db.connection() as conn:
        if action == "year_create":
            name, starts, ends = _required(data, "name", 30), _iso(data, "starts_on"), _iso(data, "ends_on")
            if ends < starts: raise ValueError("O término do ano deve ser posterior ao início.")
            conn.execute("INSERT INTO academic_years(name,starts_on,ends_on,status) VALUES(?,?,?,'planning')", (name, starts, ends))
        elif action == "year_status":
            year_id, status = int(data.get("year_id", 0)), data.get("status")
            if status not in {"planning", "active", "closed", "archived"}: raise ValueError("Situação do ano inválida.")
            if not conn.execute("SELECT 1 FROM academic_years WHERE id=?", (year_id,)).fetchone():
                raise ValueError("Ano letivo não encontrado.")
            if status == "active":
                unfinished = conn.execute(
                    """SELECT 1 FROM academic_periods p
                       JOIN academic_years y ON y.id=p.academic_year_id
                       WHERE y.status='active' AND y.id<>? AND p.status<>'closed'
                       LIMIT 1""", (year_id,)
                ).fetchone()
                if unfinished:
                    raise ValueError("Feche todos os períodos do ano ativo antes de ativar outro ano letivo.")
                conn.execute("UPDATE academic_years SET status='closed' WHERE status='active' AND id<>?", (year_id,))
            if status == "closed" and conn.execute("SELECT 1 FROM academic_periods WHERE academic_year_id=? AND status<>'closed'", (year_id,)).fetchone():
                raise ValueError("Feche todos os períodos antes de encerrar o ano letivo.")
            if conn.execute("UPDATE academic_years SET status=? WHERE id=?", (status, year_id)).rowcount != 1: raise ValueError("Ano letivo não encontrado.")
        elif action == "period_create":
            year_id, number = int(data.get("year_id", 0)), int(data.get("period_number", 0))
            starts, ends = _iso(data, "starts_on"), _iso(data, "ends_on")
            year = conn.execute("SELECT starts_on,ends_on FROM academic_years WHERE id=?", (year_id,)).fetchone()
            if not year or not (year["starts_on"] <= starts <= ends <= year["ends_on"]): raise ValueError("O período precisa estar dentro do ano letivo.")
            conn.execute("""INSERT INTO academic_periods(academic_year_id,name,period_number,starts_on,ends_on,status)
                            VALUES(?,?,?,?,?,'planning')""", (year_id, _required(data, "name", 80), number, starts, ends))
        elif action == "period_status":
            status = data.get("status")
            if status not in {"planning", "open", "closed"}: raise ValueError("Situação do período inválida.")
            period_id = int(data.get("period_id", 0))
            period = conn.execute("SELECT academic_year_id FROM academic_periods WHERE id=?", (period_id,)).fetchone()
            if not period: raise ValueError("Período não encontrado.")
            if status == "open":
                conn.execute("UPDATE academic_periods SET status='closed' WHERE academic_year_id=? AND status='open' AND id<>?", (period["academic_year_id"], period_id))
            conn.execute("UPDATE academic_periods SET status=? WHERE id=?", (status, period_id))
        elif action == "course_create":
            conn.execute("INSERT INTO courses(code,name,description,active) VALUES(?,?,?,TRUE)",
                         (_required(data, "code", 20).upper(), _required(data, "name"), str(data.get("description", "")).strip()[:1000]))
        elif action == "subject_create":
            workload = int(data.get("workload_minutes") or 0) or None
            conn.execute("INSERT INTO subjects(code,name,workload_minutes,active) VALUES(?,?,?,TRUE)",
                         (_required(data, "code", 20).upper(), _required(data, "name"), workload))
        elif action in {"course_status", "subject_status"}:
            table = "courses" if action == "course_status" else "subjects"
            item_id = int(data.get("item_id", 0)); active = str(data.get("active")) == "1"
            if conn.execute(f"UPDATE {table} SET active=? WHERE id=?", (active, item_id)).rowcount != 1:
                raise ValueError("Cadastro não encontrado.")
        elif action == "class_create":
            shift = data.get("shift"); capacity = int(data.get("capacity", 0))
            if shift not in {"Manhã", "Tarde", "Noite", "Integral"} or not 1 <= capacity <= 500: raise ValueError("Turno ou capacidade inválidos.")
            conn.execute("""INSERT INTO classes(academic_year_id,course_id,code,grade_label,shift,room,capacity,status)
                            VALUES(?,?,?,?,?,?,?,'planning')""", (int(data.get("year_id", 0)), int(data.get("course_id", 0)),
                            _required(data, "code", 30), str(data.get("grade_label", "")).strip()[:50], shift,
                            str(data.get("room", "")).strip()[:80], capacity))
        elif action == "class_subject":
            conn.execute("INSERT INTO class_subjects(class_id,subject_id) VALUES(?,?)",
                         (int(data.get("class_id", 0)), int(data.get("subject_id", 0))))
        elif action == "class_status":
            status = data.get("status"); class_id = int(data.get("class_id", 0))
            if status not in {"planning", "active", "closed", "archived"}: raise ValueError("Situação da turma inválida.")
            if status in {"closed", "archived"} and conn.execute("SELECT 1 FROM enrollments WHERE class_id=? AND status='active'", (class_id,)).fetchone():
                raise ValueError("Encerre as matrículas ativas antes de fechar ou arquivar a turma.")
            if conn.execute("UPDATE classes SET status=? WHERE id=?", (status, class_id)).rowcount != 1: raise ValueError("Turma não encontrada.")
        elif action == "student_create":
            birth = str(data.get("birth_date", "")).strip() or None
            if birth: date.fromisoformat(birth)
            conn.execute("INSERT INTO students(registration,full_name,birth_date,active) VALUES(?,?,?,TRUE)",
                         (_required(data, "registration", 30), _required(data, "full_name"), birth))
        elif action == "enrollment_create":
            student_id, class_id = int(data.get("student_id", 0)), int(data.get("class_id", 0))
            if conn.execute("SELECT 1 FROM enrollments WHERE student_id=? AND status='active'", (student_id,)).fetchone():
                raise ValueError("O estudante já possui uma matrícula ativa. Encerre ou transfira a matrícula atual.")
            enrolled = str(data.get("enrolled_on", "")).strip() or date.today().isoformat()
            date.fromisoformat(enrolled)
            klass = conn.execute("SELECT capacity,(SELECT COUNT(*) FROM enrollments WHERE class_id=? AND status='active') total FROM classes WHERE id=?", (class_id, class_id)).fetchone()
            if not klass or klass["total"] >= klass["capacity"]: raise ValueError("A turma não existe ou atingiu a capacidade.")
            conn.execute("INSERT INTO enrollments(student_id,class_id,status,enrolled_on) VALUES(?,?,'active',?)", (student_id, class_id, enrolled))
        elif action == "enrollment_end":
            status = data.get("status")
            if status not in {"transferred", "withdrawn", "completed", "cancelled"}: raise ValueError("Situação de encerramento inválida.")
            ended = str(data.get("ended_on", "")).strip() or date.today().isoformat(); date.fromisoformat(ended)
            if conn.execute("UPDATE enrollments SET status=?,ended_on=? WHERE id=? AND status='active'", (status, ended, int(data.get("enrollment_id", 0)))).rowcount != 1:
                raise ValueError("Matrícula ativa não encontrada.")
        elif action == "teacher_bind":
            teacher = _required(data, "teacher_username", 50); class_subject_id = int(data.get("class_subject_id", 0))
            conn.execute("INSERT INTO teacher_subjects(teacher_username,class_subject_id,valid_from) VALUES(?,?,?)",
                         (teacher, class_subject_id, str(data.get("valid_from", "")).strip() or date.today().isoformat()))
            legacy = conn.execute("""SELECT c.code class_code,s.code subject_code FROM class_subjects cs
                                   JOIN classes c ON c.id=cs.class_id JOIN subjects s ON s.id=cs.subject_id
                                   WHERE cs.id=?""", (class_subject_id,)).fetchone()
            if legacy:
                conn.execute("INSERT INTO teacher_assignments(teacher,class_name,discipline) VALUES(?,?,?) ON CONFLICT(teacher,class_name,discipline) DO NOTHING",
                             (teacher, legacy["class_code"], legacy["subject_code"]))
        elif action == "teacher_unbind":
            binding_id = int(data.get("binding_id", 0))
            legacy = conn.execute("""SELECT ts.teacher_username,c.code class_code,s.code subject_code FROM teacher_subjects ts
                                   JOIN class_subjects cs ON cs.id=ts.class_subject_id JOIN classes c ON c.id=cs.class_id
                                   JOIN subjects s ON s.id=cs.subject_id WHERE ts.id=?""", (binding_id,)).fetchone()
            if conn.execute("UPDATE teacher_subjects SET valid_until=? WHERE id=? AND valid_until IS NULL", (date.today().isoformat(), binding_id)).rowcount != 1:
                raise ValueError("Vínculo docente ativo não encontrado.")
            if legacy:
                conn.execute("DELETE FROM teacher_assignments WHERE teacher=? AND class_name=? AND discipline=?",
                             (legacy["teacher_username"], legacy["class_code"], legacy["subject_code"]))
        else:
            raise ValueError("Ação acadêmica inválida.")
        audit_label = str(data.get("audit_label") or action).strip()[:200]
        conn.execute("INSERT INTO activity_log(username,action,details) VALUES(?,?,?)", (actor, "estrutura_" + action, audit_label))


def sync_teacher_assignments():
    with db.connection() as conn:
        rows = conn.execute("SELECT teacher,class_name,discipline FROM teacher_assignments").fetchall()
        for row in rows:
            subject = conn.execute("SELECT id FROM subjects WHERE code=? OR name=?", (row["discipline"], row["discipline"])).fetchone()
            cs = conn.execute("""SELECT cs.id FROM class_subjects cs JOIN classes c ON c.id=cs.class_id
                               JOIN academic_years y ON y.id=c.academic_year_id
                               WHERE c.code=? AND y.status='active' AND cs.subject_id=?""", (row["class_name"], subject["id"] if subject else -1)).fetchone()
            if cs:
                conn.execute("""INSERT INTO teacher_subjects(teacher_username,class_subject_id,valid_from)
                                VALUES(?,?,CURRENT_DATE) ON CONFLICT(teacher_username,class_subject_id,valid_from) DO NOTHING""",
                             (row["teacher"], cs["id"]))


def sync_grade(registration, discipline, n1, n2):
    """Dual-write current legacy N1/N2 into the normalized historical model."""
    with db.connection() as conn:
        enrollment = conn.execute("""SELECT e.id,c.id class_id FROM enrollments e JOIN students s ON s.id=e.student_id
                                   JOIN classes c ON c.id=e.class_id JOIN academic_years y ON y.id=c.academic_year_id
                                   WHERE s.registration=? AND e.status='active' AND y.status='active'""", (registration,)).fetchone()
        subject = conn.execute("SELECT id FROM subjects WHERE code=? OR name=?", (discipline, discipline)).fetchone()
        if not enrollment or not subject: return
        cs = conn.execute("SELECT id FROM class_subjects WHERE class_id=? AND subject_id=?", (enrollment["class_id"], subject["id"])).fetchone()
        periods = conn.execute("""SELECT p.id,p.period_number FROM academic_periods p JOIN classes c ON c.academic_year_id=p.academic_year_id
                                WHERE c.id=? AND p.period_number IN (1,2) ORDER BY p.period_number""", (enrollment["class_id"],)).fetchall()
        values = {1: n1, 2: n2}
        for period in periods:
            conn.execute("""INSERT INTO assessments(class_subject_id,academic_period_id,title,assessment_type,max_score,weight,published_at)
                            VALUES(?,?,?,'nota consolidada',10,1,CURRENT_TIMESTAMP)
                            ON CONFLICT(class_subject_id,academic_period_id,title) DO NOTHING""", (cs["id"], period["id"], f"N{period['period_number']}"))
            assessment = conn.execute("SELECT id FROM assessments WHERE class_subject_id=? AND academic_period_id=? AND title=?", (cs["id"], period["id"], f"N{period['period_number']}" )).fetchone()
            conn.execute("""INSERT INTO assessment_scores(assessment_id,enrollment_id,score,status,published_at,updated_at)
                            VALUES(?,? ,?,'graded',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
                            ON CONFLICT(assessment_id,enrollment_id) DO UPDATE SET score=excluded.score,status='graded',published_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP""",
                         (assessment["id"], enrollment["id"], values[period["period_number"]]))


def sync_all_legacy_grades():
    with db.connection() as conn:
        grades = [dict(r) for r in conn.execute("SELECT student_id,discipline,n1,n2 FROM grades")]
    for grade in grades:
        sync_grade(grade["student_id"], grade["discipline"], grade["n1"], grade["n2"])


def student_history(registration):
    with db.connection() as conn:
        enrollments = [dict(r) for r in conn.execute("""SELECT e.id,y.name academic_year,y.status year_status,c.code class_code,
                             c.grade_label,co.name course_name,e.status,e.enrolled_on,e.ended_on
                             FROM enrollments e JOIN students s ON s.id=e.student_id JOIN classes c ON c.id=e.class_id
                             JOIN academic_years y ON y.id=c.academic_year_id LEFT JOIN courses co ON co.id=c.course_id
                             WHERE s.registration=? ORDER BY y.starts_on DESC""", (registration,))]
        for item in enrollments:
            item["subjects"] = [dict(r) for r in conn.execute("""SELECT sub.code,sub.name,p.name period_name,a.title,sc.score,sc.status
                       FROM assessment_scores sc JOIN assessments a ON a.id=sc.assessment_id
                       JOIN academic_periods p ON p.id=a.academic_period_id JOIN class_subjects cs ON cs.id=a.class_subject_id
                       JOIN subjects sub ON sub.id=cs.subject_id WHERE sc.enrollment_id=?
                       ORDER BY sub.name,p.period_number,a.title""", (item["id"],))]
    return enrollments
