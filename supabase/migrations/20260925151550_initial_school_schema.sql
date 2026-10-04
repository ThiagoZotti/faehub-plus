-- FaeHub+ / Supabase PostgreSQL foundation.
-- The legacy-compatible tables keep the current Flask application operational
-- while the normalized academic model becomes the source of truth.

create table public.users (
  username text primary key,
  password_hash text not null,
  name text not null,
  role text not null check (role in ('diretor', 'professor', 'aluno')),
  student_id text unique,
  active boolean not null default true,
  auth_user_id uuid unique references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.grades (
  student_id text not null,
  discipline text not null,
  n1 numeric(5,2) not null check (n1 between 0 and 10),
  n2 numeric(5,2) not null check (n2 between 0 and 10),
  updated_at timestamptz not null default now(),
  primary key (student_id, discipline)
);

create table public.attendance (
  student_id text not null,
  class_date date not null,
  status text not null check (status in ('presente', 'ausente')),
  primary key (student_id, class_date)
);

create table public.activity_log (
  id bigint generated always as identity primary key,
  username text not null,
  action text not null,
  details text,
  created_at timestamptz not null default now()
);

create table public.institution_settings (
  key text primary key,
  value text not null
);

create table public.class_settings (
  class_name text primary key,
  capacity integer check (capacity is null or capacity > 0),
  shift text not null default 'Manhã'
    check (shift in ('Manhã', 'Tarde', 'Noite', 'Integral'))
);

create table public.auth_versions (
  username text primary key references public.users(username) on delete cascade,
  version integer not null default 0 check (version >= 0)
);

create table public.messages (
  id bigint generated always as identity primary key,
  sender text not null references public.users(username),
  recipient text not null references public.users(username),
  subject text not null,
  body text not null,
  is_read boolean not null default false,
  created_at timestamptz not null default now()
);

create table public.exercises (
  id bigint generated always as identity primary key,
  teacher text not null references public.users(username),
  title text not null,
  description text not null,
  discipline text not null,
  class_name text not null default '3110',
  due_date date not null,
  created_at timestamptz not null default now()
);

create table public.submissions (
  id bigint generated always as identity primary key,
  exercise_id bigint not null references public.exercises(id) on delete cascade,
  student text not null references public.users(username),
  answer text not null,
  submitted_at timestamptz not null default now(),
  unique (exercise_id, student)
);

create table public.teacher_assignments (
  teacher text not null references public.users(username) on delete cascade,
  class_name text not null,
  discipline text not null,
  primary key (teacher, class_name, discipline)
);

create table public.notices (
  id bigint generated always as identity primary key,
  teacher text not null references public.users(username),
  class_name text not null,
  title text not null,
  body text not null,
  priority text not null default 'normal'
    check (priority in ('normal', 'importante', 'urgente')),
  archived boolean not null default false,
  updated_at timestamptz not null default now()
);

create table public.exercise_states (
  exercise_id bigint primary key references public.exercises(id) on delete cascade,
  archived boolean not null default false
);

create table public.submission_reviews (
  submission_id bigint primary key references public.submissions(id) on delete cascade,
  feedback text not null,
  score numeric(5,2) not null check (score between 0 and 10),
  answer_snapshot text not null,
  reviewed_at timestamptz not null default now()
);

create table public.avatar_styles (
  username text primary key references public.users(username) on delete cascade,
  appearance text not null default 'masculine',
  hairstyle text not null default 'short',
  outfit text not null default 'hoodie',
  bottom text not null default 'trousers',
  shoes text not null default 'sneakers'
);

create table public.avatar_profiles (
  username text primary key references public.users(username) on delete cascade,
  skin text not null default '#d7a27d',
  hair text not null default '#172033',
  shirt text not null default '#367cf6',
  accessory text not null default 'none',
  updated_at timestamptz not null default now()
);

create table public.legacy_attendance_archive (
  legacy_student_id text not null,
  canonical_student_id text not null,
  class_date date not null,
  status text not null,
  migrated_at timestamptz not null default now(),
  primary key (legacy_student_id, class_date, status)
);

create table public.legacy_grade_archive (
  legacy_student_id text not null,
  canonical_student_id text not null,
  discipline text not null,
  n1 numeric(5,2) not null,
  n2 numeric(5,2) not null,
  source_updated_at timestamptz not null,
  migrated_at timestamptz not null default now(),
  primary key (legacy_student_id, discipline, source_updated_at, n1, n2)
);

create table public.seed_markers (
  name text primary key
);

-- Normalized academic model -------------------------------------------------

create table public.academic_years (
  id bigint generated always as identity primary key,
  name text not null unique,
  starts_on date not null,
  ends_on date not null,
  status text not null default 'planning'
    check (status in ('planning', 'active', 'closed', 'archived')),
  check (ends_on >= starts_on)
);

create table public.academic_periods (
  id bigint generated always as identity primary key,
  academic_year_id bigint not null references public.academic_years(id) on delete cascade,
  name text not null,
  period_number smallint not null check (period_number > 0),
  starts_on date not null,
  ends_on date not null,
  status text not null default 'planning'
    check (status in ('planning', 'open', 'closed')),
  unique (academic_year_id, period_number),
  check (ends_on >= starts_on)
);

create table public.courses (
  id bigint generated always as identity primary key,
  code text not null unique,
  name text not null,
  description text,
  active boolean not null default true
);

create table public.subjects (
  id bigint generated always as identity primary key,
  code text not null unique,
  name text not null,
  workload_minutes integer check (workload_minutes is null or workload_minutes > 0),
  active boolean not null default true
);

create table public.classes (
  id bigint generated always as identity primary key,
  academic_year_id bigint not null references public.academic_years(id),
  course_id bigint references public.courses(id),
  code text not null,
  grade_label text,
  shift text not null check (shift in ('Manhã', 'Tarde', 'Noite', 'Integral')),
  room text,
  capacity integer not null check (capacity > 0),
  status text not null default 'active'
    check (status in ('planning', 'active', 'closed', 'archived')),
  unique (academic_year_id, code)
);

create table public.class_subjects (
  id bigint generated always as identity primary key,
  class_id bigint not null references public.classes(id) on delete cascade,
  subject_id bigint not null references public.subjects(id),
  workload_minutes integer check (workload_minutes is null or workload_minutes > 0),
  unique (class_id, subject_id)
);

create table public.students (
  id bigint generated always as identity primary key,
  registration text not null unique,
  user_username text unique references public.users(username) on delete set null,
  full_name text not null,
  birth_date date,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.enrollments (
  id bigint generated always as identity primary key,
  student_id bigint not null references public.students(id),
  class_id bigint not null references public.classes(id),
  status text not null default 'active'
    check (status in ('active', 'transferred', 'withdrawn', 'completed', 'cancelled')),
  enrolled_on date not null default current_date,
  ended_on date,
  created_at timestamptz not null default now(),
  check (ended_on is null or ended_on >= enrolled_on)
);

create unique index enrollments_one_active_class_idx
  on public.enrollments (student_id, class_id)
  where status = 'active';

create table public.teacher_subjects (
  id bigint generated always as identity primary key,
  teacher_username text not null references public.users(username),
  class_subject_id bigint not null references public.class_subjects(id) on delete cascade,
  valid_from date not null default current_date,
  valid_until date,
  unique (teacher_username, class_subject_id, valid_from),
  check (valid_until is null or valid_until >= valid_from)
);

create table public.schedule_slots (
  id bigint generated always as identity primary key,
  class_subject_id bigint not null references public.class_subjects(id) on delete cascade,
  weekday smallint not null check (weekday between 1 and 7),
  starts_at time not null,
  ends_at time not null,
  room text,
  check (ends_at > starts_at),
  unique (class_subject_id, weekday, starts_at)
);

create table public.assessments (
  id bigint generated always as identity primary key,
  class_subject_id bigint not null references public.class_subjects(id) on delete cascade,
  academic_period_id bigint not null references public.academic_periods(id),
  title text not null,
  assessment_type text not null,
  max_score numeric(6,2) not null default 10 check (max_score > 0),
  weight numeric(7,3) not null default 1 check (weight > 0),
  due_on date,
  published_at timestamptz,
  created_at timestamptz not null default now()
);

create table public.assessment_scores (
  id bigint generated always as identity primary key,
  assessment_id bigint not null references public.assessments(id) on delete cascade,
  enrollment_id bigint not null references public.enrollments(id) on delete cascade,
  score numeric(6,2),
  status text not null default 'pending'
    check (status in ('pending', 'graded', 'absent', 'excused')),
  feedback text,
  published_at timestamptz,
  updated_at timestamptz not null default now(),
  unique (assessment_id, enrollment_id),
  check (score is null or score >= 0)
);

create table public.lessons (
  id bigint generated always as identity primary key,
  class_subject_id bigint not null references public.class_subjects(id),
  teacher_username text references public.users(username),
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  topic text,
  status text not null default 'scheduled'
    check (status in ('scheduled', 'completed', 'cancelled')),
  check (ends_at > starts_at)
);

create table public.attendance_records (
  id bigint generated always as identity primary key,
  lesson_id bigint not null references public.lessons(id) on delete cascade,
  enrollment_id bigint not null references public.enrollments(id) on delete cascade,
  status text not null check (status in ('present', 'absent', 'late', 'excused', 'dismissed')),
  note text,
  recorded_at timestamptz not null default now(),
  unique (lesson_id, enrollment_id)
);

-- Foreign keys are not indexed automatically by PostgreSQL.
create index messages_sender_idx on public.messages (sender, created_at desc);
create index messages_recipient_idx on public.messages (recipient, created_at desc);
create index exercises_teacher_idx on public.exercises (teacher);
create index exercises_class_due_idx on public.exercises (class_name, due_date);
create index submissions_student_idx on public.submissions (student);
create index teacher_assignments_class_idx on public.teacher_assignments (class_name, discipline);
create index notices_class_updated_idx on public.notices (class_name, updated_at desc);
create index academic_periods_year_idx on public.academic_periods (academic_year_id);
create index classes_year_idx on public.classes (academic_year_id);
create index classes_course_idx on public.classes (course_id);
create index class_subjects_class_idx on public.class_subjects (class_id);
create index class_subjects_subject_idx on public.class_subjects (subject_id);
create index enrollments_student_idx on public.enrollments (student_id);
create index enrollments_class_idx on public.enrollments (class_id);
create index teacher_subjects_teacher_idx on public.teacher_subjects (teacher_username);
create index teacher_subjects_class_subject_idx on public.teacher_subjects (class_subject_id);
create index schedule_slots_class_subject_idx on public.schedule_slots (class_subject_id);
create index assessments_class_subject_idx on public.assessments (class_subject_id);
create index assessments_period_idx on public.assessments (academic_period_id);
create index assessment_scores_enrollment_idx on public.assessment_scores (enrollment_id);
create index lessons_class_subject_starts_idx on public.lessons (class_subject_id, starts_at);
create index lessons_teacher_idx on public.lessons (teacher_username);
create index attendance_records_enrollment_idx on public.attendance_records (enrollment_id);

-- Phase one is server-side only. Data API access remains closed until Supabase
-- Auth is connected and ownership-aware policies can be introduced safely.
do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'users','grades','attendance','activity_log','institution_settings','class_settings',
    'auth_versions','messages','exercises','submissions','teacher_assignments','notices',
    'exercise_states','submission_reviews','avatar_styles','avatar_profiles',
    'legacy_attendance_archive','legacy_grade_archive','seed_markers','academic_years',
    'academic_periods','courses','subjects','classes','class_subjects','students',
    'enrollments','teacher_subjects','schedule_slots','assessments','assessment_scores',
    'lessons','attendance_records'
  ]
  loop
    execute format('alter table public.%I enable row level security', table_name);
    execute format('revoke all on table public.%I from anon, authenticated', table_name);
  end loop;
end $$;

revoke all on all sequences in schema public from anon, authenticated;
alter default privileges in schema public revoke all on tables from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;
