"""Operações escolares da P1 com persistência SQLite/PostgreSQL portátil."""

from __future__ import annotations

import hashlib
import mimetypes
import secrets
from datetime import date, datetime, timedelta, timezone

from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

import database as db


DOCUMENT_TYPES = {
    "matricula": "Declaração de matrícula",
    "frequencia": "Declaração de frequência",
    "historico": "Histórico escolar",
    "ficha": "Ficha individual",
}
EVENT_TYPES = {
    "evento": "Evento escolar",
    "feriado": "Feriado",
    "recesso": "Recesso",
    "avaliacao": "Período de avaliação",
    "reuniao": "Reunião",
    "conselho": "Conselho de classe",
}
ATTACHMENT_MIMES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/plain",
    "application/zip",
    "application/x-zip-compressed",
}
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024


def init_operations():
    """Create the local fallback schema; Supabase uses versioned migrations."""
    with db.connection() as conn:
        if not db.using_postgres():
            conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS account_roles (
              username TEXT PRIMARY KEY REFERENCES users(username) ON DELETE CASCADE,
              role TEXT NOT NULL CHECK(role IN ('responsavel','secretaria','coordenacao'))
            );
            CREATE TABLE IF NOT EXISTS guardian_links (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              guardian_username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
              student_id TEXT NOT NULL,
              relationship TEXT NOT NULL,
              active INTEGER NOT NULL DEFAULT 1,
              UNIQUE(guardian_username,student_id)
            );
            CREATE INDEX IF NOT EXISTS guardian_links_student_idx ON guardian_links(student_id,active);
            CREATE TABLE IF NOT EXISTS academic_years (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE,
              starts_on TEXT NOT NULL,
              ends_on TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'planning' CHECK(status IN ('planning','active','closed','archived'))
            );
            CREATE TABLE IF NOT EXISTS academic_periods (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              academic_year_id INTEGER NOT NULL REFERENCES academic_years(id) ON DELETE CASCADE,
              name TEXT NOT NULL,
              period_number INTEGER NOT NULL,
              starts_on TEXT NOT NULL,
              ends_on TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'planning' CHECK(status IN ('planning','open','closed')),
              UNIQUE(academic_year_id,period_number)
            );
            CREATE TABLE IF NOT EXISTS period_closure_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              period_id INTEGER NOT NULL REFERENCES academic_periods(id),
              action TEXT NOT NULL CHECK(action IN ('close','reopen')),
              actor TEXT NOT NULL REFERENCES users(username),
              reason TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS period_closure_log_period_idx ON period_closure_log(period_id,created_at);
            CREATE TABLE IF NOT EXISTS class_diary_entries (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              teacher TEXT NOT NULL REFERENCES users(username),
              class_name TEXT NOT NULL,
              discipline TEXT NOT NULL,
              lesson_date TEXT NOT NULL,
              content TEXT NOT NULL,
              objectives TEXT NOT NULL,
              methodology TEXT NOT NULL DEFAULT '',
              resources TEXT NOT NULL DEFAULT '',
              homework TEXT NOT NULL DEFAULT '',
              observations TEXT NOT NULL DEFAULT '',
              class_hours INTEGER NOT NULL DEFAULT 2 CHECK(class_hours BETWEEN 1 AND 12),
              status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','submitted','validated','returned')),
              coordinator_note TEXT NOT NULL DEFAULT '',
              validated_by TEXT REFERENCES users(username),
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS diary_teacher_date_idx ON class_diary_entries(teacher,lesson_date DESC);
            CREATE INDEX IF NOT EXISTS diary_status_idx ON class_diary_entries(status,lesson_date DESC);
            CREATE TABLE IF NOT EXISTS document_requests (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              requester TEXT NOT NULL REFERENCES users(username),
              student_id TEXT NOT NULL,
              document_type TEXT NOT NULL,
              purpose TEXT NOT NULL DEFAULT '',
              status TEXT NOT NULL DEFAULT 'requested' CHECK(status IN ('requested','processing','ready','delivered','rejected')),
              protocol TEXT NOT NULL UNIQUE,
              verification_code TEXT NOT NULL,
              note TEXT NOT NULL DEFAULT '',
              requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS document_requests_student_idx ON document_requests(student_id,status,requested_at DESC);
            CREATE TABLE IF NOT EXISTS pedagogical_interventions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              student_id TEXT NOT NULL,
              opened_by TEXT NOT NULL REFERENCES users(username),
              category TEXT NOT NULL,
              summary TEXT NOT NULL,
              plan TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','monitoring','closed')),
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS interventions_student_idx ON pedagogical_interventions(student_id,status,updated_at DESC);
            CREATE TABLE IF NOT EXISTS notifications (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              recipient TEXT REFERENCES users(username),
              role_target TEXT,
              title TEXT NOT NULL,
              body TEXT NOT NULL,
              category TEXT NOT NULL DEFAULT 'sistema',
              action_url TEXT NOT NULL DEFAULT '',
              created_by TEXT REFERENCES users(username),
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              expires_at TEXT
            );
            CREATE INDEX IF NOT EXISTS notifications_recipient_idx ON notifications(recipient,created_at DESC);
            CREATE INDEX IF NOT EXISTS notifications_role_idx ON notifications(role_target,created_at DESC);
            CREATE TABLE IF NOT EXISTS notification_reads (
              notification_id INTEGER NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
              username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
              read_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY(notification_id,username)
            );
            CREATE TABLE IF NOT EXISTS calendar_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              description TEXT NOT NULL DEFAULT '',
              starts_at TEXT NOT NULL,
              ends_at TEXT NOT NULL,
              event_type TEXT NOT NULL,
              audience TEXT NOT NULL DEFAULT 'todos',
              class_name TEXT NOT NULL DEFAULT '',
              location TEXT NOT NULL DEFAULT '',
              created_by TEXT NOT NULL REFERENCES users(username),
              status TEXT NOT NULL DEFAULT 'published' CHECK(status IN ('published','cancelled')),
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS calendar_events_start_idx ON calendar_events(starts_at,status);
            CREATE TABLE IF NOT EXISTS password_recovery_requests (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL REFERENCES users(username),
              token_hash TEXT,
              status TEXT NOT NULL DEFAULT 'requested' CHECK(status IN ('requested','issued','used','expired')),
              requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              expires_at TEXT,
              issued_by TEXT REFERENCES users(username),
              used_at TEXT
            );
            CREATE INDEX IF NOT EXISTS password_recovery_status_idx ON password_recovery_requests(status,requested_at DESC);
            CREATE TABLE IF NOT EXISTS file_attachments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              owner TEXT NOT NULL REFERENCES users(username),
              entity_type TEXT NOT NULL CHECK(entity_type IN ('message','exercise','submission')),
              entity_id INTEGER NOT NULL,
              filename TEXT NOT NULL,
              mime_type TEXT NOT NULL,
              size_bytes INTEGER NOT NULL CHECK(size_bytes > 0),
              content BLOB NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS attachments_entity_idx ON file_attachments(entity_type,entity_id);
            """
        )
            conn.execute(
                """INSERT OR IGNORE INTO academic_years(name,starts_on,ends_on,status)
                   VALUES('2026','2026-02-02','2026-12-18','active')"""
            )
            year = conn.execute("SELECT id FROM academic_years WHERE name='2026'").fetchone()
            periods = (
                ("1º trimestre", 1, "2026-02-02", "2026-05-15", "closed"),
                ("2º trimestre", 2, "2026-05-18", "2026-08-28", "closed"),
                ("3º trimestre", 3, "2026-08-31", "2026-12-18", "open"),
            )
            for name, number, starts_on, ends_on, status in periods:
                conn.execute(
                    """INSERT OR IGNORE INTO academic_periods
                       (academic_year_id,name,period_number,starts_on,ends_on,status)
                       VALUES(?,?,?,?,?,?)""",
                    (year["id"], name, number, starts_on, ends_on, status),
                )
        from account_enrollment import demos_enabled
        if demos_enabled(conn) and not conn.execute("SELECT 1 FROM users WHERE username='responsavel.thiago'").fetchone():
            conn.execute(
                """INSERT INTO users(username,password_hash,name,role,student_id,active)
                   VALUES(?,?,?,?,?,TRUE)""",
                (
                    "responsavel.thiago",
                    generate_password_hash("responsavel@123"),
                    "Responsável de Thiago",
                    "aluno",
                    None,
                ),
            )
        conn.execute(
            """INSERT INTO account_roles(username,role) SELECT username,'responsavel' FROM users WHERE username='responsavel.thiago'
               ON CONFLICT(username) DO NOTHING"""
        )
        conn.execute(
            """INSERT INTO guardian_links
               (guardian_username,student_id,relationship) SELECT username,'23081','Responsável legal' FROM users WHERE username='responsavel.thiago'
               ON CONFLICT(guardian_username,student_id) DO NOTHING"""
        )


def list_periods():
    with db.connection() as conn:
        return [dict(row) for row in conn.execute(
            """SELECT p.*,y.name academic_year FROM academic_periods p
               JOIN academic_years y ON y.id=p.academic_year_id
               ORDER BY y.starts_on DESC,p.period_number"""
        )]


def period_is_closed(on_date: str | None = None) -> bool:
    target = on_date or date.today().isoformat()
    with db.connection() as conn:
        row = conn.execute(
            """SELECT status FROM academic_periods
               WHERE starts_on<=? AND ends_on>=? ORDER BY period_number DESC LIMIT 1""",
            (target, target),
        ).fetchone()
    return bool(row and row["status"] == "closed")


def change_period_status(period_id: int, action: str, actor: str, reason: str):
    if action not in {"close", "reopen"}:
        raise ValueError("Ação de período inválida.")
    reason = reason.strip()
    if len(reason) < 5 or len(reason) > 500:
        raise ValueError("Informe o motivo da alteração com 5 a 500 caracteres.")
    status = "closed" if action == "close" else "open"
    with db.connection() as conn:
        result = conn.execute("UPDATE academic_periods SET status=? WHERE id=? AND status<>?", (status, period_id, status))
        if result.rowcount != 1:
            raise ValueError("Período não encontrado ou já está nesta situação.")
        conn.execute(
            "INSERT INTO period_closure_log(period_id,action,actor,reason) VALUES(?,?,?,?)",
            (period_id, action, actor, reason),
        )


def list_period_log():
    with db.connection() as conn:
        return [dict(row) for row in conn.execute(
            """SELECT l.*,p.name period_name,u.name actor_name FROM period_closure_log l
               JOIN academic_periods p ON p.id=l.period_id JOIN users u ON u.username=l.actor
               ORDER BY l.id DESC LIMIT 30"""
        )]


def save_diary_entry(teacher: str, data: dict, entry_id: int | None = None):
    if period_is_closed(data['lesson_date']):
        raise ValueError("O período desta aula está fechado.")
    if entry_id:
        previous = next((row for row in list_diary_entries(teacher) if row['id'] == entry_id), None)
        if not previous or period_is_closed(previous['lesson_date']):
            raise ValueError("Registro indisponível para alteração.")
    fields = (
        data["class_name"], data["discipline"], data["lesson_date"], data["content"],
        data["objectives"], data["methodology"], data["resources"], data["homework"],
        data["observations"], data["class_hours"], data["status"],
    )
    with db.connection() as conn:
        if entry_id:
            result = conn.execute(
                """UPDATE class_diary_entries SET class_name=?,discipline=?,lesson_date=?,content=?,
                   objectives=?,methodology=?,resources=?,homework=?,observations=?,class_hours=?,status=?,
                   coordinator_note='',validated_by=NULL,updated_at=CURRENT_TIMESTAMP
                   WHERE id=? AND teacher=? AND status IN ('draft','returned')""",
                fields + (entry_id, teacher),
            )
            if result.rowcount != 1:
                raise ValueError("Este registro não pode mais ser editado.")
            return entry_id
        row = conn.execute(
            """INSERT INTO class_diary_entries
               (teacher,class_name,discipline,lesson_date,content,objectives,methodology,resources,
                homework,observations,class_hours,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) RETURNING id""",
            (teacher,) + fields,
        ).fetchone()
        return row["id"]


def list_diary_entries(teacher: str | None = None):
    where, params = (" WHERE d.teacher=?", (teacher,)) if teacher else ("", ())
    with db.connection() as conn:
        return [dict(row) for row in conn.execute(
            """SELECT d.*,u.name teacher_name FROM class_diary_entries d
               JOIN users u ON u.username=d.teacher""" + where +
            " ORDER BY d.lesson_date DESC,d.id DESC", params
        )]


def review_diary_entry(entry_id: int, reviewer: str, action: str, note: str):
    if action not in {"validate", "return"}:
        raise ValueError("Revisão inválida.")
    note = note.strip()
    if action == "return" and len(note) < 5:
        raise ValueError("Explique o que o professor precisa ajustar.")
    status = "validated" if action == "validate" else "returned"
    with db.connection() as conn:
        result = conn.execute(
            """UPDATE class_diary_entries SET status=?,coordinator_note=?,validated_by=?,updated_at=CURRENT_TIMESTAMP
               WHERE id=? AND status='submitted'""",
            (status, note, reviewer, entry_id),
        )
        if result.rowcount != 1:
            raise ValueError("O registro não está aguardando validação.")


def create_document_request(requester: str, student_id: str, document_type: str, purpose: str):
    if document_type not in DOCUMENT_TYPES:
        raise ValueError("Selecione um documento válido.")
    purpose = purpose.strip()
    if len(purpose) > 500:
        raise ValueError("A finalidade deve ter até 500 caracteres.")
    protocol = f"FH-{date.today():%Y%m%d}-{secrets.token_hex(3).upper()}"
    verification = secrets.token_hex(4).upper()
    with db.connection() as conn:
        row = conn.execute(
            """INSERT INTO document_requests
               (requester,student_id,document_type,purpose,protocol,verification_code)
               VALUES(?,?,?,?,?,?) RETURNING id""",
            (requester, student_id, document_type, purpose, protocol, verification),
        ).fetchone()
    return row["id"], protocol


def list_document_requests(requester: str | None = None, student_ids: list[str] | None = None):
    if student_ids is not None and not student_ids:
        return []
    clauses, params = [], []
    if requester:
        clauses.append("r.requester=?")
        params.append(requester)
    if student_ids:
        clauses.append("r.student_id IN (" + ",".join("?" for _ in student_ids) + ")")
        params.extend(student_ids)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with db.connection() as conn:
        return [dict(row) for row in conn.execute(
            """SELECT r.*,u.name requester_name FROM document_requests r
               JOIN users u ON u.username=r.requester""" + where +
            " ORDER BY r.id DESC", tuple(params)
        )]


def update_document_request(request_id: int, status: str, note: str):
    if status not in {"processing", "ready", "delivered", "rejected"}:
        raise ValueError("Situação documental inválida.")
    note = note.strip()
    if len(note) > 1000:
        raise ValueError("A observação deve ter até 1.000 caracteres.")
    with db.connection() as conn:
        result = conn.execute(
            """UPDATE document_requests SET status=?,note=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (status, note, request_id),
        )
        if result.rowcount != 1:
            raise ValueError("Solicitação não encontrada.")


def guardian_students(username: str):
    with db.connection() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM guardian_links WHERE guardian_username=? AND active=TRUE ORDER BY student_id",
            (username,),
        )]


