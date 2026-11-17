-- v4.1 upgrade: Save clubs per verified user. Run original schema.sql first.
-- Idempotent: safe to run again if this migration has already been applied.

create table if not exists public.saved_clubs (
  user_id uuid not null references auth.users(id) on delete cascade,
  club_id text not null check (char_length(club_id) between 1 and 120),
  saved_at timestamptz not null default now(),
  primary key (user_id, club_id)
);

create index if not exists saved_clubs_user_idx on public.saved_clubs(user_id);
alter table public.saved_clubs enable row level security;
revoke all on public.saved_clubs from anon, authenticated;
grant select, insert, update, delete on public.saved_clubs to authenticated;

-- Reuse the same verified-UCSD ownership check from the v4 schema.
drop policy if exists "select own saved clubs" on public.saved_clubs;
create policy "select own saved clubs" on public.saved_clubs for select to authenticated
using (public.is_ucsd_account() and (select auth.uid()) = user_id);

drop policy if exists "insert own saved clubs" on public.saved_clubs;
create policy "insert own saved clubs" on public.saved_clubs for insert to authenticated
with check (public.is_ucsd_account() and (select auth.uid()) = user_id);

drop policy if exists "delete own saved clubs" on public.saved_clubs;
create policy "delete own saved clubs" on public.saved_clubs for delete to authenticated
using (public.is_ucsd_account() and (select auth.uid()) = user_id);
