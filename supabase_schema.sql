-- Run once in a dedicated Supabase project. Only the trusted Flask server uses this table.
create table if not exists public.blackbox_state (
  kind text primary key check (kind in ('accounts', 'users')),
  payload jsonb not null default '{}'::jsonb
);
alter table public.blackbox_state enable row level security;
revoke all on public.blackbox_state from anon, authenticated;
