# -*- coding: utf-8 -*-
"""FaeHub+ — campus digital de gestão escolar da ETESC/FAETEC."""

import os
import secrets
from dashboard import student_summary
from academic import attendance_calendar
from database import canonical_student_id, student_attendance
from database import mark_message_read
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from flask import Flask, g, render_template, request, redirect, url_for, session, flash
from database import (authenticate, create_exercise, create_user, get_exercises,
                      get_messages, get_submissions, init_db, list_users,
                      load_attendance, load_grades, log_action, recent_logs,
                      save_attendance, save_grade, send_message, submit_exercise,
                      toggle_user, get_avatar, save_avatar)
from school_roster import KNOWN_IDS, ROSTER, ROSTER_NAMES

app = Flask(__name__)
app.secret_key = os.getenv("FAEHUB_SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
app.config['SEND_FILE_MAX_AGE_DEFAULT']=3600
try:
    CAMPUS_TIMEZONE = ZoneInfo("America/Sao_Paulo")
except ZoneInfoNotFoundError:
    CAMPUS_TIMEZONE = timezone(timedelta(hours=-3))
from pathlib import Path
from database import close_request_connection
app.teardown_appcontext(close_request_connection)
_static_versions={p.name:str(p.stat().st_mtime_ns) for p in Path(app.static_folder).iterdir() if p.is_file()}

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
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; font-src 'self'; base-uri 'self'; "
        "form-action 'self'; frame-ancestors 'none'",
    )
    if request.endpoint != "static":
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
from database import get_teacher_assignments, seed_teacher_assignments
from teacher_dashboard import teacher_overview
from teacher_workflow import scoped_roster, validated_grades, validated_attendance
from database import save_attendance_batch
from teacher_studio import studio, student_notices
from director import manage as manage_director, init_director, valid_account, access_version
init_director()

def director_section(section):
    subjects=sorted({s for row in SCHEDULE_3110["grade"] for s in row if s and "vago" not in s.lower()})
    return manage_director(section,ROSTER,subjects)
seed_teacher_assignments()

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
    "avatar": '<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="3.4" stroke="currentColor" stroke-width="1.7"/><path d="M4.2 20c.6-4 3.3-6 7.8-6s7.2 2 7.8 6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><path d="M18.4 4.1v3.4M16.7 5.8h3.4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
}

ROLE_LABEL = {"aluno": "Aluno", "professor": "Professor", "admin": "Diretor"}

NAV = {
    "aluno": [
        ("painel", "Painel", "home"),
        ("boletim", "Boletim", "book"),
        ("frequencia", "Frequência", "check"),
        ("horario", "Horário", "clock"),
        ("avisos", "Avisos", "bell"),
        ("exercicios", "Exercícios", "layers"),
        ("mensagens", "Mensagens", "users"),
        ("avatar", "Meu avatar", "avatar"),
    ],
    "professor": [
        ("painel", "Painel", "home"),
        ("turmas", "Minhas turmas", "layers"),
        ("notas", "Lançar notas", "book"),
        ("chamada", "Chamada", "check"),
        ("avisos", "Avisos", "bell"),
        ("exercicios", "Exercícios", "layers"),
        ("mensagens", "Mensagens", "users"),
    ],
    "admin": [
        ("painel", "Painel", "home"),
        ("usuarios", "Usuários", "users"),
        ("turmas", "Turmas", "layers"),
        ("relatorios", "Relatórios", "chart"),
        ("configuracoes", "Configurações", "settings"),
        ("mensagens", "Mensagens", "bell"),
    ],
}

