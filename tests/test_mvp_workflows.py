"""Local integration tests for three-portal demo data; no network or SMTP."""
from datetime import date, timedelta
import pytest

import mvp_store
from conflicts import conflict_warnings, overlap_minutes, normalize_name


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv('MVP_DEMO_MODE', '1')
    monkeypatch.setattr(mvp_store,'DB_PATH',tmp_path/'test.sqlite3')
    return mvp_store.LocalStore()


def future_event(club_id, day=None, start='18:00', end='20:00', room='Room 5'):
    return {'club_id':club_id,'title':'Demo Planning Workshop',
      'event_date':(day or (date.today()+timedelta(days=7))).isoformat(),
      'start_time':start,'end_time':end,'building':'Geisel Library','room':room,
      'category':'Tech','description':'A test workshop for demo users.',
      'external_url':'https://example.edu/test','free_food':False}


def test_overlaps_and_normalization():
    assert overlap_minutes('18:00','20:00','17:00','19:00')==60
    assert overlap_minutes('18:00','20:00','20:00','21:00')==0
    assert normalize_name('  AI  BUILDERS ')== 'ai builders'


def test_club_registration_prevents_legacy_and_duplicates(store):
    assert any(c['org_name']=='Triton Demo Makers' for c in store.clubs())
    with pytest.raises(ValueError,match='workshop dataset'):
        store.create_club({'org_name':'AI  Builders','category':'Technology',
            'org_size':'Small','description':'Legacy'},'demo-student')
    club=store.create_club({'org_name':' New  Study Society ', 'category':'Academic',
             'org_size':'Small','description':'A test group.'},'demo-student')
    assert club
    with pytest.raises(ValueError,match='already registered'):
        store.create_club({'org_name':'new study society','category':'Academic',
            'org_size':'Medium','description':'Repeated name.'},'demo-student')


def test_event_visibility_and_ownership(store):
    owner=store.clubs()[0]['owner_id']
    club=store.clubs()[0]['id']
    event=future_event(club)
    event_id=store.create_event(event,owner)
    assert any(e['id']==event_id for e in store.events())
    with pytest.raises(PermissionError):
        store.create_event(event,'demo-student')
    with pytest.raises(PermissionError):
        store.cancel_event(event_id,'demo-student')
    new=dict(event,title='Updated Workshop')
    store.update_event(event_id,new,owner)
    assert next(e for e in store.events() if e['id']==event_id)['title']=='Updated Workshop'
    store.cancel_event(event_id,owner)
    assert all(e['id']!=event_id for e in store.events())
    assert any(e['id']==event_id for e in store.events(include_cancelled=True))


def test_nonblocking_warnings(store):
    seed=store.clubs()[0]
    ev=future_event(seed['id'],start='17:00',end='19:00',room='Demo Room A')
    ev['building']='Price Center'
    ev['event_date']=(date.today()+timedelta(days=7)).isoformat()
    conflicts=conflict_warnings(ev,store.events())
    assert any(c['severity']=='same_room' and c['minutes']==60 for c in conflicts)
    ev['room']='Other Room'
    assert conflict_warnings(ev,store.events())[0]['severity']=='same_building'
    ev['building']='Geisel Library'
    assert conflict_warnings(ev,store.events())[0]['severity']=='same_time'
    # Informational warning never blocks a valid event insert in store.
    ev['event_date']=(date.today()+timedelta(days=7)).isoformat()
    assert store.create_event(ev,seed['owner_id'])


def test_ticket_routes_visibility_and_resolution(store):
    club=store.clubs()[0]
    content=store.create_ticket({'category':'event_info','club_id':club['id'],
        'description':'The published location seems wrong.'}, 'demo-student')
    bug=store.create_ticket({'category':'website_bug',
        'description':'The calendar does not show the right page.'}, 'demo-student')
    assert {t['id'] for t in store.tickets(user_id='demo-student')}=={content,bug}
    club_tickets=store.tickets(user_id=club['owner_id'])
    assert content in {t['id'] for t in club_tickets}
    assert bug not in {t['id'] for t in club_tickets}
    assert len(store.tickets(user_id='demo-client',admin=True))==2
    with pytest.raises(PermissionError):
        store.update_ticket(content,'resolved','demo-student')
    store.update_ticket(content,'resolved',club['owner_id'])
    store.update_ticket(bug,'in_progress','demo-client',is_admin=True)
    statuses={t['id']:t['status'] for t in store.tickets(user_id='demo-client',admin=True)}
    assert statuses[content]=='resolved'
    assert statuses[bug]=='in_progress'
