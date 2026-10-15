-- Additive: retain existing slots and the closed academic history.
alter table public.schedule_slots add column if not exists active boolean not null default true;
alter table public.schedule_slots add column if not exists revision integer not null default 1;
-- Existing RLS and private-server-only grants remain unchanged.