def save_intervention(actor: str, student_id: str, category: str, summary: str, plan: str):
    summary, plan = summary.strip(), plan.strip()
    if not student_id or not category or not 5 <= len(summary) <= 1000 or not 5 <= len(plan) <= 3000:
        raise ValueError("Preencha aluno, categoria, registro e plano de acompanhamento.")
    with db.connection() as conn:
        conn.execute(
            """INSERT INTO pedagogical_interventions(student_id,opened_by,category,summary,plan)
               VALUES(?,?,?,?,?)""",
            (student_id, actor, category[:80], summary, plan),
        )


def list_interventions(student_id: str | None = None):
    where, params = (" WHERE i.student_id=?", (student_id,)) if student_id else ("", ())
    with db.connection() as conn:
        return [dict(row) for row in conn.execute(
            """SELECT i.*,u.name opened_by_name FROM pedagogical_interventions i
               JOIN users u ON u.username=i.opened_by""" + where +
            " ORDER BY i.updated_at DESC,i.id DESC", params
        )]


def set_intervention_status(intervention_id: int, status: str):
    if status not in {"open", "monitoring", "closed"}:
        raise ValueError("Situação de acompanhamento inválida.")
    with db.connection() as conn:
        result = conn.execute(
            "UPDATE pedagogical_interventions SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, intervention_id),
        )
        if result.rowcount != 1:
            raise ValueError("Acompanhamento não encontrado.")


