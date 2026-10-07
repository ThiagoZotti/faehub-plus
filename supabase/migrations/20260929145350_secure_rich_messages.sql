-- Mensagens apagadas permanecem auditáveis e podem ser restauradas pelo autor.
alter table public.messages add column if not exists deleted_at timestamptz;
alter table public.messages add column if not exists deleted_by text references public.users(username);

create index if not exists messages_participants_created_idx
  on public.messages (sender, recipient, created_at desc);
create index if not exists messages_deleted_by_idx
  on public.messages (deleted_by) where deleted_by is not null;
