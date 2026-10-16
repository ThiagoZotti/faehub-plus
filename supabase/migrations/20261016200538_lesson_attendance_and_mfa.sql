-- The runtime uses Python weekday: Monday=0, Sunday=6.
-- Only an empty legacy schedule can be adopted automatically; populated
-- installations need an explicit 1-based -> 0-based data migration first.
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM public.schedule_slots) THEN
    RAISE EXCEPTION 'Review existing schedule weekday values before adopting Python weekday';
  END IF;
END $$;
ALTER TABLE public.schedule_slots DROP CONSTRAINT schedule_slots_weekday_check;
ALTER TABLE public.schedule_slots ADD CONSTRAINT schedule_slots_weekday_check CHECK (weekday BETWEEN 0 AND 6);

ALTER TABLE public.lessons ADD COLUMN IF NOT EXISTS attendance_revision integer NOT NULL DEFAULT 0;
CREATE UNIQUE INDEX IF NOT EXISTS lessons_subject_start_idx ON public.lessons(class_subject_id,starts_at);
CREATE INDEX IF NOT EXISTS attendance_enrollment_idx ON public.attendance_records(enrollment_id,lesson_id);

CREATE TABLE public.account_mfa (
  username text PRIMARY KEY REFERENCES public.users(username),secret_ciphertext text,
  pending_ciphertext text,pending_until bigint,enabled boolean NOT NULL DEFAULT false,
  last_counter bigint NOT NULL DEFAULT -1
);
CREATE TABLE public.mfa_recovery_codes (
  username text NOT NULL REFERENCES public.account_mfa(username),code_hash text NOT NULL,
  used_at timestamptz,PRIMARY KEY(username,code_hash)
);
ALTER TABLE public.account_mfa ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mfa_recovery_codes ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.account_mfa,public.mfa_recovery_codes FROM anon,authenticated,PUBLIC;