def create_notification(title: str, body: str, *, recipient: str | None = None,
                        role_target: str | None = None, category: str = "sistema",
                        action_url: str = "", created_by: str | None = None):
    if not recipient and not role_target:
        raise ValueError("Defina o destinatário da notificação.")
    if action_url and (not action_url.startswith('/') or action_url.startswith('//') or '\\' in action_url):
        raise ValueError("Use um link interno do campus, como /calendario.")
    with db.connection() as conn:
        conn.execute(
            """INSERT INTO notifications
               (recipient,role_target,title,body,category,action_url,created_by)
               VALUES(?,?,?,?,?,?,?)""",
            (recipient, role_target, title[:160], body[:2000], category[:40], action_url[:500], created_by),
        )


def list_notifications(username: str, role: str):
    with db.connection() as conn:
        return [dict(row) for row in conn.execute(
            """SELECT n.*,CASE WHEN r.username IS NULL THEN FALSE ELSE TRUE END is_read
               FROM notifications n LEFT JOIN notification_reads r
                 ON r.notification_id=n.id AND r.username=?
               WHERE (n.recipient=? OR n.role_target=? OR n.role_target='todos')
                 AND (n.expires_at IS NULL OR n.expires_at>=CURRENT_TIMESTAMP)
               ORDER BY n.created_at DESC,n.id DESC LIMIT 100""",
            (username, username, role),
        )]


