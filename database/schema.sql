-- Campus Event Hub v4.1: run in Supabase SQL Editor BEFORE enabling account features.
-- Uses a publishable/anon key from Streamlit; NEVER put a service_role key in app secrets.

create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text check (char_length(display_name) <= 80),
  class_standing text check (char_length(class_standing) <= 40),
  major text check (char_length(major) <= 120),
  default_reminder_hours smallint check (default_reminder_hours in (1,3,24)),
  created_at timestamptz not null default now()
);

create table if not exists public.saved_events (
  user_id uuid not null references auth.users(id) on delete cascade,
  event_id text not null check (char_length(event_id) between 1 and 120),
  reminder_hours smallint check (reminder_hours in (1,3,24)),
  saved_at timestamptz not null default now(),
  primary key (user_id, event_id)
);

create index if not exists saved_events_user_idx on public.saved_events(user_id);

alter table public.profiles enable row level security;
alter table public.saved_events enable row level security;

revoke all on public.profiles from anon, authenticated;
revoke all on public.saved_events from anon, authenticated;
grant select, insert, update, delete on public.profiles to authenticated;
grant select, insert, update, delete on public.saved_events to authenticated;

-- RLS verifies BOTH record ownership and that the trusted JWT email belongs to UCSD.
-- Supabase Auth must also have email confirmation enabled, and the app uses email OTP.
-- Enable the Before User Created hook below to block non-UCSD signup at the Auth layer.
create or replace function public.is_ucsd_account()
returns boolean language sql stable as $$
  select (select auth.uid()) is not null
      and lower(coalesce((select auth.jwt()) ->> 'email', '')) ~ '^[a-z0-9._%+-]+@ucsd[.]edu$';
$$;
revoke all on function public.is_ucsd_account() from public, anon;
grant execute on function public.is_ucsd_account() to authenticated;

drop policy if exists "select own profile" on public.profiles;
create policy "select own profile" on public.profiles for select to authenticated
using (public.is_ucsd_account() and (select auth.uid()) = user_id);
drop policy if exists "insert own profile" on public.profiles;
create policy "insert own profile" on public.profiles for insert to authenticated
with check (public.is_ucsd_account() and (select auth.uid()) = user_id);
drop policy if exists "update own profile" on public.profiles;
create policy "update own profile" on public.profiles for update to authenticated
using (public.is_ucsd_account() and (select auth.uid()) = user_id)
with check (public.is_ucsd_account() and (select auth.uid()) = user_id);
drop policy if exists "delete own profile" on public.profiles;
create policy "delete own profile" on public.profiles for delete to authenticated
using (public.is_ucsd_account() and (select auth.uid()) = user_id);

drop policy if exists "select own saved events" on public.saved_events;
create policy "select own saved events" on public.saved_events for select to authenticated
using (public.is_ucsd_account() and (select auth.uid()) = user_id);
drop policy if exists "insert own saved events" on public.saved_events;
create policy "insert own saved events" on public.saved_events for insert to authenticated
with check (public.is_ucsd_account() and (select auth.uid()) = user_id);
drop policy if exists "update own saved events" on public.saved_events;
create policy "update own saved events" on public.saved_events for update to authenticated
using (public.is_ucsd_account() and (select auth.uid()) = user_id)
with check (public.is_ucsd_account() and (select auth.uid()) = user_id);
drop policy if exists "delete own saved events" on public.saved_events;
create policy "delete own saved events" on public.saved_events for delete to authenticated
using (public.is_ucsd_account() and (select auth.uid()) = user_id);

-- Optional server-side signup guard: create function below, then activate it via
-- Dashboard > Authentication > Hooks > Before User Created > Postgres function.
-- RLS above protects the per-user tables even if the hook is not yet enabled.
create or replace function public.restrict_ucsd_signup(event jsonb)
returns jsonb language plpgsql as $$
declare email_text text;
begin
  email_text := lower(coalesce(event->'user'->>'email',''));
  if email_text !~ '^[a-z0-9._%+-]+@ucsd[.]edu$' then
    return jsonb_build_object('error', jsonb_build_object(
      'http_code', 403, 'message', 'Please use a UCSD email address.'
    ));
  end if;
  return '{}'::jsonb;
end;
$$;
grant execute on function public.restrict_ucsd_signup(jsonb) to supabase_auth_admin;
revoke execute on function public.restrict_ucsd_signup(jsonb) from public, anon, authenticated;

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
