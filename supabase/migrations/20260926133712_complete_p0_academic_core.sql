-- P0 integrity: one current class per student and idempotent consolidated grades.
drop index if exists public.enrollments_one_active_class_idx;

create unique index if not exists enrollments_one_active_student_idx
  on public.enrollments (student_id)
  where status = 'active';

create unique index if not exists assessments_class_period_title_idx
  on public.assessments (class_subject_id, academic_period_id, title);

create index if not exists academic_years_status_starts_idx
  on public.academic_years (status, starts_on desc);

create index if not exists enrollments_class_status_idx
  on public.enrollments (class_id, status);
