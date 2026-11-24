-- Campus Event Hub three-portal MVP.
-- Run AFTER database/schema.sql (which includes saved_clubs) in Supabase SQL Editor.
-- Use ONLY a publishable key in Streamlit. NEVER use a service-role key in app code.
-- Event data is club-authored and is NOT a campus room reservation or official UCSD listing.

create table if not exists public.hub_admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);

create or replace function public.hub_is_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.hub_admins where user_id = (select auth.uid()));
$$;
revoke all on function public.hub_is_admin() from public, anon;
grant execute on function public.hub_is_admin() to authenticated;

create table if not exists public.hub_reserved_clubs (
  club_key text primary key
);
-- workshop clubs are reserved by database/mvp_reserved_clubs.sql

create table if not exists public.hub_clubs (
  id uuid primary key default gen_random_uuid(),
  org_name text not null check (length(btrim(org_name)) between 1 and 120),
  category text not null check (length(category) between 1 and 80),
  org_size text not null check (org_size in ('Small','Medium','Large')),
  description text not null check (length(btrim(description)) between 1 and 2000),
  contact_email text,
  website_url text,
  owner_id uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);
create unique index if not exists hub_clubs_normalized_name_uidx
  on public.hub_clubs ((lower(regexp_replace(btrim(org_name), '[[:space:]]+', ' ', 'g'))));

create or replace function public.hub_check_reserved_name()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if exists (select 1 from public.hub_reserved_clubs r
    where r.club_key = lower(regexp_replace(btrim(new.org_name), '[[:space:]]+', ' ', 'g'))) then
    raise exception 'This club already exists in the workshop dataset; it cannot be claimed through self-registration';
  end if;
  return new;
end;
$$;
drop trigger if exists hub_reserved_name_guard on public.hub_clubs;
create trigger hub_reserved_name_guard before insert or update of org_name on public.hub_clubs
  for each row execute function public.hub_check_reserved_name();

create table if not exists public.hub_events (
  id uuid primary key default gen_random_uuid(),
  club_id uuid not null references public.hub_clubs(id),
  created_by uuid not null references auth.users(id),
  title text not null check (length(btrim(title)) between 1 and 150),
  event_date date not null,
  start_time time not null,
  end_time time not null,
  building text not null check (length(btrim(building)) between 1 and 200),
  room text,
  category text not null,
  description text not null check (length(btrim(description)) between 1 and 2000),
  external_url text,
  free_food boolean not null default false,
  status text not null default 'published' check (status in ('published','cancelled')),
  created_at timestamptz not null default now(),
  check (end_time > start_time)
);
create index if not exists hub_events_date_idx on public.hub_events(event_date,status);
create index if not exists hub_events_club_idx on public.hub_events(club_id);

