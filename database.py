"""Persistência do FaeHub+ exclusivamente em Supabase PostgreSQL.

SQLite permanece importado apenas para o migrador e para bancos temporários da
suíte de testes; nunca é usado como fallback da aplicação.
"""

import os
import re
import sqlite3
import sys
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
    # A ausência de python-dotenv será reportada junto das dependências do Postgres.
    pass

DEFAULT_SQLITE_PATH = BASE_DIR / "faehub.db"
DUMMY_PASSWORD_HASH = generate_password_hash('invalid-account-' + os.urandom(32).hex())
DB_PATH = Path(os.getenv("FAEHUB_DATABASE", DEFAULT_SQLITE_PATH))
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
    return "supabase-postgres" if using_postgres() else "unconfigured"


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
        check=ConnectionPool.check_connection,
        timeout=10,
        kwargs={
            "autocommit": False,
            "row_factory": dict_row,
            "prepare_threshold": None,
            "sslmode": sslmode,
            "connect_timeout": 10,
        },
        open=True,
    )
    return _postgres_pool


def _rollback_quietly(conn):
    """Preserve the original failure if a disconnected socket cannot roll back."""
    try:
        conn.rollback()
    except Exception:
        # A failed rollback must never return a potentially dirty connection.
        # Closing also lets the pool discard it and establish a replacement.
        try:
            conn.raw.close() if isinstance(conn, PostgresConnection) else conn.close()
        except Exception:
            pass


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
    elif conn is None and DB_PATH != DEFAULT_SQLITE_PATH:
        # Compatibilidade isolada para testes que substituem DB_PATH por um
        # arquivo temporário. A aplicação real nunca entra neste caminho.
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        if request_owned:
            g.faehub_connection = conn
    elif conn is None:
        raise RuntimeError(
            "Supabase não configurado. Defina FAEHUB_DATABASE_URL no arquivo .env "
            "com a connection string do Session pooler. O fallback SQLite foi removido."
        )
    try:
        yield conn
        # A request reuses one connection. Committing every small repository
        # helper added an extra network round-trip to Supabase after every
        # SELECT. The request teardown now closes the transaction once.
        if not request_owned:
            conn.commit()
    except Exception:
        _rollback_quietly(conn)
        raise
    finally:
        if not request_owned:
            if lease is not None:
                lease.__exit__(*sys.exc_info())
            else:
                conn.close()


def close_request_connection(error=None):
    conn = g.pop("faehub_connection", None)
    lease = g.pop("faehub_connection_lease", None)
    try:
        if conn is not None:
            conn.rollback() if error is not None else conn.commit()
    except Exception:
        _rollback_quietly(conn)
        if error is None:
            raise
    finally:
        # Return the lease even when commit/rollback failed; otherwise each
        # disconnect permanently removes a slot from the pool.
        if lease is not None:
            lease.__exit__(*sys.exc_info())
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


