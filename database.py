"""Persistência do FaeHub+ com SQLite local ou Supabase PostgreSQL."""

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from flask import g, has_request_context

from werkzeug.security import check_password_hash, generate_password_hash
from school_roster import GENERIC_ACCOUNTS, LEGACY_STUDENT_IDS, canonical_student_id


BASE_DIR = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    # Mantém o modo local disponível antes da primeira instalação de dependências.
    pass

DB_PATH = Path(os.getenv("FAEHUB_DATABASE", BASE_DIR / "faehub.db"))
DATABASE_URL = os.getenv("FAEHUB_DATABASE_URL") or os.getenv("DATABASE_URL")
_postgres_pool = None


class CompatRow(dict):
    """Mapping compatible with sqlite3.Row key and numeric access."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


def _portable_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _portable_row(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return CompatRow((key, _portable_value(value)) for key, value in row.items())
    return row


def _postgres_sql(statement):
    """Translate the small SQLite subset still used by the legacy Flask layer."""
    sql = statement.strip()
    ignore = bool(re.search(r"\binsert\s+or\s+ignore\s+into\b", sql, re.I))
    sql = re.sub(r"\binsert\s+or\s+ignore\s+into\b", "INSERT INTO", sql, flags=re.I)
    sql = sql.replace("strftime('%Y-%m-%d %H:%M:%f','now')", "clock_timestamp()")
    sql = sql.replace("?", "%s")
    if ignore and "on conflict" not in sql.lower():
        sql = sql.rstrip("; ") + " ON CONFLICT DO NOTHING"
    return sql


class PostgresCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def fetchone(self):
        return _portable_row(self._cursor.fetchone())

    def fetchall(self):
        return [_portable_row(row) for row in self._cursor.fetchall()]

    def __iter__(self):
        for row in self._cursor:
            yield _portable_row(row)


class PostgresConnection:
    def __init__(self, raw):
        self.raw = raw

    def execute(self, statement, params=()):
        return PostgresCursor(self.raw.execute(_postgres_sql(statement), params))

    def executemany(self, statement, params):
        cursor = self.raw.cursor()
        cursor.executemany(_postgres_sql(statement), params)
        return PostgresCursor(cursor)

    def executescript(self, script):
        for statement in script.split(";"):
            if statement.strip():
                self.raw.execute(_postgres_sql(statement))

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()


def using_postgres():
    return bool(DATABASE_URL)


def database_backend():
    return "supabase-postgres" if using_postgres() else "sqlite"


def is_integrity_error(error):
    if isinstance(error, sqlite3.IntegrityError):
        return True
    try:
        import psycopg
    except ImportError:
        return False
    return isinstance(error, psycopg.IntegrityError)


def _pool():
    global _postgres_pool
    if _postgres_pool is not None:
        return _postgres_pool
    try:
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool
    except ImportError as exc:
        raise RuntimeError(
            "O PostgreSQL foi configurado, mas as dependências não estão instaladas. "
            "Execute: pip install -r requirements.txt"
        ) from exc
    local = "localhost" in DATABASE_URL or "127.0.0.1" in DATABASE_URL
    sslmode = os.getenv("FAEHUB_DB_SSLMODE", "disable" if local else "require")
    pool_size = max(1, min(int(os.getenv("FAEHUB_DB_POOL_SIZE", "5")), 20))
    _postgres_pool = ConnectionPool(
        conninfo=DATABASE_URL,
        min_size=1,
        max_size=pool_size,
        kwargs={
            "autocommit": False,
            "row_factory": dict_row,
            "prepare_threshold": None,
            "sslmode": sslmode,
        },
        open=True,
    )
    return _postgres_pool


@contextmanager
def connection():
    request_owned = has_request_context()
    conn = getattr(g, "faehub_connection", None) if request_owned else None
    lease = None
    if conn is None and using_postgres():
        lease = _pool().connection()
        conn = PostgresConnection(lease.__enter__())
        if request_owned:
            g.faehub_connection = conn
            g.faehub_connection_lease = lease
    elif conn is None:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        if request_owned:
            g.faehub_connection = conn
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if not request_owned:
            if lease is not None:
                lease.__exit__(None, None, None)
            else:
                conn.close()


def close_request_connection(error=None):
    conn = g.pop("faehub_connection", None)
    lease = g.pop("faehub_connection_lease", None)
    if lease is not None:
        lease.__exit__(None, None, None)
    elif conn is not None:
        conn.close()


def _migrate_legacy_student_ids(db):
    """Move active records to canonical IDs after archiving every legacy row."""
    for legacy_id, current_id in LEGACY_STUDENT_IDS.items():
        attendance = db.execute(
            'SELECT class_date,status FROM attendance WHERE student_id=?', (legacy_id,)
        ).fetchall()
        for row in attendance:
            db.execute(
                '''INSERT OR IGNORE INTO legacy_attendance_archive
                   (legacy_student_id,canonical_student_id,class_date,status)
                   VALUES(?,?,?,?)''',
                (legacy_id, current_id, row['class_date'], row['status']),
            )
            db.execute(
                '''INSERT OR IGNORE INTO attendance(student_id,class_date,status)
                   VALUES(?,?,?)''',
                (current_id, row['class_date'], row['status']),
            )
        if attendance:
            db.execute('DELETE FROM attendance WHERE student_id=?', (legacy_id,))

        grades = db.execute(
            '''SELECT discipline,n1,n2,updated_at FROM grades
               WHERE student_id=?''', (legacy_id,)
        ).fetchall()
        for row in grades:
            db.execute(
                '''INSERT OR IGNORE INTO legacy_grade_archive
                   (legacy_student_id,canonical_student_id,discipline,n1,n2,source_updated_at)
                   VALUES(?,?,?,?,?,?)''',
                (legacy_id, current_id, row['discipline'], row['n1'], row['n2'], row['updated_at']),
            )
            db.execute(
                '''INSERT INTO grades(student_id,discipline,n1,n2,updated_at)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(student_id,discipline) DO UPDATE SET
                     n1=excluded.n1,n2=excluded.n2,updated_at=excluded.updated_at
                   WHERE excluded.updated_at > grades.updated_at''',
                (current_id, row['discipline'], row['n1'], row['n2'], row['updated_at']),
            )
        if grades:
            db.execute('DELETE FROM grades WHERE student_id=?', (legacy_id,))


def _migrate_seed_exercises(db):
    """Correct only the two original demo records; user-created items stay untouched."""
    db.execute(
        '''UPDATE exercises SET discipline='LP3'
           WHERE teacher='aline' AND class_name='3110'
             AND title='API de Biblioteca' AND discipline='Programação Web' '''
    )
    db.execute(
        '''UPDATE exercises SET discipline='BD'
           WHERE teacher='aline' AND class_name='3110'
             AND title='Modelo entidade-relacionamento' AND discipline='Banco de Dados' '''
    )


def init_db():
    with connection() as db:
        if using_postgres():
            schema = db.execute("SELECT to_regclass('public.users') AS table_name").fetchone()
            if not schema or not schema["table_name"]:
                raise RuntimeError(
                    "O Supabase está conectado, mas a migração inicial ainda não foi aplicada. "
                    "Execute: npx supabase db push"
                )
        else:
            db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('diretor','professor','aluno')),
                student_id TEXT,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS grades (
                student_id TEXT NOT NULL,
                discipline TEXT NOT NULL,
                n1 REAL NOT NULL,
                n2 REAL NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(student_id, discipline)
            );
            CREATE TABLE IF NOT EXISTS attendance (
                student_id TEXT NOT NULL,
                class_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('presente','ausente')),
                PRIMARY KEY(student_id, class_date)
            );
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS institution_settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS class_settings (class_name TEXT PRIMARY KEY,capacity INTEGER,shift TEXT NOT NULL DEFAULT 'Manhã');
            CREATE TABLE IF NOT EXISTS auth_versions (username TEXT PRIMARY KEY REFERENCES users(username),version INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL REFERENCES users(username),
                recipient TEXT NOT NULL REFERENCES users(username),
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher TEXT NOT NULL REFERENCES users(username),
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                discipline TEXT NOT NULL,
                class_name TEXT NOT NULL DEFAULT '3110',
                due_date TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise_id INTEGER NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
                student TEXT NOT NULL REFERENCES users(username),
                answer TEXT NOT NULL,
                submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(exercise_id, student)
            );
            CREATE TABLE IF NOT EXISTS teacher_assignments (
                teacher TEXT NOT NULL REFERENCES users(username),
                class_name TEXT NOT NULL,
                discipline TEXT NOT NULL,
                PRIMARY KEY(teacher,class_name,discipline)
            );
            CREATE TABLE IF NOT EXISTS notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher TEXT NOT NULL REFERENCES users(username),
                class_name TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'normal',
                archived INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS exercise_states (
                exercise_id INTEGER PRIMARY KEY REFERENCES exercises(id),
                archived INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS submission_reviews (
                submission_id INTEGER PRIMARY KEY REFERENCES submissions(id),
                feedback TEXT NOT NULL,
                score REAL NOT NULL,
                answer_snapshot TEXT NOT NULL,
                reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS avatar_styles (
                username TEXT PRIMARY KEY REFERENCES users(username) ON DELETE CASCADE,
                appearance TEXT NOT NULL DEFAULT 'masculine',
                hairstyle TEXT NOT NULL DEFAULT 'short',
                outfit TEXT NOT NULL DEFAULT 'hoodie',
                bottom TEXT NOT NULL DEFAULT 'trousers',
                shoes TEXT NOT NULL DEFAULT 'sneakers'
            );
            CREATE TABLE IF NOT EXISTS avatar_profiles (
                username TEXT PRIMARY KEY REFERENCES users(username) ON DELETE CASCADE,
                skin TEXT NOT NULL DEFAULT '#d7a27d',
                hair TEXT NOT NULL DEFAULT '#172033',
                shirt TEXT NOT NULL DEFAULT '#367cf6',
                accessory TEXT NOT NULL DEFAULT 'none',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS legacy_attendance_archive (
                legacy_student_id TEXT NOT NULL,
                canonical_student_id TEXT NOT NULL,
                class_date TEXT NOT NULL,
                status TEXT NOT NULL,
                migrated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(legacy_student_id, class_date, status)
            );
            CREATE TABLE IF NOT EXISTS legacy_grade_archive (
                legacy_student_id TEXT NOT NULL,
                canonical_student_id TEXT NOT NULL,
                discipline TEXT NOT NULL,
                n1 REAL NOT NULL,
                n2 REAL NOT NULL,
                source_updated_at TEXT NOT NULL,
                migrated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(legacy_student_id, discipline, source_updated_at, n1, n2)
            );
            """
            )
        accounts = [
            ("gilberto", "direcao@123", "Gilberto", "diretor", None),
            ("aline", "professora@123", "Profa. Aline", "professor", None),
            ("thiago.zotti", "aluno@123", "Thiago Zotti", "aluno", "23081"),
            ("jonathan.samuel", "aluno@123", "Jonathan Samuel", "aluno", "23092"),
            ("pablo.sousa", "aluno@123", "Pablo Sousa", "aluno", "23104"),
            ("marlon.eduardo", "aluno@123", "Marlon Eduardo", "aluno", "23117"),
        ]
        for username, password, name, role, student_id in accounts:
            if db.execute('SELECT 1 FROM users WHERE username=?', (username,)).fetchone():
                continue
            db.execute(
                "INSERT OR IGNORE INTO users(username,password_hash,name,role,student_id,active) VALUES (?, ?, ?, ?, ?, TRUE)",
                (username, generate_password_hash(password), name, role, student_id),
            )
        # Contas genéricas criadas por versões anteriores continuam válidas e
        # recebem a matrícula canônica. Em instalações novas, os demais alunos
        # ganham acesso pela central da Direção, com credenciais individuais.
        for student in GENERIC_ACCOUNTS:
            existing = db.execute(
                'SELECT student_id FROM users WHERE username=?', (student['username'],)
            ).fetchone()
            if existing and existing['student_id'] in (None, '', student['legacy_id']):
                db.execute(
                    'UPDATE users SET student_id=? WHERE username=?',
                    (student['student_id'], student['username']),
                )

        _migrate_legacy_student_ids(db)
        count = db.execute("SELECT COUNT(*) total FROM exercises").fetchone()["total"]
        if not count:
            db.execute("""INSERT INTO exercises(teacher,title,description,discipline,class_name,due_date)
                          VALUES('aline','API de Biblioteca','Crie uma API Flask com rotas para cadastrar, listar e remover livros. Entregue o link do repositório.','LP3','3110','2026-09-18')""")
            db.execute("""INSERT INTO exercises(teacher,title,description,discipline,class_name,due_date)
                          VALUES('aline','Modelo entidade-relacionamento','Modele usuários, empréstimos e acervo, indicando chaves e cardinalidades.','BD','3110','2026-09-22')""")
        _migrate_seed_exercises(db)