def mark_notification(notification_id: int, username: str, read: bool, role: str):
    if notification_id not in {item['id'] for item in list_notifications(username, role)}:
        raise ValueError("Notificação indisponível para esta conta.")
    with db.connection() as conn:
        if read:
            conn.execute(
                """INSERT INTO notification_reads(notification_id,username) VALUES(?,?)
                   ON CONFLICT(notification_id,username) DO NOTHING""",
                (notification_id, username),
            )
        else:
            conn.execute(
                "DELETE FROM notification_reads WHERE notification_id=? AND username=?",
                (notification_id, username),
            )


def save_calendar_event(actor: str, data: dict, event_id: int | None = None):
    fields = (
        data["title"], data["description"], data["starts_at"], data["ends_at"],
        data["event_type"], data["audience"], data["class_name"], data["location"],
    )
    with db.connection() as conn:
        if event_id:
            result = conn.execute(
                """UPDATE calendar_events SET title=?,description=?,starts_at=?,ends_at=?,event_type=?,
                   audience=?,class_name=?,location=? WHERE id=?""",
                fields + (event_id,),
            )
            if result.rowcount != 1:
                raise ValueError("Evento não encontrado.")
            return event_id
        row = conn.execute(
            """INSERT INTO calendar_events
               (title,description,starts_at,ends_at,event_type,audience,class_name,location,created_by)
               VALUES(?,?,?,?,?,?,?,?,?) RETURNING id""",
            fields + (actor,),
        ).fetchone()
        return row["id"]


