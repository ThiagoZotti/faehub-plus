"""Institution management backed by the configured FaeHub+ database."""
import csv
import io
import re
import secrets
from datetime import date
from flask import request, session, render_template, redirect, url_for, flash, Response
from werkzeug.security import generate_password_hash
import database as db
import p1_operations as operations


def init_director():
    with db.connection() as conn:
        conn.executescript('''CREATE TABLE IF NOT EXISTS institution_settings (
            key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS class_settings (
            class_name TEXT PRIMARY KEY,capacity INTEGER,shift TEXT NOT NULL DEFAULT 'Manhã');
            CREATE TABLE IF NOT EXISTS auth_versions (
            username TEXT PRIMARY KEY REFERENCES users(username),version INTEGER NOT NULL DEFAULT 0);''')


def settings():
    result=dict(name='ETESC / FAETEC Santa Cruz',year=str(date.today().year),contact='')
    with db.connection() as conn:result.update({r['key']:r['value'] for r in conn.execute('SELECT * FROM institution_settings')})
    return result


def access_version(username):
    with db.connection() as conn:
        row=conn.execute('SELECT version FROM auth_versions WHERE username=?',(username,)).fetchone()
    return row['version'] if row else 0


def account_access(username):
    """Return all request-auth state in one database round-trip."""
    with db.connection() as conn:
        row=conn.execute('''SELECT u.active,COALESCE(ar.role,u.role) role,
                                   COALESCE(av.version,0) auth_version
                            FROM users u
                            LEFT JOIN account_roles ar ON ar.username=u.username
                            LEFT JOIN auth_versions av ON av.username=u.username
                            WHERE u.username=?''',(username,)).fetchone()
    return dict(row) if row else None


def valid_account(username, role):
    with db.connection() as conn:
        row=conn.execute('''SELECT u.active,COALESCE(ar.role,u.role) role FROM users u
                            LEFT JOIN account_roles ar ON ar.username=u.username
                            WHERE u.username=?''',(username,)).fetchone()
    return bool(row and row['active'] and row['role']==('diretor' if role=='admin' else role))


def field(name,limit=160):
    value=request.form.get(name,'').strip()
    if not value or len(value)>limit:raise ValueError('Preencha os campos obrigatórios dentro dos limites indicados.')
    return value


def password():
    value=request.form.get('password','')
    if len(value)<10 or len(value)>128:raise ValueError('Use uma senha entre 10 e 128 caracteres.')
    return generate_password_hash(value)