def authenticate(username, password):
    with connection() as db:
        row = db.execute(
            "SELECT * FROM users WHERE username = ? AND active = TRUE", (username,)
        ).fetchone()
    return dict(row) if row and check_password_hash(row["password_hash"], password) else None


def save_grade(student_id, discipline, n1, n2):
    student_id = canonical_student_id(student_id)
    with connection() as db:
        db.execute(
            """INSERT INTO grades(student_id, discipline, n1, n2)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(student_id, discipline) DO UPDATE SET
               n1=excluded.n1, n2=excluded.n2, updated_at=CURRENT_TIMESTAMP""",
            (student_id, discipline, n1, n2),
        )


def load_grades():
    with connection() as db:
        return [dict(r) for r in db.execute("SELECT * FROM grades")]


def save_attendance_batch(class_date, marks):
    marks = {canonical_student_id(student_id): status for student_id, status in marks.items()}
    with connection() as db:
        db.executemany("""INSERT INTO attendance(student_id,class_date,status) VALUES(?,?,?)
                          ON CONFLICT(student_id,class_date) DO UPDATE SET status=excluded.status""",
                       [(student_id,class_date,status) for student_id,status in marks.items()])


def save_attendance(student_id, class_date, status):
    student_id = canonical_student_id(student_id)
    with connection() as db:
        db.execute(
            """INSERT INTO attendance(student_id, class_date, status)
               VALUES (?, ?, ?)
               ON CONFLICT(student_id, class_date) DO UPDATE SET status=excluded.status""",
            (student_id, class_date, status),
        )