def list_calendar_events(role: str, class_name: str = ""):
    with db.connection() as conn:
        return [dict(row) for row in conn.execute(
            """SELECT e.*,u.name created_by_name FROM calendar_events e
               JOIN users u ON u.username=e.created_by
               WHERE e.status='published' AND
                 (?='admin' OR e.audience='todos' OR e.audience=? OR (e.audience='turma' AND e.class_name=?))
               ORDER BY e.starts_at,e.id""",
            (role, role, class_name),
        )]


def cancel_calendar_event(event_id: int):
    with db.connection() as conn:
        result = conn.execute("UPDATE calendar_events SET status='cancelled' WHERE id=?", (event_id,))
        if result.rowcount != 1:
            raise ValueError("Evento não encontrado.")


def request_password_recovery(username: str):
    from account_ownership import is_protected
    with db.connection() as conn:
        if is_protected(conn, username):
            return  # Same neutral public response; no school-mediated owner recovery.
        user = conn.execute("SELECT username FROM users WHERE username=? AND active=TRUE", (username,)).fetchone()
        if user:
            pending = conn.execute(
                """SELECT id FROM password_recovery_requests WHERE username=? AND
                   (status='requested' OR (status='issued' AND expires_at>=?)) LIMIT 1""",
                (username, datetime.now(timezone.utc).isoformat()),
            ).fetchone()
            if pending:
                return
            conn.execute(
                "INSERT INTO password_recovery_requests(username) VALUES(?)", (username,)
            )


