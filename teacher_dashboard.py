"""Teacher overview: confirmed assignments and owned records only."""
from datetime import datetime, timedelta
from dashboard import CAMPUS_TZ, DAY_NAMES

def teacher_overview(username, assignments, schedule, roster, exercises, submissions, grades, messages, now=None):
    now=now or datetime.now(CAMPUS_TZ)
    classes=sorted({a['class_name'] for a in assignments})
    allowed={(a['class_name'],a['discipline']) for a in assignments}
    students=[s for s in roster if s['turma'] in classes]
    student_classes={s['id']:s['turma'] for s in students}
    owned=[e for e in exercises if e['teacher']==username]
    owned_ids={e['id'] for e in owned}
    received=[s for s in submissions if s['exercise_id'] in owned_ids]
    saved=[g for g in grades if (student_classes.get(g['student_id']),g['discipline']) in allowed]
    lessons=[]
    for offset in range(8):
        day=now.date()+timedelta(days=offset)
        if day.weekday()>=len(schedule['dias']):continue
        for row,clock in enumerate(schedule['horarios']):
            subject=schedule['grade'][row][day.weekday()]
            if ('3110',subject) not in allowed:continue
            start=datetime.combine(day,datetime.strptime(clock,'%H:%M').time(),tzinfo=CAMPUS_TZ)
            end=datetime.combine(day,datetime.strptime(schedule['fins'][row],'%H:%M').time(),tzinfo=CAMPUS_TZ)
            if end<=now:continue
            lessons.append(dict(subject=subject,class_name='3110',time=clock,end=schedule['fins'][row],
                                date=day.strftime('%d/%m'),day='Hoje' if offset==0 else ('Amanhã' if offset==1 else DAY_NAMES[day.weekday()]),
                                live=start<=now<end))
    return dict(assignments=assignments,classes=classes,student_count=len(students),
                lessons=lessons[:4],exercise_count=len(owned),submission_count=len(received),
                pending_reviews=sum(not s.get('reviewed_at') or s.get('answer_snapshot')!=s.get('answer') for s in received),
                grade_count=len(saved),unread=sum(m['recipient']==username and not m['is_read'] for m in messages),
                date_label=f'{DAY_NAMES[now.weekday()]}, {now:%d/%m}',name=username)