def student_attendance(student_id):
    student_id = canonical_student_id(student_id)
    with connection() as db:
        return [dict(row) for row in db.execute(
            'SELECT class_date, status FROM attendance WHERE student_id = ? ORDER BY class_date DESC',
            (student_id,))]


def load_attendance(class_date):
    with connection() as db:
        rows = db.execute(
            "SELECT student_id, status FROM attendance WHERE class_date = ?", (class_date,)
        )
        return {r["student_id"]: r["status"] for r in rows}


def log_action(username, action, details=""):
    with connection() as db:
        db.execute(
            "INSERT INTO activity_log(username, action, details) VALUES (?, ?, ?)",
            (username, action, details),
        )


def recent_logs(limit=8):
    with connection() as db:
        return [dict(r) for r in db.execute(
            "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (limit,)
        )]


def list_users():
    with connection() as db:
        return [dict(r) for r in db.execute("SELECT username, name, role, student_id, active FROM users ORDER BY name")]


def create_user(username, password, name, role, student_id=None):
    with connection() as db:
        db.execute("INSERT INTO users(username,password_hash,name,role,student_id,active) VALUES(?,?,?,?,?,TRUE)",
                   (username, generate_password_hash(password), name, role, student_id or None))


def toggle_user(username):
    with connection() as db:
        db.execute("UPDATE users SET active = NOT active WHERE username = ?", (username,))


