"""Shared persistence for all three portals.

Explicit MVP_DEMO_MODE=1: local SQLite with simulated identities (UNSAFE for public use).
Live mode: Supabase publishable key + server-enforced RLS; no service-role secrets.
"""
from contextlib import contextmanager
from datetime import date, timedelta
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from conflicts import normalize_name, validate_event

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / 'data' / 'campus_event_hub_demo.sqlite3'
CLUB_FIELDS = 'id,org_name,category,org_size,description,contact_email,website_url,owner_id,created_at'
EVENT_FIELDS = ('id,club_id,created_by,title,event_date,start_time,end_time,building,room,'
                'category,description,external_url,free_food,status,created_at')
TICKET_FIELDS = ('id,reporter_id,event_ref,club_id,category,description,route,status,created_at,updated_at')


def is_demo():
    return os.getenv('MVP_DEMO_MODE', '0') == '1'


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute('pragma journal_mode=WAL')
    connection.execute('pragma foreign_keys=ON')
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_demo():
    """Idempotent local demo setup, not a substitute for server-side authorization."""
    if not is_demo():
        return
    with connect() as db:
        db.executescript('''
            create table if not exists clubs (
              id text primary key, org_name text not null, club_key text unique not null,
              category text not null, org_size text not null, description text not null,
              contact_email text, website_url text, owner_id text not null,
              created_at text not null default (datetime('now')));
            create table if not exists published_events (
              id text primary key, club_id text not null references clubs(id),
              created_by text not null, title text not null, event_date text not null,
              start_time text not null, end_time text not null, building text not null,
              room text, category text not null, description text not null,
              external_url text, free_food integer not null default 0,
              status text not null default 'published',
              created_at text not null default (datetime('now')));
            create table if not exists tickets (
              id text primary key, reporter_id text not null, event_ref text,
              club_id text references clubs(id), category text not null,
              description text not null, route text not null, status text not null default 'open',
              created_at text not null default (datetime('now')),
              updated_at text not null default (datetime('now')));
        ''')
        # Each portal starts in a separate process. The check-and-seed operation
        # must be atomic: otherwise two simultaneous starts can both observe an
        # empty clubs table and both insert the same unique club_key.
        # BEGIN IMMEDIATE serializes this section without deleting existing data.
        db.execute('BEGIN IMMEDIATE')
        if not db.execute('select 1 from clubs limit 1').fetchone():
            club_id = str(uuid4())
            inserted = db.execute('''insert or ignore into clubs
                (id,org_name,club_key,category,org_size,description,owner_id)
                values (?,?,?,?,?,?,?)''',
                (club_id, 'Triton Demo Makers', 'triton demo makers', 'Technology', 'Medium',
                 'Fictional test organization used for this MVP demonstration.', 'demo-officer'))
            if inserted.rowcount:
                db.execute('''insert into published_events
                   (id,club_id,created_by,title,event_date,start_time,end_time,building,room,category,description,free_food)
                   values (?,?,?,?,?,?,?,?,?,?,?,?)''',
                   (str(uuid4()), club_id, 'demo-officer', 'Campus App Demo Night',
                    (date.today()+timedelta(days=7)).isoformat(), '18:00', '20:00',
                    'Price Center', 'Demo Room A', 'Technology',
                    'Fictional event demonstrating the three-portal workflow.', 0))


