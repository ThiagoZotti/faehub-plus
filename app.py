# -*- coding: utf-8 -*-
"""FaeHub+ — campus digital de gestão escolar da ETESC/FAETEC."""

import os
import secrets
import hashlib
import database as db
from io import BytesIO
from dashboard import student_summary
from academic import attendance_calendar
from database import canonical_student_id, student_attendance
from database import mark_message_read
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from flask import (Flask, g, jsonify, render_template, request, redirect, url_for,
                   session, flash, send_file, has_request_context)
from database import (authenticate, archive_internship, create_exercise, create_user, get_exercises,
                      get_messages, get_submissions, init_db, list_users,
                      load_attendance, load_grades, log_action, recent_logs,
                      save_attendance, save_grade, send_message, submit_exercise,
                      toggle_user, get_internships,
                      save_internship)
from internships import MODALITIES, present_internship, validate_internship
import p1_operations as operations
import profile_photos
import account_enrollment as enrollment
from school_roster import KNOWN_IDS, ROSTER, ROSTER_NAMES

app = Flask(__name__)
app.secret_key = os.getenv("FAEHUB_SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=bool(os.getenv('RENDER')))
app.config['SEND_FILE_MAX_AGE_DEFAULT']=31536000
app.config['MAX_CONTENT_LENGTH']=6 * 1024 * 1024
try:
    CAMPUS_TIMEZONE = ZoneInfo("America/Sao_Paulo")
except ZoneInfoNotFoundError:
    CAMPUS_TIMEZONE = timezone(timedelta(hours=-3))
from pathlib import Path
from database import close_request_connection
app.teardown_appcontext(close_request_connection)
_static_versions = {
    p.relative_to(app.static_folder).as_posix(): str(p.stat().st_mtime_ns)
    for p in Path(app.static_folder).rglob("*")
    if p.is_file()
}

@app.url_defaults
def version_static(endpoint, values):
    if endpoint=='static' and 'v' not in values:
        values['v']=_static_versions.get(values.get('filename'),'1')


@app.after_request
def protect_response(response):
    """Security and cache defaults suitable for the local campus application."""
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; font-src 'self'; base-uri 'self'; "
        "form-action 'self'; frame-ancestors 'none'",
    )
    if request.endpoint not in {"static", "foto_perfil"}:
        response.headers["Cache-Control"] = "no-store"
    elif request.endpoint == "static" and request.args.get("v"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif request.endpoint == "foto_perfil" and response.status_code not in {200, 304}:
        response.headers["Cache-Control"] = "no-store"
    return response


@app.template_filter("local_datetime")
def local_datetime(value, output_format="%d/%m/%Y · %Hh%M"):
    """Render SQLite UTC timestamps in the campus timezone."""
    if value is None or value == "":
        return "—"
    try:
        if isinstance(value, datetime):
            moment = value
        else:
            raw = str(value).strip()
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            moment = datetime.fromisoformat(raw)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(CAMPUS_TIMEZONE).strftime(output_format)
    except (TypeError, ValueError, OverflowError):
        return str(value)

init_db()
import academic_core
from database import get_teacher_assignments, seed_teacher_assignments
from teacher_dashboard import teacher_overview
from teacher_workflow import scoped_roster, validated_grades, validated_attendance
from database import save_attendance_batch
from teacher_studio import studio, student_notices
from director import manage as manage_director, init_director, account_access, access_version
init_director()

def director_section(section):
    snapshot=academic_core.structure_snapshot()
    subjects=[subject['code'] for subject in snapshot['subjects'] if subject['active']]
    return manage_director(section,live_roster(),subjects)
seed_teacher_assignments()
academic_core.sync_teacher_assignments()
academic_core.sync_all_legacy_grades()


def live_roster():
    """Normalized roster is canonical; the module constant is seed compatibility only."""
    rows = academic_core.roster()
    return rows or ROSTER

# ==========================================================================
# Ícones (SVG inline, reutilizados nos templates via |safe)
# ==========================================================================
ICONS = {
    "home": '<svg viewBox="0 0 24 24" fill="none"><path d="m4 11 8-7 8 7v9a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1v-9Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>',
    "book": '<svg viewBox="0 0 24 24" fill="none"><path d="M5 4h9a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3V4Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M17 17H8a2 2 0 0 0 0 4h9" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>',
    "check": '<svg viewBox="0 0 24 24" fill="none"><rect x="4" y="4" width="16" height="16" rx="4" stroke="currentColor" stroke-width="1.7"/><path d="m8.5 12.5 2.3 2.3 4.7-5" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "clock": '<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="8.5" stroke="currentColor" stroke-width="1.7"/><path d="M12 7.5V12l3 2" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    "bell": '<svg viewBox="0 0 24 24" fill="none"><path d="M12 3a5 5 0 0 0-5 5v3.2c0 .6-.2 1.1-.6 1.6L5 15h14l-1.4-2.2c-.4-.5-.6-1-.6-1.6V8a5 5 0 0 0-5-5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M9.5 18a2.5 2.5 0 0 0 5 0" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
    "layers": '<svg viewBox="0 0 24 24" fill="none"><path d="m12 3 8.5 4.5L12 12 3.5 7.5 12 3Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="m3.5 12 8.5 4.5 8.5-4.5M3.5 16.5 12 21l8.5-4.5" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>',
    "users": '<svg viewBox="0 0 24 24" fill="none"><circle cx="9" cy="8" r="3.2" stroke="currentColor" stroke-width="1.7"/><path d="M3.5 19c0-3 2.5-5 5.5-5s5.5 2 5.5 5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><path d="M16 8.5a3 3 0 1 1 0 5.9M18.5 19c0-2.4-1.6-4.2-3.7-4.8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    "chart": '<svg viewBox="0 0 24 24" fill="none"><path d="M4 20V10M11 20V4M18 20v-7" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg>',
    "settings": '<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.7"/><path d="M12 3.5v2M12 18.5v2M4.9 6.4l1.4 1.4M17.7 16.2l1.4 1.4M3.5 12h2M18.5 12h2M4.9 17.6l1.4-1.4M17.7 7.8l1.4-1.4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    "briefcase": '<svg viewBox="0 0 24 24" fill="none"><path d="M8 7V5.5A2.5 2.5 0 0 1 10.5 3h3A2.5 2.5 0 0 1 16 5.5V7M4 7h16a1.5 1.5 0 0 1 1.5 1.5v9A2.5 2.5 0 0 1 19 20H5a2.5 2.5 0 0 1-2.5-2.5v-9A1.5 1.5 0 0 1 4 7Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M2.8 12.5c2.7 1.3 5.8 2 9.2 2s6.5-.7 9.2-2M10 13.8v1.7h4v-1.7" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>',
    "calendar": '<svg viewBox="0 0 24 24" fill="none"><rect x="3" y="5" width="18" height="16" rx="3" stroke="currentColor" stroke-width="1.7"/><path d="M8 3v4M16 3v4M3 10h18M8 14h2M14 14h2M8 18h2" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    "document": '<svg viewBox="0 0 24 24" fill="none"><path d="M6 3h8l4 4v14H6V3Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M14 3v5h5M9 12h6M9 16h6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    "journal": '<svg viewBox="0 0 24 24" fill="none"><path d="M5 4h13a2 2 0 0 1 2 2v14H7a3 3 0 0 1-3-3V5a1 1 0 0 1 1-1Z" stroke="currentColor" stroke-width="1.7"/><path d="M8 4v16M11 9h6M11 13h6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
}

ROLE_LABEL = {"aluno": "Aluno", "professor": "Professor", "admin": "Diretor", "responsavel": "Responsável"}

NAV = {
    "aluno": [
        ("painel", "Painel", "home"),
        ("boletim", "Boletim", "book"),
        ("agenda", "Agenda", "calendar"),
        ("horario", "Horário", "clock"),
        ("exercicios", "Exercícios", "layers"),
        ("comunicados", "Comunicados", "bell"),
        ("secretaria", "Secretaria", "document"),
        ("estagios", "Estágios", "briefcase"),
        ("mensagens", "Mensagens", "users"),
    ],
    "professor": [
        ("painel", "Painel", "home"),
        ("turmas", "Minhas turmas", "layers"),
        ("notas", "Lançar notas", "book"),
        ("chamada", "Chamada", "check"),
        ("diario", "Diário", "journal"),
        ("exercicios", "Exercícios", "layers"),
        ("mensagens", "Mensagens", "users"),
        ("avisos", "Avisos", "bell"),
        ("estagios", "Estágios", "briefcase"),
        ("calendario", "Calendário", "calendar"),
        ("notificacoes", "Notificações", "bell"),
    ],
    "admin": [
        ("painel", "Painel", "home"),
        ("usuarios", "Usuários", "users"),
        ("estrutura", "Estrutura", "layers"),
        ("secretaria", "Secretaria", "document"),
        ("coordenacao", "Coordenação", "journal"),
        ("relatorios", "Relatórios", "chart"),
        ("mensagens", "Mensagens", "bell"),
        ("periodos", "Períodos", "clock"),
        ("calendario", "Calendário", "calendar"),
        ("notificacoes", "Notificações", "bell"),
        ("configuracoes", "Configurações", "settings"),
    ],
    "responsavel": [
        ("painel", "Visão geral", "home"),
        ("secretaria", "Secretaria", "document"),
        ("calendario", "Calendário", "calendar"),
        ("notificacoes", "Notificações", "bell"),
        ("mensagens", "Mensagens", "users"),
    ],
}

VIEW_TITLES = {
    "aluno": {"painel": "Painel", "boletim": "Boletim", "agenda": "Agenda", "comunicados": "Comunicados", "historico": "Histórico", "frequencia": "Frequência", "horario": "Horário", "avisos": "Avisos", "exercicios": "Exercícios", "estagios": "Estágios", "calendario": "Calendário", "secretaria": "Secretaria", "notificacoes": "Notificações", "mensagens": "Mensagens"},
    "professor": {"painel": "Painel", "turmas": "Minhas turmas", "notas": "Lançar notas", "chamada": "Chamada", "diario": "Diário", "avisos": "Avisos", "exercicios": "Exercícios", "estagios": "Estágios", "calendario": "Calendário", "notificacoes": "Notificações", "mensagens": "Mensagens"},
    "admin": {"painel": "Painel", "usuarios": "Usuários", "estrutura": "Estrutura acadêmica", "turmas": "Turmas", "historico": "Histórico", "diario": "Diário", "secretaria": "Secretaria", "coordenacao": "Coordenação", "periodos": "Períodos", "calendario": "Calendário", "notificacoes": "Notificações", "relatorios": "Relatórios", "configuracoes": "Configurações", "mensagens": "Mensagens"},
    "responsavel": {"painel": "Portal do responsável", "historico": "Histórico", "secretaria": "Documentos", "calendario": "Calendário", "notificacoes": "Notificações", "mensagens": "Mensagens"},
}

# Horário e avisos são os mesmos para toda a turma 3110
from school_schedule import SCHEDULE_3110
AVISOS_3110 = [
    {"titulo": "Entrega do Projeto Integrador", "desc": "Prazo final para envio do repositório e apresentação em sala.", "quando": "28/08 · 23h59"},
    {"titulo": "Recuperação — Física", "desc": "Revise os conteúdos trabalhados e confirme a sala com a professora.", "quando": "02/09 · 08h00"},
    {"titulo": "Semana de provas bimestrais", "desc": "Consulte o quadro de horários atualizado no mural da secretaria.", "quando": "08 a 12/09"},
]

AULAS_DADAS_3110 = 76


def _situacao(media):
    return "Recuperação" if media < 6 else "Aprovado"


def _grades(pares):
    """pares: lista de (disciplina, n1, n2) -> calcula média e situação."""
    out = []
    for disciplina, n1, n2 in pares:
        media = round((n1 + n2) / 2, 2)
        out.append({"disciplina": disciplina, "n1": n1, "n2": n2, "media": media, "situacao": _situacao(media)})
    return out


# Perfil completo de cada aluno da turma 3110, indexado pela matrícula
ALUNOS_DB = {
    "23081": {
        "nome": "Thiago Zotti", "matricula": "23081", "turma": "3110",
        "grades": _grades([
            ("Matemática", 8.5, 7.8), ("BD", 6.4, 7.0),
            ("PDM", 9.0, 8.6), ("Física", 5.5, 6.0),
            ("Biologia", 7.2, 7.6),
        ]),
        "frequencia": 96, "faltas": 3, "aulas_dadas": AULAS_DADAS_3110,
    },
    "23092": {
        "nome": "Jonathan Samuel", "matricula": "23092", "turma": "3110",
        "grades": _grades([
            ("Matemática", 6.0, 6.4), ("BD", 5.5, 5.0),
            ("PDM", 6.8, 7.0), ("Física", 5.0, 5.8),
            ("Biologia", 6.5, 6.0),
        ]),
        "frequencia": 78, "faltas": 17, "aulas_dadas": AULAS_DADAS_3110,
    },
    "23104": {
        "nome": "Pablo Sousa", "matricula": "23104", "turma": "3110",
        "grades": _grades([
            ("Matemática", 9.0, 9.2), ("BD", 8.8, 9.0),
            ("PDM", 9.5, 9.3), ("Física", 8.6, 9.0),
            ("Biologia", 9.0, 9.4),
        ]),
        "frequencia": 99, "faltas": 1, "aulas_dadas": AULAS_DADAS_3110,
    },
    "23117": {
        "nome": "Marlon Eduardo", "matricula": "23117", "turma": "3110",
        "grades": _grades([
            ("Matemática", 7.2, 7.6), ("BD", 6.8, 7.0),
            ("PDM", 7.8, 8.0), ("Física", 6.5, 7.0),
            ("Biologia", 7.6, 7.8),
        ]),
        "frequencia": 88, "faltas": 9, "aulas_dadas": AULAS_DADAS_3110,
    },
}

PROFILE_FALLBACKS = {"professor": "Professor", "admin": "Direção", "responsavel": "Responsável"}


def initials(nome):
    partes = [p for p in nome.split(" ") if p]
    return "".join(p[0] for p in partes[:2]).upper()


def current_aluno():
    """Retorna o perfil completo do aluno logado nesta sessão."""
    cached = getattr(g, "student_profile", None) if has_request_context() else None
    if cached is not None:
        return cached
    sid=canonical_student_id(session['aluno_id'])
    name=session.get('display_name','Aluno')
    if sid in ALUNOS_DB:
        result=dict(ALUNOS_DB[sid])
        result['grades']=[dict(grade) for grade in ALUNOS_DB[sid]['grades']]
    else:
        roster=live_roster()
        student=next((s for s in roster if s['id']==sid),None)
        if not student:
            student=next((s for s in roster if s['nome'].casefold()==name.casefold()),None)
        grades=[]
        for grade in load_grades():
            if grade['student_id']==sid:
                media=round((grade['n1']+grade['n2'])/2,2)
                grades.append(dict(disciplina=grade['discipline'],n1=grade['n1'],n2=grade['n2'],
                                   media=media,situacao=_situacao(media)))
        result=dict(nome=name,matricula=sid,turma=student['turma'] if student else '',grades=grades,
                    frequencia=0,faltas=0,aulas_dadas=0)

    records=current_student_attendance(sid)
    if records:
        absent=sum(record['status']=='ausente' for record in records)
        result.update(frequencia=round((len(records)-absent)*100/len(records)),
                      faltas=absent,aulas_dadas=len(records))
    if has_request_context():
        g.student_profile = result
    return result


def current_student_attendance(student_id):
    """Load a student's attendance once during the current request."""
    student_id = canonical_student_id(student_id)
    cache = getattr(g, "student_attendance", {}) if has_request_context() else {}
    if student_id not in cache:
        cache[student_id] = student_attendance(student_id)
        if has_request_context():
            g.student_attendance = cache
    return cache[student_id]


def apply_persisted_grades():
    if has_request_context() and getattr(g, "persisted_grades_applied", False):
        return
    for saved in load_grades():
        aluno = ALUNOS_DB.get(saved["student_id"])
        if not aluno:
            continue
        if not any(g['disciplina']==saved['discipline'] for g in aluno['grades']):
            aluno['grades'].append(dict(disciplina=saved['discipline'],n1=saved['n1'],n2=saved['n2'],media=0,situacao=''))
        for grade in aluno["grades"]:
            if grade["disciplina"] == saved["discipline"]:
                grade.update(n1=saved["n1"], n2=saved["n2"])
                grade["media"] = round((saved["n1"] + saved["n2"]) / 2, 2)
                grade["situacao"] = _situacao(grade["media"])
    if has_request_context():
        g.persisted_grades_applied = True


apply_persisted_grades()


# ==========================================================================
# Contexto compartilhado por todas as páginas internas
# ==========================================================================
@app.context_processor
def inject_shell():
    if getattr(g, "rendering_error", False):
        # The standalone error template needs no account/notification queries.
        # Reusing a failed database connection here hides the original error.
        return {}
    role = session.get("role")
    if not role:
        return {}
    nome = current_aluno()["nome"] if role == "aluno" else session.get("display_name", PROFILE_FALLBACKS[role])
    shell_notifications = request_notifications(session["username"], role)
    notification_unread = sum(
        not item["is_read"] and not (role == "aluno" and item.get("category") == "mensagem")
        for item in shell_notifications
    )
    nav_items = NAV.get(role, [])
    primary_limit = 6 if role == "aluno" else (7 if role in {"professor", "admin"} else len(nav_items))
    nav_primary, nav_more = nav_items[:primary_limit], nav_items[primary_limit:]
    current_view = getattr(g, "current_view", "")
    # Small metadata is cached in the signed session; navigating never downloads
    # photograph bytes or adds a database round-trip for every module.
    checked_at = datetime.now(timezone.utc).timestamp()
    if "profile_photo_revision" not in session or checked_at - session.get("profile_photo_checked", 0) > 300:
        session["profile_photo_revision"] = profile_photos.photo_revision(session["username"])
        session["profile_photo_checked"] = checked_at
    session.setdefault("profile_token", secrets.token_hex(24))
    return {
        "icons": ICONS,
        "role": role,
        "role_label": ROLE_LABEL.get(role),
        "nav_items": nav_items,
        "nav_primary": nav_primary,
        "nav_more": nav_more,
        "nav_more_current": any(item[0] == current_view for item in nav_more),
        "profile_nome": nome,
        "profile_iniciais": initials(nome),
        "profile_turma": current_aluno()["turma"] if role == "aluno" else "",
        "profile_photo_url": url_for("foto_perfil", v=session["profile_photo_revision"]) if session["profile_photo_revision"] else "",
        "profile_token": session["profile_token"],
        "current_view": current_view,
        "view_title": getattr(g, "view_title", ""),
        "notification_unread": notification_unread,
    }


def request_notifications(username, role):
    """Reuse notification data when a page and its shell need the same rows."""
    key = (username, role)
    cache = getattr(g, "notification_cache", {})
    if key not in cache:
        cache[key] = operations.list_notifications(username, role)
        g.notification_cache = cache
    return cache[key]


def login_required(view_name_map):
    """Garante sessão ativa e que o perfil logado tem acesso a esta rota."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            role = session.get("role")
            if not role:
                return redirect(url_for("login"))
            access = account_access(session.get("username"))
            expected_role = "diretor" if role == "admin" else role
            if (not access or not access["active"] or access["role"] != expected_role
                    or session.get("auth_version", 0) != access["auth_version"]):
                session.clear()
                return redirect(url_for("login"))
            g.current_view = view_name_map
            g.view_title = VIEW_TITLES[role].get(view_name_map, "")
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ==========================================================================
# Autenticação
# ==========================================================================
@app.route("/")
def login():
    # Visiting the entrance never skips the user's explicit action.
    import secrets
    session.setdefault('login_token', secrets.token_hex(24))
    return render_template("login.html", token=session['login_token'], username='', error=None,
                           demos_enabled=enrollment.demos_enabled())


@app.route("/entrar", methods=["POST"])
def entrar():
    import secrets
    wants_json = request.headers.get('X-Campus-Login') == '1'
    if not session.get('login_token') or not secrets.compare_digest(session['login_token'], request.form.get('token', '')):
        if wants_json:
            return {'error': 'Sessão expirada. Atualize a página e tente novamente.'}, 400
        flash("Sessão expirada. Tente novamente.")
        return redirect(url_for('login'))
    usuario = request.form.get("usuario", "").strip().lower()
    senha = request.form.get("senha", "")
    permitted = enrollment.consume_rate_limit('login', enrollment.login_identifier(usuario[:254]), limit=20)
    conta = authenticate(usuario, senha) if permitted and len(usuario) <= 254 and len(senha) <= 128 else None

    if not conta:
        if wants_json:
            return {'error': 'Usuário ou senha inválidos.'}, 401
        return render_template('login.html', token=session['login_token'], username=usuario,
                               error='Usuário ou senha inválidos.', demos_enabled=enrollment.demos_enabled()), 401

    session.clear()
    session["role"] = "admin" if conta["role"] == "diretor" else conta["role"]
    usuario = conta['username']  # E-mail is an alias; academic records use the immutable school ID.
    session["username"] = usuario
    session["display_name"] = conta["name"]
    session["auth_version"] = access_version(usuario)
    if conta["role"] == "aluno":
        session["aluno_id"] = conta["student_id"]
    log_action(usuario, "login", f"Acesso como {conta['role']}")
    if wants_json:
        return {'name': conta['name'], 'role': conta['role'], 'destination': url_for('painel')}
    return redirect(url_for("painel"))


@app.route('/ativar', methods=['GET', 'POST'])
def ativar_conta():
    session.setdefault('enrollment_token', secrets.token_hex(24))
    error = None
    if request.method == 'POST':
        if not secrets.compare_digest(session['enrollment_token'], request.form.get('token', '')):
            return render_template('account_activation.html', invitation=None, token=session['enrollment_token'],
                                   error='Sessão expirada. Reabra o convite recebido no e-mail.', field_error=None), 400, {'Referrer-Policy':'no-referrer'}
        try:
            action = request.form.get('action')
            if action == 'open':
                if not enrollment.consume_rate_limit('invitation', request.remote_addr or '', limit=80):
                    raise ValueError('Muitas tentativas. Aguarde alguns minutos antes de tentar novamente.')
                raw = request.form.get('invitation', '')
                digest = hashlib.sha256(raw.encode()).hexdigest()
                if not 40 <= len(raw) <= 100 or not enrollment.invitation_by_digest(digest):
                    raise ValueError('Convite inválido, expirado ou cancelado. Peça um novo convite à escola.')
                session['invitation_digest'] = digest
                return redirect(url_for('ativar_conta'))
            elif action == 'complete':
                if not enrollment.consume_rate_limit('activation', request.remote_addr or '', limit=80):
                    raise ValueError('Muitas tentativas. Aguarde alguns minutos antes de tentar novamente.')
                enrollment.complete_invitation(session.get('invitation_digest', ''),
                                                request.form.get('password', ''), request.form.get('confirmation', ''))
                session.clear()
                flash('Conta ativada e e-mail confirmado. Entre com seu e-mail e sua nova senha.')
                return redirect(url_for('login'))
            else:
                raise ValueError('Ação inválida.')
        except ValueError as exc:
            error = str(exc)
    invitation = enrollment.invitation_by_digest(session.get('invitation_digest', '')) if session.get('invitation_digest') else None
    field_error = None
    if error and request.form.get('action') == 'complete' and invitation:
        if not 15 <= len(request.form.get('password','')) <= 128:
            field_error = 'password'
        elif request.form.get('password') != request.form.get('confirmation'):
            field_error = 'confirmation'
    response = app.make_response((render_template('account_activation.html', invitation=invitation,
                  token=session['enrollment_token'], error=error, field_error=field_error), 422 if error else 200))
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@app.route("/sair")
def sair():
    session.clear()
    return redirect(url_for("login"))


@app.get("/perfil/foto")
@login_required("painel")
def foto_perfil():
    photo = profile_photos.get_photo(session["username"])
    if not photo:
        return "", 404, {"Cache-Control": "no-store"}
    response = send_file(BytesIO(photo["content"]), mimetype="image/jpeg", max_age=300,
                         etag=photo["revision"], download_name="foto-de-perfil.jpg")
    response.headers["Cache-Control"] = "private, max-age=300"
    response.vary.add("Cookie")
    return response


@app.post("/perfil/foto")
@login_required("painel")
def alterar_foto_perfil():
    if not session.get("profile_token") or not secrets.compare_digest(
            session["profile_token"], request.form.get("token", "")):
        return {"error": "Sessão expirada. Atualize a página e tente novamente."}, 400
    action = request.form.get("action", "upload")
    if action not in {"upload", "remove"}:
        return {"error": "Ação inválida."}, 400
    try:
        if action == "remove":
            profile_photos.remove_photo(session["username"])
            revision = ""
        else:
            content = profile_photos.normalize_photo(request.files.get("photo"))
            revision = profile_photos.save_photo(session["username"], content)
    except ValueError as exc:
        return {"error": str(exc)}, 422
    session["profile_photo_revision"] = revision
    session["profile_photo_checked"] = datetime.now(timezone.utc).timestamp()
    return {"url": url_for("foto_perfil", v=revision) if revision else "", "revision": revision,
            "message": "Foto de perfil atualizada." if revision else "Foto de perfil removida."}


# ==========================================================================
# Painel (visão geral) — conteúdo varia por perfil
# ==========================================================================
@app.route("/painel")
@login_required("painel")
def painel():
    role = session["role"]
    if role == "aluno":
        apply_persisted_grades()
        aluno = current_aluno()
        d = dict(aluno, avisos=student_notices(aluno['turma'],AVISOS_3110))
        media_geral = round(sum(g["media"] for g in d["grades"]) / len(d["grades"]), 1) if d['grades'] else 0
        recuperacoes = sum(1 for g in d["grades"] if g["situacao"] == "Recuperação")
        return render_template("aluno_painel.html", d=d, media_geral=media_geral, recuperacoes=recuperacoes,
                               summary=student_summary(d, get_exercises(), get_submissions(session['username']),
                                   [message for message in get_messages(session['username'])
                                    if message['recipient'] == session['username']], SCHEDULE_3110))
    if role == "professor":
        overview = teacher_overview(session['username'], get_teacher_assignments(session['username']),
                                    SCHEDULE_3110, live_roster(), get_exercises(), get_submissions(),
                                    load_grades(), get_messages(session['username']))
        return render_template("professor_painel.html", overview=overview)
    if role == "responsavel":
        apply_persisted_grades()
        links = operations.guardian_students(session["username"])
        students = []
        for link in links:
            profile = dict(ALUNOS_DB.get(link["student_id"], {}))
            if profile:
                records = student_attendance(link["student_id"])
                if records:
                    absent = sum(row["status"] == "ausente" for row in records)
                    profile.update(
                        frequencia=round((len(records) - absent) * 100 / len(records)),
                        faltas=absent,
                        aulas_dadas=len(records),
                    )
                profile["relationship"] = link["relationship"]
                profile["average"] = round(
                    sum(grade["media"] for grade in profile["grades"]) / len(profile["grades"]), 1
                ) if profile.get("grades") else 0
                students.append(profile)
        interventions = []
        for student in students:
            interventions.extend(operations.list_interventions(student["matricula"]))
        return render_template(
            "p1/responsavel.html", students=students,
            documents=operations.list_document_requests(student_ids=[s["matricula"] for s in students]),
            interventions=interventions,
        )
    return director_section("painel")


# ==========================================================================
# Rotas — Aluno
# ==========================================================================
@app.route("/boletim")
@login_required("boletim")
def boletim():
    if session.get("role") != "aluno":
        return redirect(url_for("painel"))
    apply_persisted_grades()
    return render_template("aluno_boletim.html", d=current_aluno())


@app.route("/frequencia")
@login_required("frequencia")
def frequencia():
    if session.get("role") != "aluno":
        return redirect(url_for("painel"))
    d = current_aluno()
    presencas = d["aulas_dadas"] - d["faltas"]
    calendar_data = attendance_calendar(current_student_attendance(session['aluno_id']), request.args.get('month'))
    return render_template("aluno_frequencia.html", d=d, presencas=presencas, cal=calendar_data)


@app.get("/agenda")
@login_required("agenda")
def agenda():
    """Student calendar: attendance records and institutional events in one place."""
    if session.get("role") != "aluno":
        return redirect(url_for("calendario"))
    d = current_aluno()
    records = current_student_attendance(session["aluno_id"])
    calendar_data = attendance_calendar(records, request.args.get("month"))
    events = operations.list_calendar_events("aluno", d["turma"])
    return render_template(
        "aluno_agenda.html", d=d, cal=calendar_data,
        presencas=d["aulas_dadas"] - d["faltas"], events=events,
        event_types=operations.EVENT_TYPES,
    )


@app.route("/horario")
@login_required("horario")
def horario():
    if session.get("role") != "aluno":
        return redirect(url_for("painel"))
    d = dict(current_aluno(), schedule=SCHEDULE_3110)
    from dashboard import upcoming_lessons
    return render_template("aluno_horario.html", d=d, upcoming=upcoming_lessons(SCHEDULE_3110))


# ==========================================================================
# Rotas compartilhadas (conteúdo muda por perfil)
# ==========================================================================
@app.route("/avisos", methods=["GET", "POST"])
@login_required("avisos")
def avisos():
    role = session.get("role")
    if role == "aluno":
        return render_template("aluno_avisos.html", avisos=student_notices(current_aluno()['turma'],AVISOS_3110), username=session['username'])
    if role == "professor":
        return studio('avisos')
    return redirect(url_for("painel"))


@app.route("/comunicados", methods=["GET", "POST"])
@login_required("comunicados")
def comunicados():
    """One student inbox for class notices and account notifications."""
    if session.get("role") != "aluno":
        return redirect(url_for("notificacoes"))
    error = None
    username = session["username"]
    notices = student_notices(current_aluno()["turma"], AVISOS_3110)
    notifications = [
        item for item in request_notifications(username, "aluno")
        if item.get("category") != "mensagem"
    ]
    if request.method == "POST":
        if not p1_token_valid():
            return "Sessão expirada. Atualize a página.", 400
        try:
            action = request.form.get("action", "read")
            kind = request.form.get("kind", "notification")
            item_key = request.form.get("item_key", "").strip()
            if kind == "notice":
                if item_key not in {item["key"] for item in notices}:
                    raise ValueError("Aviso indisponível para esta conta.")
                if action in {"read", "unread"}:
                    db.set_communication_read(username, kind, item_key, action == "read")
                elif action == "dismiss":
                    db.dismiss_communication(username, kind, item_key)
                elif action == "restore":
                    db.restore_communication(username, kind, item_key)
                else:
                    raise ValueError("Ação de comunicado inválida.")
            elif kind == "notification":
                notification_id = request.form.get("id", type=int)
                notification = next((item for item in notifications if item["id"] == notification_id), None)
                if not notification or item_key != str(notification_id):
                    raise ValueError("Atualização indisponível para esta conta.")
                if action in {"read", "unread"}:
                    operations.mark_notification(notification_id, username, action == "read", "aluno")
                    db.set_communication_read(username, kind, item_key, action == "read")
                elif action == "dismiss":
                    if not notification["is_read"]:
                        raise ValueError("Leia a atualização antes de descartá-la.")
                    db.set_communication_read(username, kind, item_key, True)
                    db.dismiss_communication(username, kind, item_key)
                elif action == "restore":
                    db.restore_communication(username, kind, item_key)
                else:
                    raise ValueError("Ação de comunicado inválida.")
            else:
                raise ValueError("Tipo de comunicado inválido.")
            return redirect(url_for("comunicados"))
        except ValueError as exc:
            error = str(exc)
    notice_states = db.get_communication_states(username, "notice")
    notification_states = db.get_communication_states(username, "notification")
    for item in notices:
        state = notice_states.get(item["key"], {})
        item.update(is_read=bool(state.get("is_read")), dismissed=bool(state.get("dismissed_at")))
    for item in notifications:
        state = notification_states.get(str(item["id"]), {})
        item["dismissed"] = bool(state.get("dismissed_at"))
    visible_notices = [item for item in notices if not item["dismissed"]]
    visible_notifications = [item for item in notifications if not item["dismissed"]]
    dismissed = [dict(item, kind="notice", item_key=item["key"]) for item in notices if item["dismissed"]]
    dismissed.extend(dict(item, kind="notification", item_key=str(item["id"]))
                     for item in notifications if item["dismissed"])
    return render_template(
        "aluno_comunicados.html", avisos=visible_notices, notifications=visible_notifications,
        dismissed=dismissed,
        unread=sum(not item["is_read"] for item in visible_notices + visible_notifications),
        token=p1_token(), error=error, username=username,
    ), 422 if error else 200


def teacher_scope():
    import secrets
    from dashboard import CAMPUS_TZ, datetime
    assignments=get_teacher_assignments(session['username'])
    classes=sorted({a['class_name'] for a in assignments})
    source=request.form if request.method=='POST' else request.args
    selected=source.get('turma',classes[0] if classes else '')
    students=scoped_roster(assignments,live_roster(),selected) if selected else []
    session.setdefault('teacher_token',secrets.token_hex(24))
    return dict(assignments=assignments,classes=classes,selected=selected,roster=students,
                disciplines=[a['discipline'] for a in assignments if a['class_name']==selected],
                token=session['teacher_token'],today=datetime.now(CAMPUS_TZ).date().isoformat())

def teacher_token_valid():
    import secrets
    return bool(session.get('teacher_token')) and secrets.compare_digest(session['teacher_token'],request.form.get('token',''))

@app.route("/turmas", methods=["GET","POST"])
@login_required("turmas")
def turmas():
    if session.get('role')=='admin':
        # Keep the established direction workflow compatible while the new
        # normalized academic map remains available at /estrutura.
        return director_section('turmas')
    if session.get('role')!='professor':return redirect(url_for('painel'))
    try: ctx=teacher_scope()
    except ValueError as error:return str(error),403
    ctx['class_counts']={name:sum(s['turma']==name for s in live_roster()) for name in ctx['classes']}
    return render_template('professor_turmas.html',**ctx)


@app.route("/estrutura", methods=["GET", "POST"])
@login_required("estrutura")
def estrutura():
    if session.get("role") != "admin":
        return "Acesso restrito à Direção.", 403
    session.setdefault("p0_token", secrets.token_hex(24))
    error = None
    if request.method == "POST":
        if not secrets.compare_digest(session["p0_token"], request.form.get("token", "")):
            return "Sessão expirada. Atualize a página.", 400
        try:
            academic_core.mutate(request.form.get("action", ""), request.form, session["username"])
            academic_core.sync_teacher_assignments()
            flash("Estrutura acadêmica atualizada. O histórico foi preservado.")
            return redirect(url_for("estrutura", view=request.form.get("return_view", "overview")))
        except ValueError as exc:
            error = str(exc)
        except Exception as exc:
            if not db.is_integrity_error(exc):
                raise
            error = "Já existe um cadastro com esses dados ou o vínculo informado é inválido."
    snapshot = academic_core.structure_snapshot()
    query = request.args.get("q", "").strip()[:80]
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1
    filtered = snapshot["enrollments"]
    if query:
        needle = query.casefold()
        filtered = [row for row in filtered if needle in (row["full_name"] + " " + row["registration"] + " " + row["class_code"] + " " + row["academic_year"]).casefold()]
    page_size = 10
    pages = max(1, (len(filtered) + page_size - 1) // page_size)
    page = min(page, pages)
    snapshot["enrollment_rows"] = filtered[(page - 1) * page_size:page * page_size]
    return render_template(
        "p0/estrutura.html", data=snapshot, token=session["p0_token"],
        error=error, active_view=request.args.get("view", "overview"),
        retry={key: value for key, value in request.form.items() if key != "token"} if error else None,
        today=date.today().isoformat(), query=query, page=page, pages=pages, filtered_total=len(filtered),
    ), 422 if error else 200


@app.get("/historico")
@login_required("historico")
def historico():
    role = session.get("role")
    available = []
    if role == "aluno":
        available = [row for row in live_roster() if row["id"] == session.get("aluno_id")]
    elif role == "responsavel":
        linked = {row["student_id"] for row in operations.guardian_students(session["username"])}
        snapshot = academic_core.structure_snapshot()
        available = [{"id": row["registration"], "nome": row["full_name"]} for row in snapshot["students"] if row["registration"] in linked]
    elif role == "admin":
        snapshot = academic_core.structure_snapshot()
        available = [{"id": row["registration"], "nome": row["full_name"]} for row in snapshot["students"]]
    else:
        return "Acesso restrito.", 403
    requested = request.args.get("matricula", "")
    registration = requested or (available[0]["id"] if available else "")
    if registration and registration not in {row["id"] for row in available}:
        return "Você não possui acesso a esta matrícula.", 403
    student = next((row for row in available if row["id"] == registration), None)
    return render_template("p0/historico.html", student=student, students=available,
                           history=academic_core.student_history(registration) if registration else [])

@app.route("/notas",methods=["GET","POST"])
@login_required("notas")
def notas():
    if session.get('role')!='professor':return redirect(url_for('painel'))
    try:ctx=teacher_scope()
    except ValueError as error:return str(error),403
    source=request.form if request.method=='POST' else request.args
    discipline=source.get('disciplina',ctx['disciplines'][0] if ctx['disciplines'] else '')
    if discipline and discipline not in ctx['disciplines']:return 'Disciplina não vinculada.',403
    error=None
    if request.method=='POST':
        if not teacher_token_valid():return 'Sessão expirada. Atualize a página.',400
        try:
            if operations.period_is_closed():
                raise ValueError('O período letivo está fechado. A coordenação precisa reabri-lo antes de alterar notas.')
            n1,n2=validated_grades(ctx['assignments'],live_roster(),ctx['selected'],discipline,
                                   request.form.get('aluno_id'),request.form.get('n1',''),request.form.get('n2',''))
            save_grade(request.form['aluno_id'],discipline,n1,n2)
            apply_persisted_grades()
            log_action(session['username'],'nota_atualizada',f"{request.form['aluno_id']} · {discipline}")
            flash('Notas salvas. O boletim do aluno foi atualizado.')
            return redirect(url_for('notas',turma=ctx['selected'],disciplina=discipline))
        except ValueError as exc:error=str(exc)
    ids={s['id'] for s in ctx['roster']}
    saved={g['student_id']:g for g in load_grades() if g['student_id'] in ids and g['discipline']==discipline}
    return render_template('professor_notas.html',**ctx,discipline=discipline,saved=saved,error=error),422 if error else 200

@app.route("/chamada",methods=["GET","POST"])
@login_required("chamada")
def chamada():
    if session.get('role')!='professor':return redirect(url_for('painel'))
    try:ctx=teacher_scope()
    except ValueError as error:return str(error),403
    source=request.form if request.method=='POST' else request.args
    selected_date=source.get('data',ctx['today'])
    try: date.fromisoformat(selected_date)
    except ValueError:return 'Data inválida.',400
    persisted=load_attendance(selected_date)
    marks={s['id']:persisted.get(s['id']) for s in ctx['roster']}
    error=None
    if request.method=='POST':
        if not teacher_token_valid():return 'Sessão expirada. Atualize a página.',400
        marks={s['id']:request.form.get('presenca_'+s['id']) for s in ctx['roster']}
        try:
            if operations.period_is_closed(selected_date):
                raise ValueError('O período desta chamada está fechado. Solicite reabertura à coordenação.')
            valid=validated_attendance(ctx['roster'],selected_date,marks,date.fromisoformat(ctx['today']))
            save_attendance_batch(selected_date,valid)
            log_action(session['username'],'chamada_registrada',f"{ctx['selected']} · {selected_date}")
            flash('Chamada salva para '+selected_date+'.')
            return redirect(url_for('chamada',turma=ctx['selected'],data=selected_date))
        except ValueError as exc:error=str(exc)
    return render_template('professor_chamada.html',**ctx,selected_date=selected_date,attendance=marks,
                           registered=sum(s['id'] in persisted for s in ctx['roster']),error=error),422 if error else 200


# ==========================================================================
# P1 — Operação escolar completa
# ==========================================================================
def p1_token():
    session.setdefault("p1_token", secrets.token_hex(24))
    return session["p1_token"]


@app.template_filter('ops_status')
def ops_status(value):
    return {'draft':'Rascunho','submitted':'Em validação','validated':'Validado','returned':'Ajustes solicitados',
            'requested':'Solicitado','processing':'Em atendimento','ready':'Pronto','delivered':'Entregue',
            'rejected':'Indeferido','open':'Aberto','closed':'Fechado','planning':'Planejamento',
            'monitoring':'Em acompanhamento','close':'Fechamento','reopen':'Reabertura',
            'active':'Ativo','archived':'Arquivado','completed':'Concluído','transferred':'Transferido',
            'withdrawn':'Desistência','cancelled':'Cancelado','inactive':'Inativo'}.get(value,value)


def p1_token_valid():
    supplied = request.form.get("token", "")
    return bool(session.get("p1_token")) and secrets.compare_digest(session["p1_token"], supplied)


def p1_text(name, limit, required=True):
    value = request.form.get(name, "").strip()
    if (required and not value) or len(value) > limit:
        raise ValueError("Revise os campos obrigatórios e os limites informados.")
    return value


def attachment_map(entity_type, entity_ids):
    grouped = {}
    for item in operations.list_attachments(entity_type, list(entity_ids)):
        grouped.setdefault(item["entity_id"], []).append(item)
    return grouped


def eligible_message_users(username, role):
    """Return server-authorized message contacts for one account."""
    users = [user for user in list_users() if user["username"] != username and user["active"]]
    if role != "responsavel":
        return users
    linked_ids = {row["student_id"] for row in operations.guardian_students(username)}
    staff_roles = {"professor", "diretor", "admin", "coordenacao", "secretaria"}
    return [
        user for user in users
        if user.get("student_id") in linked_ids or user.get("role") in staff_roles
    ]


@app.route("/diario", methods=["GET", "POST"])
@login_required("diario")
def diario():
    role = session.get("role")
    if role not in {"professor", "admin"}:
        return "Acesso restrito ao corpo docente e à coordenação.", 403
    assignments = get_teacher_assignments(session["username"]) if role == "professor" else []
    error = None
    if request.method == "POST":
        if not p1_token_valid():
            return "Sessão expirada. Atualize a página.", 400
        try:
            action = request.form.get("action", "create")
            entry_id = request.form.get("id", type=int)
            if role == "admin":
                operations.review_diary_entry(
                    entry_id, session["username"], action, p1_text("coordinator_note", 3000, action == "return")
                )
                log_action(session["username"], "diario_" + action, str(entry_id))
                flash("Revisão do diário registrada com histórico.")
                return redirect(url_for("diario"))
            class_name = p1_text("class_name", 40)
            discipline = p1_text("discipline", 120)
            if not any(a["class_name"] == class_name and a["discipline"] == discipline for a in assignments):
                raise ValueError("Turma e disciplina não estão vinculadas à sua conta.")
            lesson_date = p1_text("lesson_date", 10)
            if date.fromisoformat(lesson_date) > date.today():
                raise ValueError("O registro de aula ministrada não pode ter data futura.")
            if operations.period_is_closed(lesson_date):
                raise ValueError("O período desta aula está fechado. Solicite reabertura à coordenação.")
            try:
                class_hours = int(request.form.get("class_hours", "2"))
            except ValueError as exc:
                raise ValueError("Informe uma quantidade válida de tempos de aula.") from exc
            if not 1 <= class_hours <= 12:
                raise ValueError("A quantidade deve ficar entre 1 e 12 tempos.")
            status = request.form.get("status", "draft")
            if status not in {"draft", "submitted"}:
                raise ValueError("Situação do diário inválida.")
            data = {
                "class_name": class_name, "discipline": discipline, "lesson_date": lesson_date,
                "content": p1_text("content", 10000), "objectives": p1_text("objectives", 5000),
                "methodology": p1_text("methodology", 3000, False),
                "resources": p1_text("resources", 2000, False),
                "homework": p1_text("homework", 3000, False),
                "observations": p1_text("observations", 5000, False),
                "class_hours": class_hours, "status": status,
            }
            saved_id = operations.save_diary_entry(session["username"], data, entry_id)
            if status == "submitted":
                operations.create_notification(
                    "Diário aguardando validação", f"{discipline} · turma {class_name} · {lesson_date}",
                    role_target="admin", category="diario", action_url=url_for("diario"),
                    created_by=session["username"],
                )
            log_action(session["username"], "diario_salvo", f"{saved_id} · {status}")
            flash("Diário salvo como rascunho." if status == "draft" else "Diário enviado para validação.")
            return redirect(url_for("diario"))
        except (ValueError, TypeError) as exc:
            error = str(exc) if isinstance(exc, ValueError) else "Dados do diário inválidos."
    entries = operations.list_diary_entries(session["username"] if role == "professor" else None)
    edit_id = request.args.get('edit', type=int)
    edit_entry = next((row for row in entries if row['id']==edit_id and row['status'] in ('draft','returned')), None)
    form_values = request.form.to_dict() if error else (edit_entry or {})
    return render_template(
        "p1/diario.html", entries=entries, assignments=assignments, token=p1_token(), error=error,
        today=date.today().isoformat(), form_values=form_values,
    ), 422 if error else 200


@app.route("/secretaria", methods=["GET", "POST"])
@login_required("secretaria")
def secretaria():
    role = session.get("role")
    if role not in {"aluno", "responsavel", "admin"}:
        return "Acesso restrito à comunidade acadêmica autorizada.", 403
    if role == "aluno":
        allowed_students = [session["aluno_id"]]
    elif role == "responsavel":
        allowed_students = [row["student_id"] for row in operations.guardian_students(session["username"])]
    else:
        allowed_students = [student["id"] for student in live_roster()]
    error = None
    issued_code = session.pop("issued_recovery_code", None)
    if request.method == "POST":
        if not p1_token_valid():
            return "Sessão expirada. Atualize a página.", 400
        try:
            action = request.form.get("action", "request")
            if role == "admin":
                if action == "document_status":
                    request_id = request.form.get("id", type=int)
                    status = request.form.get("status", "")
                    operations.update_document_request(request_id, status, p1_text("note", 1000, False))
                    record = next((row for row in operations.list_document_requests() if row["id"] == request_id), None)
                    if record:
                        operations.create_notification(
                            "Documento atualizado", f"O protocolo {record['protocol']} agora está: {status}.",
                            recipient=record["requester"], category="documento",
                            action_url=url_for("secretaria"), created_by=session["username"],
                        )
                elif action == "issue_recovery":
                    recovery_id = request.form.get("id", type=int)
                    session["issued_recovery_code"] = operations.issue_recovery_code(recovery_id, session["username"])
                    flash("Código emitido. Ele será mostrado uma única vez nesta sessão.")
                    return redirect(url_for("secretaria"))
                else:
                    raise ValueError("Ação de secretaria inválida.")
                log_action(session["username"], "secretaria_" + action, str(request.form.get("id", "")))
                flash("Solicitação atualizada.")
            else:
                student_id = request.form.get("student_id", "")
                if student_id not in allowed_students:
                    raise ValueError("Você não possui acesso a esta matrícula.")
                _, protocol = operations.create_document_request(
                    session["username"], student_id, request.form.get("document_type", ""),
                    p1_text("purpose", 500, False),
                )
                operations.create_notification(
                    "Nova solicitação documental", f"Protocolo {protocol} aguarda atendimento.",
                    role_target="admin", category="documento", action_url=url_for("secretaria"),
                    created_by=session["username"],
                )
                log_action(session["username"], "documento_solicitado", protocol)
                flash(f"Solicitação registrada. Protocolo: {protocol}.")
            return redirect(url_for("secretaria"))
        except ValueError as exc:
            error = str(exc)
    requests = operations.list_document_requests() if role == "admin" else operations.list_document_requests(student_ids=allowed_students)
    history_registration = ""
    academic_history = []
    if role != "admin" and allowed_students:
        requested_history = request.args.get("matricula", "")
        history_registration = requested_history if requested_history in allowed_students else allowed_students[0]
        academic_history = academic_core.student_history(history_registration)
    return render_template(
        "p1/secretaria.html", requests=requests, student_ids=allowed_students,
        students={student["id"]: student["nome"] for student in live_roster()},
        document_types=operations.DOCUMENT_TYPES, recoveries=operations.list_recovery_requests() if role == "admin" else [],
        issued_code=issued_code, token=p1_token(), error=error,
        history_registration=history_registration, academic_history=academic_history,
    ), 422 if error else 200


@app.get("/secretaria/documentos/<int:request_id>/imprimir")
@login_required("secretaria")
def imprimir_documento(request_id):
    record = next((row for row in operations.list_document_requests() if row["id"] == request_id), None)
    if not record or record["status"] not in {"ready", "delivered"}:
        return "Documento indisponível.", 404
    role = session.get("role")
    allowed = role == "admin" or (role == "aluno" and record["student_id"] == session.get("aluno_id"))
    if role == "responsavel":
        allowed = record["student_id"] in {row["student_id"] for row in operations.guardian_students(session["username"])}
    if not allowed:
        return "Você não possui acesso a este documento.", 403
    student = next((row for row in live_roster() if row["id"] == record["student_id"]), None)
    grades = [row for row in load_grades() if row['student_id'] == record['student_id']]
    attendance = student_attendance(record['student_id'])
    return render_template(
        "p1/documento_impressao.html", record=record, student=student,
        document_name=operations.DOCUMENT_TYPES.get(record["document_type"], "Documento escolar"),
        grades=grades, attendance=attendance,
        frequency=round(100*sum(row['status']=='presente' for row in attendance)/len(attendance),1) if attendance else None,
    )


@app.route("/coordenacao", methods=["GET", "POST"])
@login_required("coordenacao")
def coordenacao():
    if session.get("role") != "admin":
        return "Acesso restrito à coordenação.", 403
    error = None
    if request.method == "POST":
        if not p1_token_valid():
            return "Sessão expirada. Atualize a página.", 400
        try:
            action = request.form.get("action", "create")
            if action == "status":
                operations.set_intervention_status(request.form.get("id", type=int), request.form.get("status", ""))
            else:
                if request.form.get("student_id", "") not in {student['id'] for student in live_roster()}:
                    raise ValueError("Selecione uma matrícula cadastrada.")
                operations.save_intervention(
                    session["username"], request.form.get("student_id", ""), p1_text("category", 80),
                    p1_text("summary", 1000), p1_text("plan", 3000),
                )
            log_action(session["username"], "coordenacao_" + action, request.form.get("student_id", ""))
            flash("Acompanhamento pedagógico atualizado.")
            return redirect(url_for("coordenacao"))
        except ValueError as exc:
            error = str(exc)
    apply_persisted_grades()
    risk = []
    for student_id, profile in ALUNOS_DB.items():
        average = round(sum(row["media"] for row in profile["grades"]) / len(profile["grades"]), 1) if profile["grades"] else 0
        reasons = []
        if average < 6:
            reasons.append("média abaixo de 6")
        records = student_attendance(student_id)
        frequency = round(100 * sum(row['status']=='presente' for row in records) / len(records)) if records else None
        if frequency is not None and frequency < 75:
            reasons.append("frequência abaixo de 75%")
        if sum(row["media"] < 6 for row in profile["grades"]) >= 2:
            reasons.append("duas ou mais recuperações")
        if reasons:
            risk.append(dict(profile, average=average, reasons=reasons, frequencia=frequency))
    return render_template(
        "p1/coordenacao.html", risk=risk, interventions=operations.list_interventions(),
        diaries=[row for row in operations.list_diary_entries() if row["status"] == "submitted"],
        token=p1_token(), error=error, students=live_roster(),
    ), 422 if error else 200


@app.route("/periodos", methods=["GET", "POST"])
@login_required("periodos")
def periodos():
    if session.get("role") != "admin":
        return "Acesso restrito à direção.", 403
    error = None
    if request.method == "POST":
        if not p1_token_valid():
            return "Sessão expirada. Atualize a página.", 400
        try:
            action = request.form.get("action", "")
            operations.change_period_status(
                request.form.get("period_id", type=int), action, session["username"], p1_text("reason", 500)
            )
            log_action(session["username"], "periodo_" + action, request.form.get("period_id", ""))
            flash("Situação do período atualizada. O histórico foi preservado.")
            return redirect(url_for("periodos"))
        except ValueError as exc:
            error = str(exc)
    return render_template(
        "p1/periodos.html", periods=operations.list_periods(), history=operations.list_period_log(),
        token=p1_token(), error=error,
    ), 422 if error else 200


@app.route("/calendario", methods=["GET", "POST"])
@login_required("calendario")
def calendario():
    role = session.get("role")
    class_name = current_aluno()["turma"] if role == "aluno" else ""
    if role == "responsavel":
        linked = operations.guardian_students(session["username"])
        profile = ALUNOS_DB.get(linked[0]["student_id"], {}) if linked else {}
        class_name = profile.get("turma", "")
    error = None
    if request.method == "POST":
        if role != "admin":
            return "Somente a direção pode alterar o calendário.", 403
        if not p1_token_valid():
            return "Sessão expirada. Atualize a página.", 400
        try:
            action = request.form.get("action", "create")
            if action == "cancel":
                operations.cancel_calendar_event(request.form.get("id", type=int))
                flash("Evento cancelado; o registro foi preservado.")
            else:
                starts_at, ends_at = request.form.get("starts_at", ""), request.form.get("ends_at", "")
                start_dt, end_dt = datetime.fromisoformat(starts_at), datetime.fromisoformat(ends_at)
                if end_dt < start_dt:
                    raise ValueError("O término deve ser posterior ao início.")
                event_type = request.form.get("event_type", "")
                if event_type not in operations.EVENT_TYPES:
                    raise ValueError("Tipo de evento inválido.")
                audience = request.form.get("audience", "todos")
                if audience not in {"todos", "aluno", "professor", "admin", "responsavel", "turma"}:
                    raise ValueError("Público inválido.")
                event_id = operations.save_calendar_event(session["username"], {
                    "title": p1_text("title", 160), "description": p1_text("description", 5000, False),
                    "starts_at": start_dt.replace(tzinfo=CAMPUS_TIMEZONE).isoformat(),
                    "ends_at": end_dt.replace(tzinfo=CAMPUS_TIMEZONE).isoformat(), "event_type": event_type,
                    "audience": audience, "class_name": p1_text("class_name", 40, audience == "turma"),
                    "location": p1_text("location", 160, False),
                })
                # Do not disclose class-specific event titles to other classes.
                if audience != "turma":
                    operations.create_notification(
                        "Novo evento no calendário", request.form["title"].strip(), role_target=audience,
                        category="calendario", action_url=url_for("calendario"), created_by=session["username"],
                    )
                log_action(session["username"], "calendario_publicado", str(event_id))
                flash("Evento publicado no calendário escolar.")
            return redirect(url_for("calendario"))
        except (ValueError, TypeError) as exc:
            error = str(exc) if isinstance(exc, ValueError) else "Dados do evento inválidos."
    events = operations.list_calendar_events(role, class_name)
    return render_template(
        "p1/calendario.html", events=events, event_types=operations.EVENT_TYPES,
        token=p1_token(), error=error, today=date.today().isoformat(),
    ), 422 if error else 200


@app.route("/notificacoes", methods=["GET", "POST"])
@login_required("notificacoes")
def notificacoes():
    role = session.get("role")
    error = None
    if request.method == "POST":
        if not p1_token_valid():
            return "Sessão expirada. Atualize a página.", 400
        try:
            action = request.form.get("action", "read")
            if action in {"read", "unread"}:
                operations.mark_notification(request.form.get("id", type=int), session["username"], action == "read", role)
            elif action == "publish" and role == "admin":
                target = request.form.get("role_target", "todos")
                if target not in {"todos", "aluno", "professor", "admin", "responsavel"}:
                    raise ValueError("Público da notificação inválido.")
                operations.create_notification(
                    p1_text("title", 160), p1_text("body", 2000), role_target=target,
                    category=request.form.get("category", "institucional")[:40],
                    action_url=p1_text("action_url", 500, False), created_by=session["username"],
                )
                log_action(session["username"], "notificacao_publicada", target)
                flash("Notificação publicada.")
            else:
                raise ValueError("Ação de notificação inválida.")
            return redirect(url_for("notificacoes"))
        except ValueError as exc:
            error = str(exc)
    items = request_notifications(session["username"], role)
    return render_template(
        "p1/notificacoes.html", notifications=items, unread=sum(not row["is_read"] for row in items),
        token=p1_token(), error=error,
    ), 422 if error else 200


@app.route("/recuperar-senha", methods=["GET", "POST"])
def recuperar_senha():
    session.setdefault("recovery_token", secrets.token_hex(24))
    message = error = None
    if request.method == "POST":
        if not secrets.compare_digest(session["recovery_token"], request.form.get("token", "")):
            return "Sessão expirada. Atualize a página.", 400
        action = request.form.get("action", "request")
        try:
            if action == "request":
                operations.request_password_recovery(enrollment.login_identifier(request.form.get("username", "")[:254]))
                message = "Se a conta estiver ativa, a secretaria recebeu a solicitação. O código é entregue após confirmação de identidade."
            elif action == "reset":
                new_password = request.form.get("new_password", "")
                if new_password != request.form.get("confirm_password", ""):
                    raise ValueError("As novas senhas não coincidem.")
                operations.use_recovery_code(
                    enrollment.login_identifier(request.form.get("username", "")[:254]), request.form.get("code", ""), new_password
                )
                flash("Senha redefinida. Entre novamente com a nova senha.")
                return redirect(url_for("login"))
            else:
                raise ValueError("Ação inválida.")
        except ValueError as exc:
            error = str(exc)
    return render_template("p1/recuperar_senha.html", message=message, error=error, token=session["recovery_token"])


@app.get("/anexos/<int:attachment_id>")
@login_required("mensagens")
def baixar_anexo(attachment_id):
    attachment = operations.get_attachment(attachment_id)
    if not attachment:
        return "Anexo não encontrado.", 404
    allowed = session.get("role") == "admin" or (
        attachment["entity_type"] != "message" and attachment["owner"] == session["username"]
    )
    with operations.db.connection() as conn:
        if attachment["entity_type"] == "message":
            entity = conn.execute("SELECT sender,recipient,group_id,deleted_at FROM messages WHERE id=?", (attachment["entity_id"],)).fetchone()
            counterpart = ""
            if entity and session["username"] == entity["sender"]:
                counterpart = entity["recipient"]
            elif entity and session["username"] == entity["recipient"]:
                counterpart = entity["sender"]
            permitted = {user["username"] for user in eligible_message_users(session["username"], session.get("role"))}
            group_allowed = bool(
                entity and entity["group_id"] and conn.execute(
                    "SELECT 1 FROM message_group_members WHERE group_id=? AND username=?",
                    (entity["group_id"], session["username"]),
                ).fetchone()
            )
            allowed = allowed or bool(entity and not entity["deleted_at"] and (counterpart in permitted or group_allowed))
        elif attachment["entity_type"] == "exercise":
            entity = conn.execute("SELECT teacher,class_name FROM exercises WHERE id=?", (attachment["entity_id"],)).fetchone()
            allowed = allowed or bool(entity and session.get("role") == "aluno" and current_aluno()["turma"] == entity["class_name"])
        else:
            entity = conn.execute(
                """SELECT s.student,e.teacher FROM submissions s JOIN exercises e ON e.id=s.exercise_id WHERE s.id=?""",
                (attachment["entity_id"],),
            ).fetchone()
            allowed = allowed or bool(entity and session["username"] in {entity["student"], entity["teacher"]})
    if not allowed:
        return "Você não possui acesso a este anexo.", 403
    inline_image = request.args.get("inline") == "1" and attachment["mime_type"] in {"image/png", "image/jpeg"}
    return send_file(
        BytesIO(attachment["content"]), mimetype=attachment["mime_type"],
        as_attachment=not inline_image, download_name=attachment["filename"], max_age=0,
    )


# ==========================================================================
# Rotas — Direção / Admin
# ==========================================================================
@app.route("/usuarios", methods=["GET", "POST"])
@login_required("usuarios")
def usuarios():
    return director_section('usuarios')


@app.post("/usuarios/<username>/alternar")
def usuario_alternar(username):
    return 'Use a central de usuários para alterar o status com confirmação.',400


@app.route("/relatorios")
@login_required("relatorios")
def relatorios():
    return director_section('relatorios')


@app.route("/configuracoes",methods=["GET","POST"])
@login_required("configuracoes")
def configuracoes():
    return director_section('configuracoes')


@app.route("/mensagens", methods=["GET", "POST"])
@login_required("mensagens")
def mensagens():
    eligible = eligible_message_users(session["username"], session.get("role"))
    allowed_participants = {user["username"] for user in eligible}
    groups = db.list_message_groups(session["username"])
    allowed_group_ids = {group["id"] for group in groups}
    session.setdefault('message_token', secrets.token_hex(24))

    def destination(participant="", group_id=None, **extra):
        params = dict(extra)
        if group_id in allowed_group_ids:
            params["group"] = group_id
        elif participant in allowed_participants:
            params["with"] = participant
        return url_for("mensagens", **params)

    if request.method == "POST":
        if not secrets.compare_digest(session.get('message_token', ''), request.form.get('token', '')):
            flash("Sessão expirada. Abra as mensagens novamente.")
            return redirect(url_for("mensagens"))
        action = request.form.get('action', 'send')
        participant = request.form.get('participant', request.form.get('recipient', ''))
        group_id = request.form.get('group_id', type=int)
        message_id = request.form.get('message_id', type=int)
        visible = db.message_visible_to(message_id, session["username"]) if message_id else None

        if action == 'read' and visible and visible["recipient"] == session["username"]:
            mark_message_read(message_id, session["username"])
            return redirect(destination(visible["sender"]))
        if action == 'read_thread' and participant in allowed_participants:
            db.mark_thread_read(session['username'], participant)
            return redirect(destination(participant))
        if action == 'open_group' and group_id in allowed_group_ids:
            db.mark_group_read(session['username'], group_id)
            return redirect(destination(group_id=group_id))
        if action in {'delete_message', 'restore_message'}:
            changed = (db.soft_delete_message(message_id, session['username']) if action == 'delete_message'
                       else db.restore_message(message_id, session['username']))
            flash("Mensagem apagada." if changed and action == 'delete_message'
                  else "Mensagem restaurada." if changed else "Ação indisponível.")
            return redirect(destination(participant, group_id))
        if action == 'edit_message':
            body = request.form.get("body", "").strip()
            changed = bool(visible and visible["sender"] == session["username"] and body and len(body) <= 10000
                           and db.edit_message(message_id, session["username"], body))
            flash("Mensagem editada." if changed else "Não foi possível editar essa mensagem.")
            return redirect(destination(participant, group_id))
        if action == 'react_message':
            emoji = request.form.get("emoji", "")
            if visible and not visible.get("deleted_at") and emoji in {'👍','❤️','😂','😮','👏','✅'}:
                db.toggle_message_reaction(message_id, session["username"], emoji)
            return redirect(destination(participant, group_id))
        if action == 'create_group':
            if session.get("role") not in {"professor", "admin"}:
                return "Somente professores e direção podem criar grupos.", 403
            members = [name for name in request.form.getlist("members") if name in allowed_participants]
            try:
                created = db.create_message_group(request.form.get("group_name", ""),
                                                  request.form.get("class_name", "")[:40],
                                                  session["username"], members)
                flash("Grupo criado.")
                return redirect(url_for("mensagens", group=created))
            except ValueError as exc:
                flash(str(exc))
                return redirect(url_for("mensagens"))

        recipient = request.form.get("recipient", "")
        subject = request.form.get("subject", "").strip() or "Mensagem direta"
        body = request.form.get("body", "").strip()
        reply_to_id = request.form.get("reply_to_id", type=int)
        try:
            validated = operations.validate_upload(request.files.get("attachment"))
        except ValueError as exc:
            flash(str(exc))
            return redirect(destination(recipient, group_id))
        reply = db.message_visible_to(reply_to_id, session["username"]) if reply_to_id else None
        reply_ok = not reply or ((group_id and reply.get("group_id") == group_id) or
                                 (not group_id and not reply.get("group_id") and
                                  {reply["sender"], reply["recipient"]} == {session["username"], recipient}))
        target_ok = group_id in allowed_group_ids or recipient in allowed_participants
        if target_ok and reply_ok and (body or validated) and len(subject) <= 160 and len(body) <= 10000:
            if reply_to_id or group_id:
                message_id = send_message(session["username"], session["username"] if group_id else recipient,
                                          subject, body, reply_to_id=reply_to_id, group_id=group_id)
            else:
                message_id = send_message(session["username"], recipient, subject, body)
            operations.save_attachment(session["username"], "message", message_id, validated=validated)
            recipients = ([member["username"] for member in db.message_group_members(group_id)
                           if member["username"] != session["username"]] if group_id else [recipient])
            for target in recipients:
                operations.create_notification("Nova mensagem", body[:120] or "Imagem ou arquivo",
                                               recipient=target, category="mensagem",
                                               action_url=destination(recipient, group_id),
                                               created_by=session["username"])
            log_action(session["username"], "mensagem_enviada", f"grupo:{group_id}" if group_id else recipient)
        else:
            flash("Escolha uma conversa e escreva uma mensagem ou adicione um arquivo.")
        return redirect(destination(recipient, group_id))

    if session.get('role') in ('aluno','professor','admin','responsavel'):
        db.mark_messages_delivered(session["username"])
        selected_group = request.args.get("group", type=int)
        selected = request.args.get("with", "")
        if selected_group in allowed_group_ids:
            db.mark_group_read(session["username"], selected_group)
        elif selected in allowed_participants:
            db.mark_thread_read(session["username"], selected)

        messages_list = get_messages(session['username'])
        threads = {}
        for message in reversed(messages_list):
            received = message["recipient"] == session["username"]
            other = message["sender"] if received else message["recipient"]
            if other not in allowed_participants:
                continue
            thread = threads.setdefault(other, {
                "username": other, "name": message["sender_name"] if received else message["recipient_name"],
                "messages": [], "unread": 0, "is_group": False,
            })
            thread["messages"].append(message)
            thread["last"] = message
            if received and not message["is_read"]:
                thread["unread"] += 1
        thread_list = list(threads.values())
        for group in groups:
            last = db.get_group_messages(group["id"], session["username"], limit=1)
            thread_list.append({
                "username": f"group-{group['id']}", "name": group["name"], "messages": [],
                "unread": group["unread"], "is_group": True, "group_id": group["id"],
                "member_count": group["member_count"],
                "last": last[-1] if last else {"id": 0, "body": "Grupo da turma", "created_at": group["created_at"], "deleted_at": None, "sender": ""},
            })
        thread_list.sort(key=lambda item: item["last"]["id"], reverse=True)

        active_thread = None
        before_id = request.args.get("before", type=int)
        if selected_group in allowed_group_ids:
            group = next(item for item in groups if item["id"] == selected_group)
            page = db.get_group_messages(selected_group, session["username"], limit=31, before_id=before_id)
            active_thread = {"username": f"group-{group['id']}", "name": group["name"],
                             "messages": page[-30:], "unread": 0, "is_group": True,
                             "group_id": group["id"], "member_count": group["member_count"],
                             "has_older": len(page) > 30}
        else:
            if selected not in threads:
                selected = next((item["username"] for item in thread_list if not item["is_group"]), "")
            active_thread = threads.get(selected)
            if active_thread:
                page = [item for item in active_thread["messages"] if not before_id or item["id"] < before_id]
                active_thread["has_older"] = len(page) > 30
                active_thread["messages"] = page[-30:]
        active_ids = {item["id"] for item in active_thread["messages"]} if active_thread else set()
        return render_template("aluno_mensagens.html", messages=messages_list,
                               users=eligible, token=session['message_token'],
                               threads=thread_list, active_thread=active_thread,
                               attachments=attachment_map("message", active_ids), groups=groups,
                               group_members=db.message_group_members(active_thread["group_id"])
                               if active_thread and active_thread.get("is_group") else [],
                               can_create_group=session.get("role") in {"professor", "admin"})
    return render_template("mensagens.html", messages=get_messages(session["username"]),
                           users=[u for u in list_users() if u["username"] != session["username"] and u["active"]])


@app.get("/api/mensagens/estado")
@login_required("mensagens")
def message_state():
    """Small authenticated snapshot polled without holding a web worker open."""
    username = session["username"]
    return jsonify(db.message_sync_state(username))


@app.route("/estagios", methods=["GET", "POST"])
@login_required("estagios")
def estagios():
    role = session.get("role")
    if role not in {"professor", "aluno"}:
        return redirect(url_for("painel"))

    today = datetime.now(CAMPUS_TIMEZONE).date()
    error = None
    failed_form = None
    classes = []
    token = ""

    if role == "professor":
        try:
            scope = teacher_scope()
        except ValueError as exc:
            return str(exc), 403
        classes = scope["classes"]
        token = scope["token"]
        if request.method == "POST":
            if not teacher_token_valid():
                return "Sessão expirada. Atualize a página.", 400
            action = request.form.get("action", "create")
            internship_id = request.form.get("id", type=int)
            try:
                if action in {"archive", "restore"}:
                    if not internship_id:
                        raise ValueError("Oportunidade inválida.")
                    archive_internship(
                        internship_id, session["username"], action == "archive"
                    )
                    verb = "arquivada" if action == "archive" else "restaurada"
                    log_action(session["username"], f"estagio_{verb}", str(internship_id))
                    flash(f"Oportunidade {verb}. O histórico foi preservado.")
                    return redirect(url_for("estagios"))

                if action not in {"create", "edit"}:
                    raise ValueError("Ação de estágio inválida.")
                if action == "edit" and not internship_id:
                    raise ValueError("Oportunidade inválida.")
                data = validate_internship(request.form, classes, today)
                save_internship(
                    session["username"], data,
                    internship_id=internship_id if action == "edit" else None,
                )
                event = "atualizada" if action == "edit" else "publicada"
                log_action(session["username"], f"estagio_{event}", data["title"])
                flash(f"Oportunidade {event} para a turma {data['class_name']}.")
                return redirect(url_for("estagios"))
            except ValueError as exc:
                error = str(exc)
                failed_form = request.form.to_dict()
    elif request.method == "POST":
        return "Somente professores podem publicar oportunidades.", 403

    if role == "professor":
        raw_items = get_internships(teacher=session["username"], include_archived=True)
    else:
        raw_items = get_internships(
            class_name=current_aluno()["turma"], active_on=today.isoformat()
        )
    items = [present_internship(item, today) for item in raw_items]
    open_items = [item for item in items if not item["archived"] and item["days_left"] >= 0]
    next_deadline = min((item["days_left"] for item in open_items), default=None)
    return render_template(
        "p1/estagios.html",
        items=items,
        open_count=len(open_items),
        archived_count=sum(bool(item["archived"]) for item in items),
        next_deadline=next_deadline,
        modalities=MODALITIES,
        classes=classes,
        token=token,
        today=today.isoformat(),
        error=error,
        failed_form=failed_form,
    ), 422 if error else 200


@app.route("/exercicios", methods=["GET", "POST"])
@login_required("exercicios")
def exercicios():
    if session.get('role')=='professor':
        return studio('exercicios')
    if session.get("role") != "aluno":
        return redirect(url_for("painel"))
    if request.method == "POST":
        if session["role"] == "professor":
            create_exercise(session["username"], request.form["title"], request.form["description"],
                            request.form.get("discipline", "Matemática"), "3110", request.form["due_date"])
            log_action(session["username"], "exercicio_criado", request.form["title"])
            flash("Exercício publicado para a turma 3110.")
        else:
            import secrets
            token = session.get('exercise_token', '')
            if not token or not secrets.compare_digest(token, request.form.get('token', '')):
                flash("Sua sessão de entrega expirou. Abra o exercício novamente.")
                return redirect(url_for("exercicios"))
            exercise_id = request.form.get("exercise_id", type=int)
            answer = request.form.get("answer", "").strip()
            try:
                validated = operations.validate_upload(request.files.get("attachment"))
            except ValueError as exc:
                flash(str(exc))
                return redirect(url_for("exercicios"))
            allowed = {e['id'] for e in get_exercises() if e['class_name'] == current_aluno()['turma']}
            if exercise_id not in allowed or (not answer and not validated) or len(answer) > 20000:
                flash("Entrega inválida. Escreva uma resposta ou envie um anexo permitido.")
                return redirect(url_for("exercicios"))
            submission_id = submit_exercise(exercise_id, session["username"], answer)
            operations.save_attachment(session["username"], "submission", submission_id, validated=validated)
            log_action(session["username"], "exercicio_entregue", request.form["exercise_id"])
            flash("Resposta entregue com sucesso.")
        return redirect(url_for("exercicios"))
    submissions = get_submissions(session["username"] if session["role"] == "aluno" else None)
    if session["role"] == "aluno":
        import secrets
        from dashboard import CAMPUS_TZ, datetime
        session.setdefault('exercise_token', secrets.token_hex(24))
        exercises = [e for e in get_exercises() if e['class_name'] == current_aluno()['turma']]
        exercise_filter = request.args.get("status", "all")
        if exercise_filter not in {"all", "pending", "done"}:
            exercise_filter = "all"
        return render_template("aluno_exercicios.html", exercises=exercises,
                               submitted={s['exercise_id']: s for s in submissions},
                               today=datetime.now(CAMPUS_TZ).date().isoformat(),
                               exercise_filter=exercise_filter,
                               token=session['exercise_token'],
                               exercise_attachments=attachment_map("exercise", {e["id"] for e in exercises}),
                               submission_attachments=attachment_map("submission", {s["id"] for s in submissions}))
    return render_template("exercicios.html", exercises=get_exercises(), submissions=submissions)


@app.errorhandler(404)
def not_found(_error):
    return render_template(
        "error.html", status=404, title="Caminho não encontrado",
        message="Este espaço não existe no campus ou mudou de endereço.",
    ), 404


@app.errorhandler(500)
def internal_error(_error):
    g.rendering_error = True
    return render_template(
        "error.html", status=500, title="Algo saiu do lugar",
        message="Não foi possível concluir esta ação. Seus dados anteriores continuam preservados.",
    ), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