def send_message(sender, recipient, subject, body):
    with connection() as db:
        db.execute("INSERT INTO messages(sender,recipient,subject,body) VALUES(?,?,?,?)", (sender, recipient, subject, body))


def mark_message_read(message_id, username):
    with connection() as db:
        db.execute("UPDATE messages SET is_read=TRUE WHERE id=? AND recipient=?", (message_id, username))


def get_teacher_assignments(username):
    with connection() as db:
        return [dict(row) for row in db.execute(
            "SELECT class_name,discipline FROM teacher_assignments WHERE teacher=? ORDER BY class_name,discipline", (username,))]


def seed_teacher_assignments():
    with connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS seed_markers (name TEXT PRIMARY KEY)')
        if db.execute("SELECT 1 FROM seed_markers WHERE name='teacher_assignments'").fetchone():return
        for discipline in ('Projeto Final','LP3'):
            db.execute("INSERT OR IGNORE INTO teacher_assignments(teacher,class_name,discipline) VALUES('aline','3110',?)", (discipline,))
        db.execute("INSERT INTO seed_markers VALUES('teacher_assignments')")


def get_messages(username):
    with connection() as db:
        rows = db.execute("""SELECT m.*, su.name sender_name, ru.name recipient_name
                             FROM messages m JOIN users su ON su.username=m.sender
                             JOIN users ru ON ru.username=m.recipient
                             WHERE sender=? OR recipient=? ORDER BY m.id DESC""", (username, username))
        return [dict(r) for r in rows]