class LocalStore:
    def __init__(self):
        init_demo()

    def clubs(self):
        with connect() as db:
            return [dict(x) for x in db.execute('select * from clubs order by org_name').fetchall()]

    def create_club(self, values, user_id):
        name = ' '.join(str(values['org_name']).split())
        if not name or len(name) > 120 or not str(values.get('description','')).strip():
            raise ValueError('Club name and description are required (name max 120 characters).')
        # The workshop's 60 legacy clubs exist in the read-only student dataset.
        from pandas import read_csv
        legacy = read_csv(BASE / 'data' / 'events_clean.csv', usecols=['org_name'])
        if normalize_name(name) in {normalize_name(str(n)) for n in legacy['org_name'].unique()}:
            raise ValueError('That club already exists in the workshop dataset. The demo cannot claim its ownership.')
        club_id = str(uuid4())
        try:
            with connect() as db:
                db.execute('''insert into clubs (id,org_name,club_key,category,org_size,description,contact_email,website_url,owner_id)
                              values (?,?,?,?,?,?,?,?,?)''',
                           (club_id, name, normalize_name(name), values['category'], values['org_size'],
                            values['description'].strip(), values.get('contact_email') or None,
                            values.get('website_url') or None, user_id))
        except sqlite3.IntegrityError as e:
            raise ValueError('That club name is already registered.') from e
        return club_id

    def events(self, include_cancelled=False):
        with connect() as db:
            where = '' if include_cancelled else " where e.status='published'"
            return [dict(x) for x in db.execute('select e.*, c.org_name,c.org_size from published_events e join clubs c on c.id=e.club_id'+where+' order by e.event_date,e.start_time').fetchall()]

    def create_event(self, values, user_id):
        validate_event(values)
        with connect() as db:
            club = db.execute('select owner_id from clubs where id=?', (values['club_id'],)).fetchone()
            if not club or club['owner_id'] != user_id:
                raise PermissionError('You can publish only for a club you own.')
            event_id = str(uuid4())
            db.execute('''insert into published_events
                (id,club_id,created_by,title,event_date,start_time,end_time,building,room,category,description,external_url,free_food)
                values (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (event_id,values['club_id'],user_id,values['title'],str(values['event_date']),
                 str(values['start_time'])[:5],str(values['end_time'])[:5],values['building'],
                 values.get('room') or '',values['category'],values['description'],
                 values.get('external_url') or '',int(bool(values.get('free_food')))))
            return event_id

    def update_event(self, event_id, values, user_id):
        validate_event(values)
        with connect() as db:
            owned = db.execute('select club_id from published_events where id=? and created_by=?', (event_id,user_id)).fetchone()
            if not owned:
                raise PermissionError('You cannot edit this event.')
            db.execute('''update published_events set title=?, event_date=?,start_time=?,end_time=?,building=?,room=?,
                category=?,description=?,external_url=?,free_food=? where id=?''',
                (values['title'],str(values['event_date']),str(values['start_time'])[:5],str(values['end_time'])[:5],
                 values['building'],values.get('room') or '',values['category'],values['description'],
                 values.get('external_url') or '',int(bool(values.get('free_food'))),event_id))

    def cancel_event(self, event_id, user_id):
        with connect() as db:
            cur = db.execute("update published_events set status='cancelled' where id=? and created_by=?", (event_id,user_id))
            if not cur.rowcount:
                raise PermissionError('Cannot cancel another club’s event.')

    def tickets(self, user_id=None, admin=False):
        with connect() as db:
            if admin:
                rows = db.execute('select * from tickets order by created_at desc').fetchall()
            else:
                rows = db.execute('''select distinct t.* from tickets t
                  left join clubs c on c.id=t.club_id
                  where t.reporter_id=? or c.owner_id=? order by t.created_at desc''',(user_id,user_id)).fetchall()
            return [dict(x) for x in rows]

    def create_ticket(self, values, user_id):
        desc = str(values.get('description') or '').strip()
        if len(desc) < 10 or len(desc) > 2000:
            raise ValueError('Describe the issue in 10–2000 characters.')
        cat = values['category']; club_id = values.get('club_id') or None
        if cat not in ('event_info','website_bug','account','other'):
            raise ValueError('Invalid ticket category.')
        with connect() as db:
            if club_id and not db.execute('select 1 from clubs where id=?',(club_id,)).fetchone():
                raise ValueError('Unknown club.')
            route = 'club' if cat=='event_info' and club_id else ('developer' if cat=='website_bug' else 'client')
            ticket_id = str(uuid4())
            db.execute('''insert into tickets (id,reporter_id,event_ref,club_id,category,description,route)
                        values (?,?,?,?,?,?,?)''',
                       (ticket_id,user_id,values.get('event_ref') or None,club_id,cat,desc,route))
            return ticket_id

    def update_ticket(self, ticket_id, status, user_id, is_admin=False):
        if status not in ('open','in_progress','resolved'):
            raise ValueError('Invalid ticket status.')
        with connect() as db:
            row = db.execute('''select t.route,c.owner_id from tickets t
                                left join clubs c on c.id=t.club_id where t.id=?''', (ticket_id,)).fetchone()
            if not row or (not is_admin and not (row['route']=='club' and row['owner_id']==user_id)):
                raise PermissionError('You do not have permission to resolve this ticket.')
            db.execute("update tickets set status=?, updated_at=datetime('now') where id=?",(status,ticket_id))

    def is_admin(self, user_id):
        return user_id == 'demo-client'


class SupabaseStore:
    """Production-facing thin client; Supabase RLS is the source of authorization."""
    def __init__(self, client):
        self.client = client

    def clubs(self):
        return self.client.table('hub_clubs').select(CLUB_FIELDS).order('org_name').execute().data or []

    def create_club(self, values, user_id):
        name = ' '.join(values['org_name'].split())
        if not name or len(name)>120 or not values.get('description','').strip():
            raise ValueError('Club name and description required (name max 120 characters).')
        payload = {k: values.get(k) for k in ('category','org_size','description','contact_email','website_url')}
        payload.update({'org_name':name,'owner_id':user_id})
        result = self.client.table('hub_clubs').insert(payload).execute().data
        return result[0]['id']

    def events(self, include_cancelled=False):
        query = self.client.table('hub_events').select(EVENT_FIELDS+',hub_clubs(org_name,org_size)')
        if not include_cancelled:
            query=query.eq('status','published')
        rows=query.order('event_date').execute().data or []
        for row in rows:
            info=row.pop('hub_clubs',None) or {}
            row['org_name']=info.get('org_name','')
            row['org_size']=info.get('org_size','')
        return rows

    def create_event(self, values, user_id):
        validate_event(values)
        payload={k: values.get(k) for k in ('club_id','title','event_date','start_time','end_time','building','room','category','description','external_url','free_food')}
        payload['created_by']=user_id
        result=self.client.table('hub_events').insert(payload).execute().data
        return result[0]['id']

    def update_event(self, event_id, values, user_id):
        validate_event(values)
        payload={k: values.get(k) for k in ('title','event_date','start_time','end_time','building','room','category','description','external_url','free_food')}
        self.client.table('hub_events').update(payload).eq('id',event_id).eq('created_by',user_id).execute()

    def cancel_event(self,event_id,user_id):
        self.client.table('hub_events').update({'status':'cancelled'}).eq('id',event_id).eq('created_by',user_id).execute()

    def tickets(self,user_id=None,admin=False):
        # RLS enforces reporter, club owner, or client admin visibility.
        return self.client.table('hub_tickets').select(TICKET_FIELDS).order('created_at',desc=True).execute().data or []

    def create_ticket(self,values,user_id):
        desc=str(values.get('description') or '').strip()
        if not 10<=len(desc)<=2000:
            raise ValueError('Describe the issue in 10–2000 characters.')
        payload={k:values.get(k) for k in ('event_ref','club_id','category')}
        payload.update({'reporter_id':user_id,'description':desc})
        # Route is derived on the database server, not trusted from user input.
        result=self.client.table('hub_tickets').insert(payload).execute().data
        return result[0]['id']

    def update_ticket(self,ticket_id,status,user_id,is_admin=False):
        if status not in ('open','in_progress','resolved'):
            raise ValueError('Invalid status.')
        self.client.table('hub_tickets').update({'status':status}).eq('id',ticket_id).execute()

    def is_admin(self,user_id):
        return bool(self.client.table('hub_admins').select('user_id').eq('user_id',user_id).limit(1).execute().data)


def get_store():
    """Get backend for a Streamlit browser session. No privileged key is used."""
    if is_demo():
        return LocalStore()
    import streamlit as st
    url=os.getenv('SUPABASE_URL',''); key=os.getenv('SUPABASE_ANON_KEY','')
    if not (url and key):
        try:
            url=url or st.secrets.get('SUPABASE_URL','')
            key=key or st.secrets.get('SUPABASE_ANON_KEY','')
        except Exception:
            pass
    if not (url.startswith('https://') and key):
        return None
    if '_supabase_client' not in st.session_state:
        from account_store import new_client
        st.session_state['_supabase_client']=new_client(url,key)
    return SupabaseStore(st.session_state['_supabase_client'])