VIEW_TITLES = {
    "aluno": {"painel": "Painel", "boletim": "Boletim", "frequencia": "Frequência", "horario": "Horário", "avisos": "Avisos", "exercicios": "Exercícios", "mensagens": "Mensagens", "avatar": "Meu avatar"},
    "professor": {"painel": "Painel", "turmas": "Minhas turmas", "notas": "Lançar notas", "chamada": "Chamada", "avisos": "Avisos", "exercicios": "Exercícios", "mensagens": "Mensagens"},
    "admin": {"painel": "Painel", "usuarios": "Usuários", "turmas": "Turmas", "relatorios": "Relatórios", "configuracoes": "Configurações", "mensagens": "Mensagens"},
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

PROFILE_FALLBACKS = {"professor": "Professor", "admin": "Direção"}


def initials(nome):
    partes = [p for p in nome.split(" ") if p]
    return "".join(p[0] for p in partes[:2]).upper()


def current_aluno():
    """Retorna o perfil completo do aluno logado nesta sessão."""
    sid=canonical_student_id(session['aluno_id'])
    student=next((s for s in ROSTER if s['id']==sid),None)
    name=session.get('display_name','Aluno')
    if sid in ALUNOS_DB:
        result=dict(ALUNOS_DB[sid])
        result['grades']=[dict(grade) for grade in ALUNOS_DB[sid]['grades']]
    else:
        if not student:
            student=next((s for s in ROSTER if s['nome'].casefold()==name.casefold()),None)
        grades=[]
        for grade in load_grades():
            if grade['student_id']==sid:
                media=round((grade['n1']+grade['n2'])/2,2)
                grades.append(dict(disciplina=grade['discipline'],n1=grade['n1'],n2=grade['n2'],
                                   media=media,situacao=_situacao(media)))
        result=dict(nome=name,matricula=sid,turma=student['turma'] if student else '',grades=grades,
                    frequencia=0,faltas=0,aulas_dadas=0)

    records=student_attendance(sid)
    if records:
        absent=sum(record['status']=='ausente' for record in records)
        result.update(frequencia=round((len(records)-absent)*100/len(records)),
                      faltas=absent,aulas_dadas=len(records))
    return result


def apply_persisted_grades():
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


apply_persisted_grades()


# ==========================================================================
# Contexto compartilhado por todas as páginas internas
# ==========================================================================
@app.context_processor
def inject_shell():
    role = session.get("role")
    if not role:
        return {}
    nome = current_aluno()["nome"] if role == "aluno" else session.get("display_name", PROFILE_FALLBACKS[role])
    avatar = get_avatar(session["username"]) if role == "aluno" else None
    return {
        "icons": ICONS,
        "role": role,
        "role_label": ROLE_LABEL.get(role),
        "nav_items": NAV.get(role, []),
        "profile_nome": nome,
        "profile_iniciais": initials(nome),
        "profile_avatar": avatar,
        "current_view": getattr(g, "current_view", ""),
        "view_title": getattr(g, "view_title", ""),
    }


def login_required(view_name_map):
    """Garante sessão ativa e que o perfil logado tem acesso a esta rota."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            role = session.get("role")
            if not role:
                return redirect(url_for("login"))
            if not valid_account(session.get("username"),role) or session.get("auth_version",0)!=access_version(session.get("username")):
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
    return render_template("login.html", token=session['login_token'], username='', error=None)


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
    conta = authenticate(usuario, senha)

    if not conta:
        if wants_json:
            return {'error': 'Usuário ou senha inválidos.'}, 401
        return render_template('login.html', token=session['login_token'], username=usuario,
                               error='Usuário ou senha inválidos.'), 401

    session.clear()
    session["role"] = "admin" if conta["role"] == "diretor" else conta["role"]
    session["username"] = usuario
    session["display_name"] = conta["name"]
    session["auth_version"] = access_version(usuario)
    if conta["role"] == "aluno":
        session["aluno_id"] = conta["student_id"]
    log_action(usuario, "login", f"Acesso como {conta['role']}")
    if wants_json:
        return {'name': conta['name'], 'role': conta['role'], 'destination': url_for('painel')}
    return redirect(url_for("painel"))


@app.route("/sair")
def sair():
    session.clear()
    return redirect(url_for("login"))


# ==========================================================================
# Painel (visão geral) — conteúdo varia por perfil
# ==========================================================================
@app.route("/painel")
@login_required("painel")
def painel():
    role = session["role"]
    if role == "aluno":
        apply_persisted_grades()
        d = dict(current_aluno(), avisos=student_notices(current_aluno()['turma'],AVISOS_3110))
        media_geral = round(sum(g["media"] for g in d["grades"]) / len(d["grades"]), 1) if d['grades'] else 0
        recuperacoes = sum(1 for g in d["grades"] if g["situacao"] == "Recuperação")
        return render_template("aluno_painel.html", d=d, media_geral=media_geral, recuperacoes=recuperacoes,
                               avatar=get_avatar(session["username"]),
                               summary=student_summary(d, get_exercises(), get_submissions(session['username']),
                                   [message for message in get_messages(session['username'])
                                    if message['recipient'] == session['username']], SCHEDULE_3110))
    if role == "professor":
        overview = teacher_overview(session['username'], get_teacher_assignments(session['username']),
                                    SCHEDULE_3110, ROSTER, get_exercises(), get_submissions(),
                                    load_grades(), get_messages(session['username']))
        return render_template("professor_painel.html", overview=overview)
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
    calendar_data = attendance_calendar(student_attendance(session['aluno_id']), request.args.get('month'))
    return render_template("aluno_frequencia.html", d=d, presencas=presencas, cal=calendar_data)


@app.route("/horario")
@login_required("horario")
def horario():
    if session.get("role") != "aluno":
        return redirect(url_for("painel"))
    d = dict(current_aluno(), schedule=SCHEDULE_3110)
    from dashboard import upcoming_lessons
    return render_template("aluno_horario.html", d=d, upcoming=upcoming_lessons(SCHEDULE_3110))


@app.route("/avatar", methods=["GET", "POST"])
@login_required("avatar")
def avatar():
    """Ateliê persistente de avatar para o Campus Lobby."""
    if session.get("role") != "aluno":
        return redirect(url_for("painel"))
    if request.method == "POST":
        import secrets
        if not session.get('avatar_token') or not secrets.compare_digest(session['avatar_token'], request.form.get('token', '')):
            flash("Sessão expirada. Abra o ateliê novamente.")
            return redirect(url_for("avatar"))
        skin = request.form.get("skin", "#d7a27d")
        hair = request.form.get("hair", "#172033")
        shirt = request.form.get("shirt", "#367cf6")
        accessory = request.form.get("accessory", "none")
        options = {
            'appearance': ('masculine', 'feminine', 'neutral'),
            'hairstyle': ('short', 'fade', 'bob', 'long', 'waves', 'curls', 'bun', 'afro'),
            'outfit': ('hoodie', 'jacket', 'tee', 'uniform', 'varsity'),
            'bottom': ('trousers', 'cargo', 'shorts', 'skirt'),
            'shoes': ('sneakers', 'boots', 'hightop'),
        }
        current_style = get_avatar(session['username'])
        style = {key: request.form.get(key,current_style[key]) for key in options}
        skin_colors = {"#f0c7a8", "#d7a27d", "#b87a55", "#8d5a3b", "#6c4632", "#5a3829"}
        hair_colors = {"#172033", "#38241f", "#573522", "#8a5b3d", "#d2a06b", "#d43c6f"}
        shirt_colors = {"#367cf6", "#8a5cf6", "#15b895", "#ef7f3e", "#cf315f", "#e7b73d"}
        accessories = {"none", "glasses", "headphones", "earrings", "cap", "backpack"}
        if (skin not in skin_colors or hair not in hair_colors or shirt not in shirt_colors
                or accessory not in accessories
                or any(style[key] not in choices for key, choices in options.items())):
            flash("Escolha de avatar inválida.")
        else:
            save_avatar(session["username"], skin, hair, shirt, accessory, style)
            log_action(session["username"], "avatar_atualizado", accessory)
            flash("Avatar salvo no Campus Lobby.")
        return redirect(url_for("avatar"))
    import secrets
    session.setdefault('avatar_token', secrets.token_hex(24))
    return render_template("avatar.html", avatar=get_avatar(session["username"]), d=current_aluno(), token=session['avatar_token'])


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


def teacher_scope():
    import secrets
    from dashboard import CAMPUS_TZ, datetime
    assignments=get_teacher_assignments(session['username'])
    classes=sorted({a['class_name'] for a in assignments})
    source=request.form if request.method=='POST' else request.args
    selected=source.get('turma',classes[0] if classes else '')
    students=scoped_roster(assignments,ROSTER,selected) if selected else []
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
        return director_section('turmas')
    if session.get('role')!='professor':return redirect(url_for('painel'))
    try: ctx=teacher_scope()
    except ValueError as error:return str(error),403
    ctx['class_counts']={name:sum(s['turma']==name for s in ROSTER) for name in ctx['classes']}
    return render_template('professor_turmas.html',**ctx)

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
            n1,n2=validated_grades(ctx['assignments'],ROSTER,ctx['selected'],discipline,
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
            valid=validated_attendance(ctx['roster'],selected_date,marks,date.fromisoformat(ctx['today']))
            save_attendance_batch(selected_date,valid)
            log_action(session['username'],'chamada_registrada',f"{ctx['selected']} · {selected_date}")
            flash('Chamada salva para '+selected_date+'.')
            return redirect(url_for('chamada',turma=ctx['selected'],data=selected_date))
        except ValueError as exc:error=str(exc)
    return render_template('professor_chamada.html',**ctx,selected_date=selected_date,attendance=marks,
                           registered=sum(s['id'] in persisted for s in ctx['roster']),error=error),422 if error else 200


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
    import secrets
    eligible = [u for u in list_users() if u["username"] != session["username"] and u["active"]]
    if request.method == "POST":
        if session.get('role') in ('aluno','professor','admin'):
            if not session.get('message_token') or not secrets.compare_digest(session['message_token'], request.form.get('token', '')):
                flash("Sessão expirada. Abra as mensagens novamente.")
                return redirect(url_for("mensagens"))
            if request.form.get('action') == 'read':
                mark_message_read(request.form.get('message_id', type=int), session['username'])
                return redirect(url_for("mensagens"))
        recipient = request.form.get("recipient", "")
        subject = request.form.get("subject", "").strip()
        body = request.form.get("body", "").strip()
        if recipient in {u['username'] for u in eligible} and subject and body and len(subject) <= 160 and len(body) <= 10000:
            send_message(session["username"], recipient, subject, body)
            log_action(session["username"], "mensagem_enviada", recipient)
            flash("Mensagem enviada.")
        else:
            flash("Confira o destinatário e preencha assunto (até 160 caracteres) e mensagem (até 10.000).")
        return redirect(url_for("mensagens"))
    if session.get('role') in ('aluno','professor','admin'):
        session.setdefault('message_token', secrets.token_hex(24))
        return render_template("aluno_mensagens.html", messages=get_messages(session['username']),
                               users=eligible, token=session['message_token'])
    return render_template("mensagens.html", messages=get_messages(session["username"]),
                           users=[u for u in list_users() if u["username"] != session["username"] and u["active"]])


@app.route("/exercicios", methods=["GET", "POST"])
@login_required("exercicios")
def exercicios():
    if session.get('role')=='professor':
        return studio('exercicios')
    if session.get("role") == "admin":
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
            allowed = {e['id'] for e in get_exercises() if e['class_name'] == current_aluno()['turma']}
            if exercise_id not in allowed or not answer or len(answer) > 20000:
                flash("Entrega inválida. Confira a atividade e escreva uma resposta de até 20.000 caracteres.")
                return redirect(url_for("exercicios"))
            submit_exercise(exercise_id, session["username"], answer)
            log_action(session["username"], "exercicio_entregue", request.form["exercise_id"])
            flash("Resposta entregue com sucesso.")
        return redirect(url_for("exercicios"))
    submissions = get_submissions(session["username"] if session["role"] == "aluno" else None)
    if session["role"] == "aluno":
        import secrets
        from dashboard import CAMPUS_TZ, datetime
        session.setdefault('exercise_token', secrets.token_hex(24))
        exercises = [e for e in get_exercises() if e['class_name'] == current_aluno()['turma']]
        return render_template("aluno_exercicios.html", exercises=exercises,
                               submitted={s['exercise_id']: s for s in submissions},
                               today=datetime.now(CAMPUS_TZ).date().isoformat(),
                               token=session['exercise_token'])
    return render_template("exercicios.html", exercises=get_exercises(), submissions=submissions)


@app.errorhandler(404)
def not_found(_error):
    return render_template(
        "error.html", status=404, title="Caminho não encontrado",
        message="Este espaço não existe no campus ou mudou de endereço.",
    ), 404


@app.errorhandler(500)
def internal_error(_error):
    return render_template(
        "error.html", status=500, title="Algo saiu do lugar",
        message="Não foi possível concluir esta ação. Seus dados anteriores continuam preservados.",
    ), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