def manage(section, roster, subjects):
    if session.get('role')!='admin':return 'Acesso restrito à direção.',403
    session.setdefault('director_token',secrets.token_hex(24))
    token=session['director_token'];error=None
    classes=sorted({s['turma'] for s in roster})
    if request.method=='POST':
        if not secrets.compare_digest(token,request.form.get('token','')):return 'Sessão expirada. Atualize a página.',400
        try:
            action=request.form.get('action','')
            allowed={'usuarios':{'create','update','status','password'},'turmas':{'class','assign','unassign'},'configuracoes':{'settings'}}
            if action not in allowed.get(section,set()):raise ValueError('Ação inválida para esta seção.')
            with db.connection() as conn:
                if section=='usuarios':
                    username=field('username',50).lower()
                    existing=conn.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
                    if action=='create':
                        if not re.fullmatch(r'[a-z0-9_.-]{3,50}',username):raise ValueError('Usuário: 3 a 50 letras sem acento, números, ponto, hífen ou sublinhado.')
                        role=request.form.get('role')
                        if role not in ('aluno','professor','diretor','responsavel'):raise ValueError('Perfil inválido.')
                        sid=request.form.get('student_id','') if role in ('aluno','responsavel') else None
                        if role in ('aluno','responsavel'):
                            if sid not in {s['id'] for s in roster}:raise ValueError('Selecione um aluno da lista cadastrada.')
                            if role=='aluno' and conn.execute('SELECT 1 FROM users WHERE student_id=?',(sid,)).fetchone():raise ValueError('Já existe uma conta para esta matrícula.')
                        stored_role='aluno' if role=='responsavel' else role
                        conn.execute('INSERT INTO users(username,password_hash,name,role,student_id) VALUES(?,?,?,?,?)',
                                     (username,password(),field('name'),stored_role,sid if role=='aluno' else None))
                        if role=='responsavel':
                            conn.execute('INSERT INTO account_roles(username,role) VALUES(?,?)',(username,role))
                            conn.execute('''INSERT INTO guardian_links(guardian_username,student_id,relationship)
                                            VALUES(?,?,?)''',(username,sid,'Responsável legal'))
                    else:
                        if not existing:raise ValueError('Conta não encontrada.')
                        if action=='update':conn.execute('UPDATE users SET name=? WHERE username=?',(field('name'),username))
                        elif action=='status':
                            if username==session['username']:raise ValueError('Você não pode desativar sua própria conta.')
                            active=request.form.get('active')
                            if active not in ('0','1'):raise ValueError('Status inválido.')
                            if active=='0' and existing['role']=='diretor' and conn.execute("SELECT COUNT(*) AS total FROM users WHERE role='diretor' AND active=TRUE").fetchone()['total']<=1:raise ValueError('Mantenha ao menos um diretor ativo.')
                            conn.execute('UPDATE users SET active=? WHERE username=?',(active=='1',username))
                        elif action=='password':conn.execute('UPDATE users SET password_hash=? WHERE username=?',(password(),username))
                        if action in ('status','password'):
                            conn.execute('INSERT INTO auth_versions(username,version) VALUES(?,1) ON CONFLICT(username) DO UPDATE SET version=version+1',(username,))
                elif section=='turmas':
                    class_name=field('class_name')
                    if class_name not in classes:raise ValueError('Turma não cadastrada.')
                    if action=='class':
                        try:capacity=int(request.form.get('capacity',''))
                        except ValueError:raise ValueError('Informe uma capacidade inteira.')
                        if not sum(s['turma']==class_name for s in roster)<=capacity<=500:raise ValueError('A capacidade deve comportar os alunos cadastrados e ser menor ou igual a 500.')
                        shift=request.form.get('shift')
                        if shift not in ('Manhã','Tarde','Noite','Integral'):raise ValueError('Turno inválido.')
                        conn.execute('INSERT INTO class_settings VALUES(?,?,?) ON CONFLICT(class_name) DO UPDATE SET capacity=excluded.capacity,shift=excluded.shift',(class_name,capacity,shift))
                    else:
                        teacher=field('teacher');discipline=field('discipline')
                        if action=='assign':
                            if discipline not in subjects:raise ValueError('Disciplina não está na grade cadastrada.')
                            if not conn.execute("SELECT 1 FROM users WHERE username=? AND role='professor' AND active=TRUE",(teacher,)).fetchone():raise ValueError('Selecione um professor ativo.')
                            conn.execute('INSERT OR IGNORE INTO teacher_assignments VALUES(?,?,?)',(teacher,class_name,discipline))
                        else:conn.execute('DELETE FROM teacher_assignments WHERE teacher=? AND class_name=? AND discipline=?',(teacher,class_name,discipline))
                else:
                    name=field('institution_name',120)
                    try:year=int(request.form.get('year',''))
                    except ValueError:raise ValueError('Ano letivo inválido.')
                    if not 2020<=year<=2100:raise ValueError('Ano letivo deve estar entre 2020 e 2100.')
                    contact=request.form.get('contact','').strip()
                    if len(contact)>160:raise ValueError('Contato deve ter até 160 caracteres.')
                    conn.executemany('INSERT INTO institution_settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', [('name',name),('year',str(year)),('contact',contact)])
                conn.execute('INSERT INTO activity_log(username,action,details) VALUES(?,?,?)',
                             (session['username'],'direcao_'+action,request.form.get('username') or request.form.get('class_name') or 'Instituição'))
            if section=='usuarios' and action=='update' and username==session['username']:
                session['display_name']=request.form['name'].strip()
            flash('Alteração salva com sucesso.')
            return redirect(url_for(section))
        except ValueError as exc:
            error=str(exc)
        except Exception as exc:
            if not db.is_integrity_error(exc):
                raise
            error='Cadastro já existente ou vínculo inválido. Confira os dados.'
    users=db.list_users() if section in ('painel','usuarios','turmas') else []
    with db.connection() as conn:
        assignments=[dict(r) for r in conn.execute('SELECT a.*,u.name FROM teacher_assignments a JOIN users u ON u.username=a.teacher ORDER BY class_name,discipline')] if section in ('painel','turmas') else []
        metadata={r['class_name']:dict(r) for r in conn.execute('SELECT * FROM class_settings')} if section=='turmas' else {}
        attendance=[dict(r) for r in conn.execute('SELECT * FROM attendance ORDER BY class_date DESC')] if section=='relatorios' else []
    start=request.args.get('start','');end=request.args.get('end','')
    try:
        if start:date.fromisoformat(start)
        if end:date.fromisoformat(end)
        if start and end and start>end:raise ValueError()
    except ValueError:return 'Período inválido.',400
    records=[r for r in attendance if (not start or r['class_date']>=start) and (not end or r['class_date']<=end)]
    grades=db.load_grades() if section in ('painel','relatorios') else []
    if request.args.get('export'):
        if section!='relatorios':return 'Exportação indisponível.',400
        kind=request.args['export'];output=io.StringIO();writer=csv.writer(output,delimiter=';')
        if kind=='attendance':headers=['Matrícula','Data','Presença'];values=[[r['student_id'],r['class_date'],r['status']] for r in records]
        elif kind=='grades':headers=['Matrícula','Disciplina','N1','N2'];values=[[r['student_id'],r['discipline'],r['n1'],r['n2']] for r in grades]
        elif kind=='documents':
            headers=['Protocolo','Matrícula','Documento','Situação','Solicitante','Data']
            values=[[r['protocol'],r['student_id'],r['document_type'],r['status'],r['requester_name'],r['requested_at']] for r in operations.list_document_requests()]
        elif kind=='diary':
            headers=['Professor','Turma','Disciplina','Data','Tempos','Situação','Conteúdo']
            values=[[r['teacher_name'],r['class_name'],r['discipline'],r['lesson_date'],r['class_hours'],r['status'],r['content']] for r in operations.list_diary_entries()]
        elif kind=='interventions':
            headers=['Matrícula','Categoria','Situação','Responsável','Registro','Plano']
            values=[[r['student_id'],r['category'],r['status'],r['opened_by_name'],r['summary'],r['plan']] for r in operations.list_interventions()]
        else:return 'Relatório inválido.',400
        writer.writerow(headers)
        for row in values:writer.writerow([("'"+str(v)) if str(v).lstrip().startswith(('=','+','-','@')) else v for v in row])
        return Response('\ufeff'+output.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename="faehub-{kind}.csv"','Cache-Control':'no-store'})
    stats=dict(accounts=len(users),active=sum(u['active'] for u in users),teachers=sum(u['role']=='professor' and u['active'] for u in users),
               students=len(roster),classes=len(classes),grades=len(grades),records=len(records),
               frequency=round(100*sum(r['status']=='presente' for r in records)/len(records),1) if records else None)
    class_rows=[dict(name=c,count=sum(s['turma']==c for s in roster),capacity=metadata.get(c,{}).get('capacity'),shift=metadata.get(c,{}).get('shift','Manhã')) for c in classes]
    return render_template('director.html',section=section,token=token,error=error,users=users,roster=roster,
                           classes=class_rows,assignments=assignments,subjects=subjects,stats=stats,settings=settings(),
                           logs=db.recent_logs(50) if section=='relatorios' else [],records=records,grades=grades,start=start,end=end,
                           p1_metrics=operations.p1_metrics() if section in ('painel','relatorios') else {},
                           retry={k:v for k,v in request.form.items() if k not in ('password','token')} if error else None),422 if error else 200
