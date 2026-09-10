"""Calendar presentation based only on persisted attendance records."""
import calendar
from datetime import date

MONTHS = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
          'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro')

def attendance_calendar(records, month=None, today=None):
    today = today or date.today()
    try:
        selected = date.fromisoformat((month or today.strftime('%Y-%m')) + '-01')
        if not 1901 <= selected.year <= 2099:
            raise ValueError('Unsupported year')
    except ValueError:
        selected = today.replace(day=1)
    by_date = {r['class_date']: r['status'] for r in records}
    weeks = []
    for week in calendar.Calendar().monthdayscalendar(selected.year, selected.month):
        weeks.append([{'day': n, 'date': selected.replace(day=n).isoformat(),
                       'status': by_date.get(selected.replace(day=n).isoformat(), 'unrecorded'),
                       'today': selected.replace(day=n) == today} if n else None for n in week])
    prefix = selected.strftime('%Y-%m')
    rows = [dict(r) for r in records if r['class_date'].startswith(prefix)]
    return dict(weeks=weeks, month=prefix, title=f'{MONTHS[selected.month-1]} {selected.year}',
                rows=rows, present=sum(r['status'] == 'presente' for r in rows),
                absent=sum(r['status'] == 'ausente' for r in rows))
