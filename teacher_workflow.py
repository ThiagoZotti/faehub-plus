"""Validation shared by the teacher's class, attendance and grade workflows."""
from datetime import date
import math

def scoped_roster(assignments, roster, class_name):
    if class_name not in {a['class_name'] for a in assignments}:
        raise ValueError('Turma não vinculada à sua conta.')
    return [s for s in roster if s['turma']==class_name]

def validated_grades(assignments, roster, class_name, discipline, student_id, n1, n2):
    students=scoped_roster(assignments,roster,class_name)
    if (class_name,discipline) not in {(a['class_name'],a['discipline']) for a in assignments}:
        raise ValueError('Disciplina não vinculada à sua conta.')
    if student_id not in {s['id'] for s in students}:
        raise ValueError('Aluno não pertence à turma selecionada.')
    try: values=[float(str(n).replace(',','.')) for n in (n1,n2)]
    except ValueError: raise ValueError('Informe N1 e N2 válidas.')
    if not all(math.isfinite(n) and 0<=n<=10 for n in values):
        raise ValueError('As duas notas devem estar entre 0 e 10.')
    return values

def validated_attendance(students, selected_date, marks, today):
    try: parsed=date.fromisoformat(selected_date)
    except ValueError: raise ValueError('Informe uma data válida.')
    if parsed>today: raise ValueError('Não é possível registrar presença em uma data futura.')
    if not students: raise ValueError('Não há alunos nesta turma.')
    if any(marks.get(s['id']) not in ('presente','ausente') for s in students):
        raise ValueError('Marque presente ou ausente para todos os alunos antes de salvar.')
    return {s['id']:marks[s['id']] for s in students}