create table if not exists public.hub_tickets (
  id uuid primary key default gen_random_uuid(),
  reporter_id uuid not null references auth.users(id),
  event_ref text,
  club_id uuid references public.hub_clubs(id),
  category text not null check (category in ('event_info','website_bug','account','other')),
  description text not null check (length(btrim(description)) between 10 and 2000),
  route text not null default 'client' check (route in ('club','developer','client')),
  status text not null default 'open' check (status in ('open','in_progress','resolved')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists hub_tickets_route_idx on public.hub_tickets(route,status);

create or replace function public.hub_ticket_insert_guard()
returns trigger language plpgsql set search_path=public as $$
begin
  -- Client never chooses the routing destination or changes ownership.
  new.route := case when new.category = 'event_info' and new.club_id is not null then 'club'
                    when new.category = 'website_bug' then 'developer'
                    else 'client' end;
  new.status := 'open';
  return new;
end;
$$;
drop trigger if exists hub_ticket_route on public.hub_tickets;
create trigger hub_ticket_route before insert on public.hub_tickets
  for each row execute function public.hub_ticket_insert_guard();

create or replace function public.hub_ticket_timestamp()
returns trigger language plpgsql set search_path=public as $$
begin
  new.updated_at := now(); return new;
end;
$$;
drop trigger if exists hub_ticket_updated on public.hub_tickets;
create trigger hub_ticket_updated before update on public.hub_tickets
  for each row execute function public.hub_ticket_timestamp();

alter table public.hub_admins enable row level security;
alter table public.hub_clubs enable row level security;
alter table public.hub_events enable row level security;
alter table public.hub_tickets enable row level security;
alter table public.hub_reserved_clubs enable row level security;

revoke all on public.hub_admins,public.hub_clubs,public.hub_events,public.hub_tickets,public.hub_reserved_clubs from anon, authenticated;
grant select on public.hub_clubs, public.hub_events to anon,authenticated;
grant insert, update on public.hub_clubs, public.hub_events to authenticated;
grant select on public.hub_admins to authenticated;
grant select, insert on public.hub_tickets to authenticated;
grant update (status) on public.hub_tickets to authenticated;

-- Only admin's own admin record is readable; inserting admins is SQL-editor-only.
drop policy if exists hub_admin_self on public.hub_admins;
create policy hub_admin_self on public.hub_admins for select to authenticated
  using (user_id = (select auth.uid()));

-- Everyone can browse club profiles; only its creator can edit its profile.
drop policy if exists hub_clubs_browse on public.hub_clubs;
create policy hub_clubs_browse on public.hub_clubs for select to anon,authenticated using (true);
drop policy if exists hub_clubs_create on public.hub_clubs;
create policy hub_clubs_create on public.hub_clubs for insert to authenticated
  with check (public.is_ucsd_account() and owner_id = (select auth.uid()));
drop policy if exists hub_clubs_owner_edit on public.hub_clubs;
create policy hub_clubs_owner_edit on public.hub_clubs for update to authenticated
  using (public.is_ucsd_account() and owner_id = (select auth.uid()))
  with check (public.is_ucsd_account() and owner_id = (select auth.uid()));

-- Published events are public; owner can see canceled events too.
drop policy if exists hub_events_browse on public.hub_events;
create policy hub_events_browse on public.hub_events for select to anon,authenticated
  using (status='published');
drop policy if exists hub_events_private_owner_read on public.hub_events;
create policy hub_events_private_owner_read on public.hub_events for select to authenticated
  using (created_by = (select auth.uid()) or (select public.hub_is_admin()));
drop policy if exists hub_events_create on public.hub_events;
create policy hub_events_create on public.hub_events for insert to authenticated
  with check (public.is_ucsd_account() and created_by = (select auth.uid())
    and exists(select 1 from public.hub_clubs c where c.id = club_id and c.owner_id = (select auth.uid())));
drop policy if exists hub_events_owner_edit on public.hub_events;
create policy hub_events_owner_edit on public.hub_events for update to authenticated
  using (public.is_ucsd_account() and created_by = (select auth.uid())
    and exists(select 1 from public.hub_clubs c where c.id = club_id and c.owner_id = (select auth.uid())))
  with check (public.is_ucsd_account() and created_by = (select auth.uid())
    and exists(select 1 from public.hub_clubs c where c.id = club_id and c.owner_id = (select auth.uid())));

-- A reporter sees their own tickets; owning club sees routed content tickets;
-- client admin sees all tickets (but cannot edit any club events).
drop policy if exists hub_tickets_read on public.hub_tickets;
create policy hub_tickets_read on public.hub_tickets for select to authenticated
  using (public.is_ucsd_account() and (
    reporter_id = (select auth.uid()) or (select public.hub_is_admin())
    or (route='club' and exists(
      select 1 from public.hub_clubs c where c.id=club_id and c.owner_id=(select auth.uid())))));
drop policy if exists hub_tickets_create on public.hub_tickets;
create policy hub_tickets_create on public.hub_tickets for insert to authenticated
  with check (public.is_ucsd_account() and reporter_id=(select auth.uid()));
drop policy if exists hub_tickets_resolve on public.hub_tickets;
create policy hub_tickets_resolve on public.hub_tickets for update to authenticated
  using (public.is_ucsd_account() and (
    (select public.hub_is_admin())
    or (route='club' and exists(
      select 1 from public.hub_clubs c where c.id=club_id and c.owner_id=(select auth.uid())))))
  with check (public.is_ucsd_account() and (
    (select public.hub_is_admin())
    or (route='club' and exists(
      select 1 from public.hub_clubs c where c.id=club_id and c.owner_id=(select auth.uid())))));

-- After an actual admin account signs in once, assign it in SQL Editor using its auth.users ID:
-- insert into public.hub_admins(user_id) values ('REAL-AUTH-USER-UUID');