def _ensure_sqlite_column(db, table, column, definition):
    """Add a local compatibility column without rewriting existing data."""
    columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


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
            CREATE TABLE IF NOT EXISTS profile_photos (
                username TEXT PRIMARY KEY REFERENCES users(username) ON DELETE CASCADE,
                content BLOB NOT NULL CHECK(length(content) BETWEEN 1 AND 196608),
                revision TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
            CREATE TABLE IF NOT EXISTS message_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                class_name TEXT,
                created_by TEXT NOT NULL REFERENCES users(username),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS message_group_members (
                group_id INTEGER NOT NULL REFERENCES message_groups(id) ON DELETE CASCADE,
                username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(group_id,username)
            );
            CREATE TABLE IF NOT EXISTS message_receipts (
                message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                delivered_at TEXT,
                read_at TEXT,
                PRIMARY KEY(message_id,username)
            );
            CREATE TABLE IF NOT EXISTS message_reactions (
                message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                emoji TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(message_id,username,emoji)
            );
            CREATE INDEX IF NOT EXISTS message_group_members_user_idx ON message_group_members(username,group_id);
            CREATE INDEX IF NOT EXISTS message_receipts_user_idx ON message_receipts(username,read_at,message_id);
            CREATE INDEX IF NOT EXISTS message_reactions_message_idx ON message_reactions(message_id);
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
            CREATE TABLE IF NOT EXISTS communication_states (
                username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                kind TEXT NOT NULL CHECK(kind IN ('notice','notification')),
                item_key TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                dismissed_at TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(username,kind,item_key)
            );
            CREATE INDEX IF NOT EXISTS communication_states_user_idx
                ON communication_states(username,kind,dismissed_at);
            CREATE TABLE IF NOT EXISTS internships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher TEXT NOT NULL REFERENCES users(username),
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                modality TEXT NOT NULL CHECK(modality IN ('presencial','hibrido','remoto')),
                workload TEXT NOT NULL DEFAULT '',
                requirements TEXT NOT NULL DEFAULT '',
                application_url TEXT,
                application_instructions TEXT NOT NULL DEFAULT '',
                deadline TEXT NOT NULL,
                class_name TEXT NOT NULL DEFAULT '3110',
                archived INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS internships_teacher_idx
                ON internships(teacher, archived, updated_at);
            CREATE INDEX IF NOT EXISTS internships_class_deadline_idx
                ON internships(class_name, archived, deadline);
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
            _ensure_sqlite_column(db, "messages", "deleted_at", "TEXT")
            _ensure_sqlite_column(db, "messages", "deleted_by", "TEXT")
            _ensure_sqlite_column(db, "messages", "group_id", "INTEGER")
            _ensure_sqlite_column(db, "messages", "reply_to_id", "INTEGER")
            _ensure_sqlite_column(db, "messages", "edited_at", "TEXT")
        # O antigo módulo de avatar foi retirado; apaga apenas suas preferências legadas.
        db.execute("DROP TABLE IF EXISTS avatar_styles")
        db.execute("DROP TABLE IF EXISTS avatar_profiles")
        from account_enrollment import init_enrollment, demos_enabled
        init_enrollment(db)
        seed_demos = demos_enabled(db)
        accounts = [
            ("gilberto", "direcao@123", "Gilberto", "diretor", None),
            ("aline", "professora@123", "Profa. Aline", "professor", None),
            ("thiago.zotti", "aluno@123", "Thiago Zotti", "aluno", "23081"),
            ("jonathan.samuel", "aluno@123", "Jonathan Samuel", "aluno", "23092"),
            ("pablo.sousa", "aluno@123", "Pablo Sousa", "aluno", "23104"),
            ("marlon.eduardo", "aluno@123", "Marlon Eduardo", "aluno", "23117"),
        ]
        for username, password, name, role, student_id in (accounts if seed_demos else []):
            if db.execute('SELECT 1 FROM users WHERE username=?', (username,)).fetchone():
                continue
            db.execute(
                "INSERT OR IGNORE INTO users(username,password_hash,name,role,student_id,active) VALUES (?, ?, ?, ?, ?, TRUE)",
                (username, generate_password_hash(password), name, role, student_id),
            )

        # One canonical class conversation is available to the demo cohort.
        group = db.execute(
            "SELECT id FROM message_groups WHERE class_name='3110' ORDER BY id LIMIT 1"
        ).fetchone()
        if not group and seed_demos:
            group = db.execute(
                """INSERT INTO message_groups(name,class_name,created_by)
                   VALUES('Turma 3110','3110','aline') RETURNING id"""
            ).fetchone()
        group_id = group["id"] if group else None
        for username in ('aline','gilberto','thiago.zotti','jonathan.samuel','pablo.sousa','marlon.eduardo'):
            if not group_id or not db.execute('SELECT 1 FROM users WHERE username=?', (username,)).fetchone():
                continue
            db.execute(
                "INSERT OR IGNORE INTO message_group_members(group_id,username) VALUES(?,?)",
                (group_id, username),
            )
        # Existing direct messages receive durable delivery/read receipts.
        db.execute(
            """INSERT OR IGNORE INTO message_receipts(message_id,username,delivered_at,read_at)
               SELECT id,recipient,CASE WHEN is_read THEN created_at END,
                      CASE WHEN is_read THEN created_at END
               FROM messages WHERE group_id IS NULL"""
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
        if not count and seed_demos:
            db.execute("""INSERT INTO exercises(teacher,title,description,discipline,class_name,due_date)
                          VALUES('aline','API de Biblioteca','Crie uma API Flask com rotas para cadastrar, listar e remover livros. Entregue o link do repositório.','LP3','3110','2026-09-18')""")
            db.execute("""INSERT INTO exercises(teacher,title,description,discipline,class_name,due_date)
                          VALUES('aline','Modelo entidade-relacionamento','Modele usuários, empréstimos e acervo, indicando chaves e cardinalidades.','BD','3110','2026-09-22')""")
        _migrate_seed_exercises(db)

    # Keep feature schemas in sync when tests or maintenance scripts create a
    # fresh local database after this module has already been imported.
    from p1_operations import init_operations
    init_operations()
    from academic_core import init_academic_core
    init_academic_core()


def authenticate(username, password):
    with connection() as db:
        row = db.execute(
            """SELECT u.*,COALESCE(ar.role,u.role) AS effective_role FROM users u
               LEFT JOIN account_roles ar ON ar.username=u.username
               LEFT JOIN account_identities ai ON ai.username=u.username
               WHERE (u.username = ? OR (ai.email=? AND ai.verified_at IS NOT NULL))
                 AND u.active = TRUE""", (username, username)
        ).fetchone()
    valid_password = check_password_hash(row["password_hash"] if row else DUMMY_PASSWORD_HASH, password)
    if not row or not valid_password:
        return None
    account = dict(row)
    account["role"] = account.pop("effective_role")
    return account


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
    # Keep the normalized history current while legacy screens are migrated.
    from academic_core import sync_grade
    sync_grade(student_id, discipline, n1, n2)


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
        return [dict(r) for r in db.execute(
            """SELECT u.username,u.name,COALESCE(ar.role,u.role) AS role,u.student_id,u.active
               FROM users u LEFT JOIN account_roles ar ON ar.username=u.username ORDER BY u.name"""
        )]


def create_user(username, password, name, role, student_id=None):
    with connection() as db:
        stored_role = "aluno" if role in {"responsavel", "secretaria", "coordenacao"} else role
        db.execute("INSERT INTO users(username,password_hash,name,role,student_id,active) VALUES(?,?,?,?,?,TRUE)",
                   (username, generate_password_hash(password), name, stored_role, student_id or None))
        if stored_role != role:
            db.execute("INSERT INTO account_roles(username,role) VALUES(?,?)", (username, role))


def toggle_user(username):
    with connection() as db:
        db.execute("UPDATE users SET active = NOT active WHERE username = ?", (username,))


def send_message(sender, recipient, subject, body, *, reply_to_id=None, group_id=None):
    with connection() as db:
        row = db.execute(
            """INSERT INTO messages(sender,recipient,subject,body,reply_to_id,group_id)
               VALUES(?,?,?,?,?,?) RETURNING id""",
            (sender, recipient, subject, body, reply_to_id, group_id),
        ).fetchone()
        message_id = row["id"]
        if group_id:
            recipients = db.execute(
                "SELECT username FROM message_group_members WHERE group_id=? AND username!=?",
                (group_id, sender),
            ).fetchall()
            for member in recipients:
                db.execute(
                    "INSERT OR IGNORE INTO message_receipts(message_id,username) VALUES(?,?)",
                    (message_id, member["username"]),
                )
        else:
            db.execute(
                "INSERT OR IGNORE INTO message_receipts(message_id,username) VALUES(?,?)",
                (message_id, recipient),
            )
        return message_id


def mark_message_read(message_id, username):
    with connection() as db:
        db.execute("UPDATE messages SET is_read=TRUE WHERE id=? AND recipient=?", (message_id, username))
        try:
            db.execute(
                """UPDATE message_receipts SET delivered_at=COALESCE(delivered_at,CURRENT_TIMESTAMP),
                   read_at=CURRENT_TIMESTAMP WHERE message_id=? AND username=?""",
                (message_id, username),
            )
        except sqlite3.OperationalError as exc:
            # Compatibility with small isolated legacy-schema tests.
            if "message_receipts" not in str(exc):
                raise


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


def _enrich_messages(db, rows):
    messages = [dict(row) for row in rows]
    ids = [item["id"] for item in messages]
    if not ids:
        return messages
    placeholders = ",".join("?" for _ in ids)
    reactions = db.execute(
        f"""SELECT message_id,username,emoji FROM message_reactions
            WHERE message_id IN ({placeholders}) ORDER BY created_at""", ids
    ).fetchall()
    by_message = {}
    for reaction in reactions:
        by_message.setdefault(reaction["message_id"], []).append(dict(reaction))
    for message in messages:
        message["reactions"] = by_message.get(message["id"], [])
        summary = {}
        for reaction in message["reactions"]:
            item = summary.setdefault(reaction["emoji"], {"emoji": reaction["emoji"], "count": 0, "users": []})
            item["count"] += 1
            item["users"].append(reaction["username"])
        message["reaction_summary"] = list(summary.values())
    return messages


def get_messages(username):
    with connection() as db:
        rows = db.execute("""SELECT m.*, su.name sender_name, ru.name recipient_name,
                                    reply.body reply_body, reply_sender.name reply_sender_name,
                                    (SELECT COUNT(*) FROM message_receipts mr WHERE mr.message_id=m.id) receipt_count,
                                    (SELECT COUNT(*) FROM message_receipts mr WHERE mr.message_id=m.id AND mr.delivered_at IS NOT NULL) delivered_count,
                                    (SELECT COUNT(*) FROM message_receipts mr WHERE mr.message_id=m.id AND mr.read_at IS NOT NULL) read_count
                             FROM messages m JOIN users su ON su.username=m.sender
                             JOIN users ru ON ru.username=m.recipient
                             LEFT JOIN messages reply ON reply.id=m.reply_to_id
                             LEFT JOIN users reply_sender ON reply_sender.username=reply.sender
                             WHERE m.group_id IS NULL AND (m.sender=? OR m.recipient=?)
                             ORDER BY m.id DESC""", (username, username))
        return _enrich_messages(db, rows)


def list_message_groups(username):
    with connection() as db:
        return [dict(row) for row in db.execute(
            """SELECT g.*,COUNT(gm2.username) member_count,
                      (SELECT COUNT(*) FROM messages m JOIN message_receipts mr ON mr.message_id=m.id
                       WHERE m.group_id=g.id AND mr.username=? AND mr.read_at IS NULL) unread,
                      (SELECT MAX(id) FROM messages WHERE group_id=g.id) last_message_id
               FROM message_groups g JOIN message_group_members gm ON gm.group_id=g.id AND gm.username=?
               JOIN message_group_members gm2 ON gm2.group_id=g.id
               GROUP BY g.id,g.name,g.class_name,g.created_by,g.created_at
               ORDER BY COALESCE((SELECT MAX(id) FROM messages WHERE group_id=g.id),0) DESC""",
            (username, username),
        )]


def message_group_members(group_id):
    with connection() as db:
        return [dict(row) for row in db.execute(
            """SELECT u.username,u.name,COALESCE(ar.role,u.role) role
               FROM message_group_members gm JOIN users u ON u.username=gm.username
               LEFT JOIN account_roles ar ON ar.username=u.username
               WHERE gm.group_id=? AND u.active=TRUE ORDER BY u.name""", (group_id,)
        )]


def message_sync_state(username):
    """Small monotonic snapshot used by the authenticated event stream."""
    with connection() as db:
        row = db.execute(
            """SELECT COALESCE(MAX(m.id),0) latest_id,
                      COALESCE(MAX(COALESCE(m.edited_at,m.deleted_at,m.created_at)),'' ) latest_change,
                      (SELECT COUNT(*) FROM message_receipts mr
                       WHERE mr.username=? AND mr.read_at IS NULL) unread
               FROM messages m WHERE m.sender=? OR m.recipient=? OR EXISTS(
                 SELECT 1 FROM message_group_members gm
                 WHERE gm.group_id=m.group_id AND gm.username=?)""",
            (username, username, username, username),
        ).fetchone()
        return dict(row)


def get_group_messages(group_id, username, *, limit=30, before_id=None):
    with connection() as db:
        member = db.execute(
            "SELECT 1 FROM message_group_members WHERE group_id=? AND username=?",
            (group_id, username),
        ).fetchone()
        if not member:
            return []
        params = [group_id]
        before = ""
        if before_id:
            before = " AND m.id<?"
            params.append(before_id)
        params.append(limit)
        rows = db.execute(
            f"""SELECT m.*,su.name sender_name,su.name recipient_name,
                       reply.body reply_body,reply_sender.name reply_sender_name,
                       (SELECT COUNT(*) FROM message_receipts mr WHERE mr.message_id=m.id) receipt_count,
                       (SELECT COUNT(*) FROM message_receipts mr WHERE mr.message_id=m.id AND mr.delivered_at IS NOT NULL) delivered_count,
                       (SELECT COUNT(*) FROM message_receipts mr WHERE mr.message_id=m.id AND mr.read_at IS NOT NULL) read_count
                FROM messages m JOIN users su ON su.username=m.sender
                LEFT JOIN messages reply ON reply.id=m.reply_to_id
                LEFT JOIN users reply_sender ON reply_sender.username=reply.sender
                WHERE m.group_id=?{before} ORDER BY m.id DESC LIMIT ?""",
            tuple(params),
        ).fetchall()
        return list(reversed(_enrich_messages(db, rows)))


def create_message_group(name, class_name, created_by, members):
    clean_name = name.strip()
    if not clean_name or len(clean_name) > 80:
        raise ValueError("Informe um nome de grupo com até 80 caracteres.")
    with connection() as db:
        row = db.execute(
            "INSERT INTO message_groups(name,class_name,created_by) VALUES(?,?,?) RETURNING id",
            (clean_name, class_name or None, created_by),
        ).fetchone()
        group_id = row["id"]
        for member in set(members) | {created_by}:
            db.execute(
                "INSERT OR IGNORE INTO message_group_members(group_id,username) VALUES(?,?)",
                (group_id, member),
            )
        return group_id


def message_visible_to(message_id, username):
    with connection() as db:
        row = db.execute(
            """SELECT m.* FROM messages m
               WHERE m.id=? AND (m.sender=? OR (m.group_id IS NULL AND m.recipient=?) OR
                 (m.group_id IS NOT NULL AND EXISTS(
                    SELECT 1 FROM message_group_members gm WHERE gm.group_id=m.group_id AND gm.username=?)))""",
            (message_id, username, username, username),
        ).fetchone()
        return dict(row) if row else None


def edit_message(message_id, username, body):
    with connection() as db:
        result = db.execute(
            """UPDATE messages SET body=?,edited_at=CURRENT_TIMESTAMP
               WHERE id=? AND sender=? AND deleted_at IS NULL""",
            (body, message_id, username),
        )
        return result.rowcount == 1


def toggle_message_reaction(message_id, username, emoji):
    with connection() as db:
        existing = db.execute(
            "SELECT 1 FROM message_reactions WHERE message_id=? AND username=? AND emoji=?",
            (message_id, username, emoji),
        ).fetchone()
        if existing:
            db.execute(
                "DELETE FROM message_reactions WHERE message_id=? AND username=? AND emoji=?",
                (message_id, username, emoji),
            )
            return False
        db.execute(
            "INSERT INTO message_reactions(message_id,username,emoji) VALUES(?,?,?)",
            (message_id, username, emoji),
        )
        return True


def mark_messages_delivered(username):
    with connection() as db:
        db.execute(
            """UPDATE message_receipts SET delivered_at=COALESCE(delivered_at,CURRENT_TIMESTAMP)
               WHERE username=?""", (username,)
        )


def mark_group_read(username, group_id):
    with connection() as db:
        db.execute(
            """UPDATE message_receipts SET delivered_at=COALESCE(delivered_at,CURRENT_TIMESTAMP),
               read_at=CURRENT_TIMESTAMP WHERE username=? AND message_id IN
               (SELECT id FROM messages WHERE group_id=?)""", (username, group_id)
        )


def mark_thread_read(username, participant):
    """Mark only received messages from one participant as read."""
    with connection() as db:
        db.execute(
            """UPDATE messages SET is_read=TRUE
               WHERE recipient=? AND sender=?""",
            (username, participant),
        )
        db.execute(
            """UPDATE message_receipts SET delivered_at=COALESCE(delivered_at,CURRENT_TIMESTAMP),
               read_at=CURRENT_TIMESTAMP WHERE username=? AND message_id IN
               (SELECT id FROM messages WHERE group_id IS NULL AND sender=? AND recipient=?)""",
            (username, participant, username),
        )


def soft_delete_message(message_id, username):
    """Soft-delete one sent message. Returns True only for its author."""
    with connection() as db:
        result = db.execute(
            """UPDATE messages SET deleted_at=CURRENT_TIMESTAMP,deleted_by=?
               WHERE id=? AND sender=? AND deleted_at IS NULL""",
            (username, message_id, username),
        )
        return result.rowcount == 1


def restore_message(message_id, username):
    """Restore a message only when the same author deleted it."""
    with connection() as db:
        result = db.execute(
            """UPDATE messages SET deleted_at=NULL,deleted_by=NULL
               WHERE id=? AND sender=? AND deleted_by=? AND deleted_at IS NOT NULL""",
            (message_id, username, username),
        )
        return result.rowcount == 1


def get_communication_states(username, kind):
    if kind not in {"notice", "notification"}:
        raise ValueError("Tipo de comunicado inválido.")
    with connection() as db:
        rows = db.execute(
            """SELECT item_key,is_read,dismissed_at FROM communication_states
               WHERE username=? AND kind=?""",
            (username, kind),
        )
        return {row["item_key"]: dict(row) for row in rows}


def set_communication_read(username, kind, item_key, read):
    if kind not in {"notice", "notification"} or not item_key:
        raise ValueError("Comunicado inválido.")
    with connection() as db:
        db.execute(
            """INSERT INTO communication_states(username,kind,item_key,is_read)
               VALUES(?,?,?,?)
               ON CONFLICT(username,kind,item_key) DO UPDATE SET
                 is_read=excluded.is_read, updated_at=CURRENT_TIMESTAMP""",
            (username, kind, item_key, bool(read)),
        )


def dismiss_communication(username, kind, item_key):
    """Soft-dismiss an item only after it has been read."""
    if kind not in {"notice", "notification"} or not item_key:
        raise ValueError("Comunicado inválido.")
    with connection() as db:
        state = db.execute(
            """SELECT is_read FROM communication_states
               WHERE username=? AND kind=? AND item_key=?""",
            (username, kind, item_key),
        ).fetchone()
        if not state or not state["is_read"]:
            raise ValueError("Leia o comunicado antes de descartá-lo.")
        db.execute(
            """UPDATE communication_states SET dismissed_at=CURRENT_TIMESTAMP,
                 updated_at=CURRENT_TIMESTAMP
               WHERE username=? AND kind=? AND item_key=?""",
            (username, kind, item_key),
        )


def restore_communication(username, kind, item_key):
    if kind not in {"notice", "notification"} or not item_key:
        raise ValueError("Comunicado inválido.")
    with connection() as db:
        state = db.execute(
            """SELECT dismissed_at FROM communication_states
               WHERE username=? AND kind=? AND item_key=?""",
            (username, kind, item_key),
        ).fetchone()
        if not state or not state["dismissed_at"]:
            raise ValueError("Comunicado descartado não encontrado.")
        db.execute(
            """UPDATE communication_states SET dismissed_at=NULL,
                 updated_at=CURRENT_TIMESTAMP
               WHERE username=? AND kind=? AND item_key=?""",
            (username, kind, item_key),
        )


def create_exercise(teacher, title, description, discipline, class_name, due_date):
    with connection() as db:
        row = db.execute(
            """INSERT INTO exercises(teacher,title,description,discipline,class_name,due_date)
               VALUES(?,?,?,?,?,?) RETURNING id""",
            (teacher, title, description, discipline, class_name, due_date),
        ).fetchone()
        return row["id"]


def get_exercises(include_archived=False):
    with connection() as db:
        return [dict(r) for r in db.execute("""SELECT e.*, COALESCE(s.archived,FALSE) archived FROM exercises e
            LEFT JOIN exercise_states s ON s.exercise_id=e.id """ +
            ("" if include_archived else " WHERE COALESCE(s.archived,FALSE)=FALSE ") + " ORDER BY due_date, e.id DESC")]


def submit_exercise(exercise_id, student, answer):
    with connection() as db:
        row = db.execute("""INSERT INTO submissions(exercise_id,student,answer) VALUES(?,?,?)
                      ON CONFLICT(exercise_id,student) DO UPDATE SET answer=excluded.answer,
                      submitted_at=CURRENT_TIMESTAMP RETURNING id""",
                         (exercise_id, student, answer)).fetchone()
        return row["id"]


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


def get_internships(teacher=None, class_name=None, include_archived=False, active_on=None):
    """Return opportunities in a portable shape for SQLite and PostgreSQL."""
    conditions = []
    params = []
    if teacher:
        conditions.append("i.teacher=?")
        params.append(teacher)
    if class_name:
        conditions.append("i.class_name=?")
        params.append(class_name)
    if not include_archived:
        conditions.append("i.archived=FALSE")
    if active_on:
        conditions.append("i.deadline>=?")
        params.append(active_on)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    with connection() as db:
        rows = db.execute(
            """SELECT i.*, u.name AS teacher_name
                 FROM internships i
                 JOIN users u ON u.username=i.teacher"""
            + where
            + " ORDER BY i.archived, i.deadline, i.updated_at DESC, i.id DESC",
            tuple(params),
        )
        return [dict(row) for row in rows]


def save_internship(teacher, data, internship_id=None):
    fields = (
        data["company"], data["title"], data["description"], data["location"],
        data["modality"], data["workload"], data["requirements"],
        data["application_url"], data["application_instructions"],
        data["deadline"], data["class_name"],
    )
    with connection() as db:
        if internship_id:
            result = db.execute(
                """UPDATE internships SET company=?,title=?,description=?,location=?,
                   modality=?,workload=?,requirements=?,application_url=?,
                   application_instructions=?,deadline=?,class_name=?,
                   updated_at=CURRENT_TIMESTAMP WHERE id=? AND teacher=?""",
                fields + (internship_id, teacher),
            )
            if result.rowcount != 1:
                raise ValueError("Esta oportunidade não pertence à sua conta.")
            return internship_id
        cursor = db.execute(
            """INSERT INTO internships
               (teacher,company,title,description,location,modality,workload,
                requirements,application_url,application_instructions,deadline,class_name)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (teacher,) + fields,
        )
        return getattr(cursor._cursor, "lastrowid", None) if hasattr(cursor, "_cursor") else None


def archive_internship(internship_id, teacher, archived):
    with connection() as db:
        result = db.execute(
            """UPDATE internships SET archived=?,updated_at=CURRENT_TIMESTAMP
               WHERE id=? AND teacher=?""",
            (bool(archived), internship_id, teacher),
        )
        if result.rowcount != 1:
            raise ValueError("Esta oportunidade não pertence à sua conta.")


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
