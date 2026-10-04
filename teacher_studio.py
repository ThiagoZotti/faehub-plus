"""Teacher publishing workflows: owned records, reversible archives and reviews."""
import hashlib
import math
import secrets
from datetime import date
from flask import request, session, render_template, redirect, url_for, flash
import database as db
import p1_operations as operations


def text_field(name, limit):
    value=request.form.get(name,'').strip()
    label={'title':'o título','body':'o comunicado','description':'o enunciado','feedback':'o feedback'}.get(name,name)
    if not value or len(value)>limit:raise ValueError(f'Preencha {label} com até {limit} caracteres.')
    return value


def studio(kind):
    teacher=session['username']
    assignments=db.get_teacher_assignments(teacher)
    classes=sorted({a['class_name'] for a in assignments})
    session.setdefault('studio_token',secrets.token_hex(24))
    error=None
    notices=[n for n in db.get_notices() if n['teacher']==teacher]
    exercises=[e for e in db.get_exercises(include_archived=True) if e['teacher']==teacher]
    owned=notices if kind=='avisos' else exercises
    if request.method=='POST':
        if not secrets.compare_digest(session['studio_token'],request.form.get('token','')):
            return 'Sessão expirada. Atualize a página.',400
        try:
            action=request.form.get('action','create')
            item_id=request.form.get('id',type=int)
            item=next((r for r in owned if r['id']==item_id),None)
            if action not in ('create','edit','archive','restore','review'):raise ValueError('Ação inválida.')
            if action!='create' and not item:raise ValueError('Registro não pertence à sua conta.')
            if action in ('archive','restore'):
                if kind=='avisos':db.archive_notice(item_id,teacher,action=='archive')
                else:db.archive_exercise(item_id,teacher,action=='archive')
            elif action=='review':
                if kind!='exercicios':raise ValueError('Ação inválida.')
                submission_id=request.form.get('submission_id',type=int)
                submission=next((s for s in db.get_submissions() if s['id']==submission_id and s['exercise_id']==item_id),None)
                if not submission:raise ValueError('Entrega inválida.')
                try:score=float(request.form.get('score','').replace(',','.'))
                except ValueError:raise ValueError('Informe uma nota de 0 a 10.')
                if not math.isfinite(score) or not 0<=score<=10:raise ValueError('Informe uma nota de 0 a 10.')
                db.review_submission(submission_id,teacher,text_field('feedback',10000),score,request.form.get('answer_snapshot',''))
            else:
                class_name=item['class_name'] if item else request.form.get('class_name','')
                if class_name not in classes:raise ValueError('Turma não vinculada à sua conta.')
                title=text_field('title',160)
                if kind=='avisos':
                    priority=request.form.get('priority','normal')
                    if priority not in ('normal','importante'):raise ValueError('Prioridade inválida.')
                    db.save_notice(teacher,class_name,title,text_field('body',10000),priority,item_id if item else None)
                else:
                    validated=operations.validate_upload(request.files.get('attachment'))
                    description=text_field('description',20000)
                    due_date=request.form.get('due_date','')
                    try:date.fromisoformat(due_date)
                    except ValueError:raise ValueError('Informe uma data de entrega válida.')
                    if item:
                        db.edit_exercise(item_id,teacher,title,description,due_date)
                        exercise_id=item_id
                    else:
                        discipline=request.form.get('discipline','')
                        if not any(a['class_name']==class_name and a['discipline']==discipline for a in assignments):
                            raise ValueError('Disciplina não vinculada à turma.')
                        exercise_id=db.create_exercise(teacher,title,description,discipline,class_name,due_date)
                    operations.save_attachment(teacher,'exercise',exercise_id,validated=validated)
            db.log_action(teacher,kind+'_'+action,str(item_id or 'novo'))
            flash('Alteração salva. Publicações ativas e correções ficam disponíveis para os alunos.')
            return redirect(url_for(kind))
        except ValueError as exc:error=str(exc)
    ids={e['id'] for e in exercises}
    submissions=[s for s in db.get_submissions() if s['exercise_id'] in ids]
    exercise_attachments={}
    for attachment in operations.list_attachments('exercise',list(ids)):
        exercise_attachments.setdefault(attachment['entity_id'],[]).append(attachment)
    submission_attachments={}
    for attachment in operations.list_attachments('submission',[s['id'] for s in submissions]):
        submission_attachments.setdefault(attachment['entity_id'],[]).append(attachment)
    return render_template('professor_studio.html',kind=kind,items=owned,classes=classes,assignments=assignments,
                           submissions=submissions,token=session['studio_token'],error=error,
                           exercise_attachments=exercise_attachments,
                           submission_attachments=submission_attachments),422 if error else 200


def student_notices(class_name, legacy):
    current=[dict(key=f"notice:{n['id']}",titulo=n['title'],desc=n['body'],
                  quando=f"{n['priority'].title()} · {n['updated_at'][:10]}")
             for n in db.get_notices() if n['class_name']==class_name and not n['archived']]
    historic=[]
    for item in legacy:
        digest=hashlib.sha256(
            f"{item['titulo']}|{item['desc']}|{item['quando']}".encode('utf-8')
        ).hexdigest()[:20]
        historic.append(dict(item,key=f"legacy:{digest}"))
    return current+historic
