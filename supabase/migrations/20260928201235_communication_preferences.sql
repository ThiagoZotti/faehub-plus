-- Preferências individuais de leitura e descarte reversível de comunicados.
-- O Flask acessa a tabela pelo servidor; a Data API pública permanece fechada.

create table public.communication_states (
  username text not null references public.users(username) on delete cascade,
  kind text not null check (kind in ('notice','notification')),
  item_key text not null,
  is_read boolean not null default false,
  dismissed_at timestamptz,
  updated_at timestamptz not null default now(),
  primary key (username,kind,item_key)
);

create index communication_states_user_idx
  on public.communication_states (username,kind,dismissed_at);

alter table public.communication_states enable row level security;
revoke all on table public.communication_states from anon, authenticated;
