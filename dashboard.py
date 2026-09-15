"""Resumo do aluno calculado a partir dos registros disponíveis."""
from datetime import datetime, timedelta, timezone

CAMPUS_TZ = timezone(timedelta(hours=-3))
DAY_NAMES = ('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo')


def upcoming_lessons(schedule, now=None):
    now = now or datetime.now(CAMPUS_TZ)
    lessons = []
    for offset in range(8):
        day = now.date() + timedelta(days=offset)
        if day.weekday() >= len(schedule['dias']):
            continue
        for index, clock in enumerate(schedule['horarios']):
            subject = schedule['grade'][index][day.weekday()]
            if not subject:
                continue
            hour, minute = map(int, clock.split(':'))
            start = datetime(day.year, day.month, day.day, hour, minute, tzinfo=CAMPUS_TZ)
            if start < now:
                continue
            lessons.append({'subject': subject, 'time': clock, 'iso': start.isoformat(),
                            'date': day.strftime('%d/%m'),
                            'day': 'Hoje' if offset == 0 else ('Amanhã' if offset == 1 else DAY_NAMES[day.weekday()])})
    return lessons[:5]


def student_summary(student, exercises, submissions, messages, schedule, now=None):
    now = now or datetime.now(CAMPUS_TZ)
    submitted = {item['exercise_id'] for item in submissions}
    exercises = [dict(item) for item in exercises if item['class_name'] == student['turma']]
    pending = []
    activity_preview = []
    for exercise in exercises:
        is_completed = exercise['id'] in submitted
        try:
            deadline = datetime.strptime(exercise['due_date'], '%Y-%m-%d').date()
            days = (deadline - now.date()).days
            exercise.update(overdue=not is_completed and days < 0, due_label=deadline.strftime('%d/%m'),
                            urgency='Concluída' if is_completed else ('Prazo encerrado' if days < 0 else ('Entrega hoje' if days == 0 else f'Entrega até {deadline:%d/%m}')))
        except ValueError:
            exercise.update(overdue=False, due_label='A confirmar', urgency='Concluída' if is_completed else 'Sem prazo válido')
        activity_preview.append(exercise)
        if not is_completed:
            pending.append(exercise)
    completed = sum(item['id'] in submitted for item in exercises)
    return {'pending': pending, 'activity_preview': activity_preview, 'pending_count': len(pending), 'completed': completed,
            'total': len(exercises), 'completion': round(completed / len(exercises) * 100) if exercises else 0,
            'overdue': sum(item['overdue'] for item in pending),
            'messages': messages[:2], 'message_count': len(messages),
            'unread_count': sum(not item.get('is_read', 0) for item in messages),
            'lessons': upcoming_lessons(schedule, now), 'now': now.isoformat(),
            'date_label': f'{DAY_NAMES[now.weekday()]}, {now:%d/%m}',
            'best': max(student['grades'], key=lambda item: item['media'], default=None),
            'attention': [item for item in student['grades'] if item['media'] < 6]}