def create_exercise(teacher, title, description, discipline, class_name, due_date):
    with connection() as db:
        db.execute("INSERT INTO exercises(teacher,title,description,discipline,class_name,due_date) VALUES(?,?,?,?,?,?)",
                   (teacher, title, description, discipline, class_name, due_date))


def get_exercises(include_archived=False):
    with connection() as db:
        return [dict(r) for r in db.execute("""SELECT e.*, COALESCE(s.archived,FALSE) archived FROM exercises e
            LEFT JOIN exercise_states s ON s.exercise_id=e.id """ +
            ("" if include_archived else " WHERE COALESCE(s.archived,FALSE)=FALSE ") + " ORDER BY due_date, e.id DESC")]


def submit_exercise(exercise_id, student, answer):
    with connection() as db:
        db.execute("""INSERT INTO submissions(exercise_id,student,answer) VALUES(?,?,?)
                      ON CONFLICT(exercise_id,student) DO UPDATE SET answer=excluded.answer, submitted_at=CURRENT_TIMESTAMP""",
                   (exercise_id, student, answer))


def get_submissions(username=None):
    with connection() as db:
        sql = """SELECT s.*, r.feedback, r.score, r.answer_snapshot, r.reviewed_at,
                 u.name student_name FROM submissions s JOIN users u ON u.username=s.student
                 LEFT JOIN submission_reviews r ON r.submission_id=s.id""" + (" WHERE student=?" if username else "")
        rows = db.execute(sql, (username,) if username else ())
        return [dict(r) for r in rows]


def get_notices():
    with connection() as db:
        return [dict(r) for r in db.execute('SELECT * FROM notices ORDER BY updated_at DESC,id DESC')]


def save_notice(teacher, class_name, title, body, priority, notice_id=None):
    with connection() as db:
        if notice_id:
            result=db.execute('UPDATE notices SET title=?,body=?,priority=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND teacher=?',
                              (title,body,priority,notice_id,teacher))
            if result.rowcount!=1:raise ValueError('Comunicado não pertence à sua conta.')
        else:
            db.execute('INSERT INTO notices(teacher,class_name,title,body,priority) VALUES(?,?,?,?,?)',
                       (teacher,class_name,title,body,priority))