def list_recovery_requests():
    with db.connection() as conn:
        return [dict(row) for row in conn.execute(
            """SELECT r.*,u.name FROM password_recovery_requests r
               JOIN users u ON u.username=r.username
               WHERE r.status IN ('requested','issued')
               AND NOT EXISTS (SELECT 1 FROM enrollment_settings s
                               WHERE s.key='system_owner_username' AND s.value=r.username)
               ORDER BY r.id DESC"""
        )]


def issue_recovery_code(request_id: int, admin: str):
    from account_ownership import is_protected
    code = secrets.token_urlsafe(9)
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    expires = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    with db.connection() as conn:
        target = conn.execute('SELECT username FROM password_recovery_requests WHERE id=?', (request_id,)).fetchone()
        if target and is_protected(conn, target['username']):
            raise ValueError('A recuperação do proprietário não pode ser realizada pela secretaria.')
        result = conn.execute(
            """UPDATE password_recovery_requests SET token_hash=?,status='issued',expires_at=?,issued_by=?
               WHERE id=? AND status='requested'""",
            (digest, expires, admin, request_id),
        )
        if result.rowcount != 1:
            raise ValueError("Solicitação indisponível ou já atendida.")
    return code


def use_recovery_code(username: str, code: str, new_password: str):
    from account_ownership import is_protected
    if len(new_password) < 10 or len(new_password) > 128:
        raise ValueError("Use uma senha entre 10 e 128 caracteres.")
    digest = hashlib.sha256(code.strip().encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    with db.connection() as conn:
        if is_protected(conn, username.strip().lower()):
            raise ValueError('Código inválido ou expirado.')
        row = conn.execute(
            """SELECT id FROM password_recovery_requests
               WHERE username=? AND token_hash=? AND status='issued' AND expires_at>=?
               ORDER BY id DESC LIMIT 1""",
            (username.strip().lower(), digest, now),
        ).fetchone()
        if not row:
            raise ValueError("Código inválido ou expirado.")
        identity = conn.execute('SELECT verified_at FROM account_identities WHERE username=?',
                                (username.strip().lower(),)).fetchone()
        if identity and identity['verified_at'] and len(new_password) < 15:
            raise ValueError('Use uma senha entre 15 e 128 caracteres para sua conta ativada.')
        consumed = conn.execute(
            "UPDATE password_recovery_requests SET status='used',used_at=CURRENT_TIMESTAMP WHERE id=? AND status='issued'",
            (row["id"],),
        )
        if consumed.rowcount != 1:
            raise ValueError("Código inválido ou já utilizado.")
        conn.execute(
            "UPDATE users SET password_hash=? WHERE username=?",
            (generate_password_hash(new_password), username.strip().lower()),
        )
        conn.execute(
            """INSERT INTO auth_versions(username,version) VALUES(?,1)
               ON CONFLICT(username) DO UPDATE SET version=auth_versions.version+1""",
            (username.strip().lower(),),
        )


def validate_upload(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    filename = secure_filename(file_storage.filename)
    content = file_storage.read(MAX_ATTACHMENT_BYTES + 1)
    mime = (file_storage.mimetype or mimetypes.guess_type(filename)[0] or "application/octet-stream").lower()
    if not filename or not content:
        raise ValueError("O arquivo selecionado está vazio ou possui nome inválido.")
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise ValueError("Cada anexo pode ter no máximo 5 MB.")
    if mime not in ATTACHMENT_MIMES:
        raise ValueError("Envie PDF, PNG, JPG, TXT ou ZIP.")
    extensions = {'.pdf':'application/pdf','.png':'image/png','.jpg':'image/jpeg',
                  '.jpeg':'image/jpeg','.txt':'text/plain','.zip':'application/zip'}
    from pathlib import Path
    expected = extensions.get(Path(filename).suffix.lower())
    normalized = 'application/zip' if mime == 'application/x-zip-compressed' else mime
    if expected != normalized:
        raise ValueError("A extensão e o tipo do arquivo não correspondem.")
    signatures = {'application/pdf':(b'%PDF-',),'image/png':(b'\x89PNG\r\n\x1a\n',),
                  'image/jpeg':(b'\xff\xd8\xff',),'application/zip':(b'PK\x03\x04',b'PK\x05\x06')}
    if normalized in signatures and not content.startswith(signatures[normalized]):
        raise ValueError("O conteúdo não corresponde ao formato informado.")
    if normalized == 'text/plain':
        try:
            content.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise ValueError("Envie o arquivo de texto na codificação UTF-8.") from exc
        if b'\x00' in content:
            raise ValueError("Arquivo de texto inválido.")
    return filename, mime, content


def save_attachment(owner: str, entity_type: str, entity_id: int, file_storage=None, validated=None):
    validated = validated or validate_upload(file_storage)
    if not validated:
        return None
    filename, mime, content = validated
    with db.connection() as conn:
        row = conn.execute(
            """INSERT INTO file_attachments
               (owner,entity_type,entity_id,filename,mime_type,size_bytes,content)
               VALUES(?,?,?,?,?,?,?) RETURNING id""",
            (owner, entity_type, entity_id, filename, mime, len(content), content),
        ).fetchone()
        return row["id"]


def list_attachments(entity_type: str, entity_ids: list[int]):
    if not entity_ids:
        return []
    placeholders = ",".join("?" for _ in entity_ids)
    with db.connection() as conn:
        return [dict(row) for row in conn.execute(
            f"""SELECT id,owner,entity_type,entity_id,filename,mime_type,size_bytes,created_at
                FROM file_attachments WHERE entity_type=? AND entity_id IN ({placeholders})
                ORDER BY id""",
            (entity_type, *entity_ids),
        )]


def get_attachment(attachment_id: int):
    with db.connection() as conn:
        row = conn.execute("SELECT * FROM file_attachments WHERE id=?", (attachment_id,)).fetchone()
        return dict(row) if row else None


def p1_metrics():
    with db.connection() as conn:
        def count(table, where=""):
            return conn.execute(f"SELECT COUNT(*) total FROM {table} {where}").fetchone()["total"]
        return {
            "diaries_pending": count("class_diary_entries", "WHERE status='submitted'"),
            "documents_pending": count("document_requests", "WHERE status IN ('requested','processing')"),
            "interventions_open": count("pedagogical_interventions", "WHERE status!='closed'"),
            "calendar_upcoming": count("calendar_events", "WHERE status='published' AND ends_at>=CURRENT_TIMESTAMP"),
            "recovery_pending": count("password_recovery_requests", "WHERE status='requested'"),
        }
