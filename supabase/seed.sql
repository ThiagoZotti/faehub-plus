-- Dados acadêmicos mínimos da demonstração 3110.
-- Contas, senhas e registros pessoais são importados pelo script de migração.

insert into public.academic_years (name, starts_on, ends_on, status)
values ('2026', '2026-02-02', '2026-12-18', 'active')
on conflict (name) do update set
  starts_on = excluded.starts_on,
  ends_on = excluded.ends_on,
  status = excluded.status;

insert into public.academic_periods
  (academic_year_id, name, period_number, starts_on, ends_on, status)
select y.id, p.name, p.period_number, p.starts_on, p.ends_on, p.status
from public.academic_years y
cross join (values
  ('1º trimestre', 1::smallint, '2026-02-02'::date, '2026-05-15'::date, 'closed'),
  ('2º trimestre', 2::smallint, '2026-05-18'::date, '2026-08-28'::date, 'closed'),
  ('3º trimestre', 3::smallint, '2026-08-31'::date, '2026-12-18'::date, 'open')
) as p(name, period_number, starts_on, ends_on, status)
where y.name = '2026'
on conflict (academic_year_id, period_number) do update set
  name = excluded.name,
  starts_on = excluded.starts_on,
  ends_on = excluded.ends_on,
  status = excluded.status;

insert into public.courses (code, name, description)
values ('DS', 'Desenvolvimento de Sistemas', 'Curso técnico integrado da ETESC/FAETEC.')
on conflict (code) do update set name = excluded.name, description = excluded.description;

insert into public.subjects (code, name) values
  ('MAT', 'Matemática'),
  ('FIS', 'Física'),
  ('ING', 'Inglês'),
  ('SOC', 'Sociologia'),
  ('FIL', 'Filosofia'),
  ('POE', 'POE'),
  ('BD', 'Banco de Dados'),
  ('PF', 'Projeto Final'),
  ('QUI', 'Química'),
  ('LP3', 'Linguagem de Programação III'),
  ('SMAS', 'SMAS'),
  ('PDM', 'Programação para Dispositivos Móveis'),
  ('BIO', 'Biologia'),
  ('HIS', 'História'),
  ('POR', 'Português'),
  ('GEO', 'Geografia')
on conflict (code) do update set name = excluded.name;

insert into public.classes
  (academic_year_id, course_id, code, grade_label, shift, room, capacity, status)
select y.id, c.id, '3110', '3º ano', 'Manhã', null, 40, 'active'
from public.academic_years y
join public.courses c on c.code = 'DS'
where y.name = '2026'
on conflict (academic_year_id, code) do update set
  course_id = excluded.course_id,
  grade_label = excluded.grade_label,
  shift = excluded.shift,
  capacity = excluded.capacity,
  status = excluded.status;

insert into public.class_subjects (class_id, subject_id)
select c.id, s.id
from public.classes c
join public.academic_years y on y.id = c.academic_year_id and y.name = '2026'
cross join public.subjects s
where c.code = '3110'
on conflict (class_id, subject_id) do nothing;