def archive_notice(notice_id, teacher, archived):
    with connection() as db:
        result=db.execute('UPDATE notices SET archived=? WHERE id=? AND teacher=?',(bool(archived),notice_id,teacher))
        if result.rowcount!=1:raise ValueError('Comunicado não pertence à sua conta.')


def edit_exercise(exercise_id, teacher, title, description, due_date):
    with connection() as db:
        result=db.execute('UPDATE exercises SET title=?,description=?,due_date=? WHERE id=? AND teacher=?',
                          (title,description,due_date,exercise_id,teacher))
        if result.rowcount!=1:raise ValueError('Atividade não pertence à sua conta.')


def archive_exercise(exercise_id, teacher, archived):
    with connection() as db:
        if not db.execute('SELECT 1 FROM exercises WHERE id=? AND teacher=?',(exercise_id,teacher)).fetchone():
            raise ValueError('Atividade não pertence à sua conta.')
        db.execute('INSERT INTO exercise_states VALUES(?,?) ON CONFLICT(exercise_id) DO UPDATE SET archived=excluded.archived',
                   (exercise_id,bool(archived)))


def review_submission(submission_id, teacher, feedback, score, expected_answer):
    with connection() as db:
        row=db.execute('''SELECT s.answer FROM submissions s JOIN exercises e ON e.id=s.exercise_id
                           WHERE s.id=? AND e.teacher=?''',(submission_id,teacher)).fetchone()
        if not row:raise ValueError('Entrega não pertence às suas atividades.')
        if row['answer']!=expected_answer:raise ValueError('O aluno atualizou a resposta. Reabra a entrega antes de corrigir.')
        db.execute('''INSERT INTO submission_reviews(submission_id,feedback,score,answer_snapshot) VALUES(?,?,?,?)
            ON CONFLICT(submission_id) DO UPDATE SET feedback=excluded.feedback,score=excluded.score,
            answer_snapshot=excluded.answer_snapshot,
            reviewed_at=strftime('%Y-%m-%d %H:%M:%f','now')''',
            (submission_id,feedback,score,row['answer']))


def get_avatar(username):
    with connection() as db:
        row = db.execute("SELECT skin, hair, shirt, accessory FROM avatar_profiles WHERE username=?", (username,)).fetchone()
        style = db.execute("SELECT appearance, hairstyle, outfit, bottom, shoes FROM avatar_styles WHERE username=?", (username,)).fetchone()
    result = dict(row) if row else {"skin": "#d7a27d", "hair": "#172033", "shirt": "#367cf6", "accessory": "none"}
    result.update(dict(style) if style else dict(appearance='masculine', hairstyle='short', outfit='hoodie', bottom='trousers', shoes='sneakers'))
    return result


def save_avatar(username, skin, hair, shirt, accessory, style=None):
    with connection() as db:
        db.execute("""INSERT INTO avatar_profiles(username,skin,hair,shirt,accessory)
                      VALUES(?,?,?,?,?)
                      ON CONFLICT(username) DO UPDATE SET skin=excluded.skin, hair=excluded.hair,
                      shirt=excluded.shirt, accessory=excluded.accessory, updated_at=CURRENT_TIMESTAMP""",
                   (username, skin, hair, shirt, accessory))
        if style:
            db.execute("""INSERT INTO avatar_styles(username,appearance,hairstyle,outfit,bottom,shoes) VALUES(?,?,?,?,?,?)
                          ON CONFLICT(username) DO UPDATE SET appearance=excluded.appearance,hairstyle=excluded.hairstyle,
                          outfit=excluded.outfit,bottom=excluded.bottom,shoes=excluded.shoes""",
                       (username,style['appearance'],style['hairstyle'],style['outfit'],style['bottom'],style['shoes']))
