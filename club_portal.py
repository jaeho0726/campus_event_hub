"""Campus Event Hub — club-admin self-service MVP."""
from datetime import date, time
import pandas as pd
import streamlit as st

from conflicts import conflict_warnings, normalize_name, validate_event
from mvp_store import get_store
from portal_ui import (CATEGORY_OPTIONS, CLUB_CATEGORIES, identity,
                       show_tickets, style_portal, submit_ticket_form)

st.set_page_config(page_title='Club Admin | Campus Event Hub',layout='wide')
style_portal()
st.title('Club Admin Portal')
st.caption('Self-service club registration, event publishing, and issue resolution. Not a UCSD booking system.')
store=get_store()
user=identity(store,'club')


def register_club():
    st.subheader('Register a new club')
    st.caption('Only new names can register. Existing workshop clubs cannot be claimed in this MVP.')
    name=st.text_input('Club name',placeholder='Enter your club name',key='new_club_name')
    if st.button('Check name availability'):
        if not name.strip():
            st.error('Enter a club name.')
        else:
            legacy=pd.read_csv('data/events_clean.csv',usecols=['org_name'])
            used={normalize_name(str(n)) for n in legacy['org_name'].unique()}
            used.update(normalize_name(c['org_name']) for c in store.clubs())
            if normalize_name(name) in used:
                st.error('This club name is already in use. Existing clubs cannot be claimed automatically.')
                st.session_state.pop('available_club_name',None)
            else:
                st.session_state.available_club_name=' '.join(name.split())
    if st.session_state.get('available_club_name') == ' '.join(name.split()) and name.strip():
        st.success('Name available. Complete the club profile below.')
        with st.form('new_club_form'):
            category=st.selectbox('Club category',CLUB_CATEGORIES)
            size=st.selectbox('Club size',['Small','Medium','Large'])
            description=st.text_area('Club description',max_chars=2000)
            contact=st.text_input('Public club contact email (optional)')
            website=st.text_input('Website or social media link (optional)')
            if st.form_submit_button('Create club'):
                try:
                    club_id=store.create_club({'org_name':name,'category':category,'org_size':size,
                      'description':description,'contact_email':contact,'website_url':website},user['id'])
                    st.session_state.pop('available_club_name',None)
                    st.success(f'Club created ({str(club_id)[:8]}). You can now publish events.')
                    st.rerun()
                except Exception as exc:
                    st.error(f'Could not create club: {exc}')


def event_fields(form_key, default=None):
    e=default or {}
    event_date=e.get('event_date') or date.today()
    if isinstance(event_date,str):
        event_date=date.fromisoformat(event_date[:10])
    start=str(e.get('start_time') or '18:00')[:5]
    end=str(e.get('end_time') or '19:00')[:5]
    try:
        start_time=time.fromisoformat(start)
        end_time=time.fromisoformat(end)
    except ValueError:
        start_time,end_time=time(18),time(19)
    title=st.text_input('Event title',value=e.get('title',''),key=f'{form_key}_title')
    day=st.date_input('Event date',value=event_date,key=f'{form_key}_day')
    left,right=st.columns(2)
    with left:
        start=st.time_input('Start time (Pacific)',start_time,key=f'{form_key}_start')
    with right:
        end=st.time_input('End time (Pacific)',end_time,key=f'{form_key}_end')
    a,b=st.columns(2)
    with a:
        building=st.text_input('Building or venue',value=e.get('building',''),key=f'{form_key}_building')
    with b:
        room=st.text_input('Room / specific location (if applicable)',value=e.get('room') or '',key=f'{form_key}_room')
    old_category=e.get('category','Tech')
    index=CATEGORY_OPTIONS.index(old_category) if old_category in CATEGORY_OPTIONS else 0
    category=st.selectbox('Event category',CATEGORY_OPTIONS,index=index,key=f'{form_key}_cat')
    description=st.text_area('Description',value=e.get('description',''),max_chars=2000,key=f'{form_key}_desc')
    url=st.text_input('Announcement URL (optional)',value=e.get('external_url') or '',key=f'{form_key}_url')
    food=st.checkbox('Free food',value=bool(e.get('free_food',False)),key=f'{form_key}_food')
    return {'title':title,'event_date':day.isoformat(),'start_time':start.strftime('%H:%M'),
      'end_time':end.strftime('%H:%M'),'building':building.strip(),'room':room.strip(),
      'category':category,'description':description.strip(),'external_url':url.strip(),'free_food':food}


def warnings_panel(warnings):
    if not warnings:
        return
    st.warning(f'{len(warnings)} event(s) overlap in time. These are possible conflicts, not confirmed reservations.')
    for w in warnings[:8]:
        ev=w['event']
        severity={'same_room':'Same specific room','same_building':'Same building','same_time':'Same time (different location)'}[w['severity']]
        st.write(f"**{severity}** · {ev['title']} — {ev['org_name']} · "
                 f"{str(ev['start_time'])[:5]}–{str(ev['end_time'])[:5]} · "
                 f"{ev['building']} {ev.get('room') or ''} ({w['minutes']} min overlap)")
    st.caption('Check official venue availability independently. You may still publish if the information is correct.')


def publish_panel(clubs):
    st.subheader('Publish an event')
    owned=[c for c in clubs if c['owner_id']==user['id']]
    if not owned:
        st.info('You have no club yet. Use the Register Club tab first.')
        return
    selected=st.selectbox('Publish for club',owned,format_func=lambda c:c['org_name'])
    with st.form('create_event_form'):
        values=event_fields('create')
        check=st.form_submit_button('Check details and publish')
    if check:
        values['club_id']=selected['id']
        try:
            validate_event(values)
            overlaps=conflict_warnings(values,store.events())
            if overlaps:
                st.session_state.pending_event=values
                st.session_state.pending_conflicts=overlaps
            else:
                event_id=store.create_event(values,user['id'])
                st.session_state.pop('pending_event',None)
                st.success(f'Published immediately. Event ID: {str(event_id)[:8]}')
                st.rerun()
        except Exception as exc:
            st.error(f'Event not published: {exc}')
    pending=st.session_state.get('pending_event')
    if pending:
        if pending.get('club_id')!=selected['id']:
            st.session_state.pop('pending_event',None)
            st.rerun()
        st.markdown('#### Confirm overlapping event')
        warnings_panel(st.session_state.get('pending_conflicts',[]))
        st.caption('If you edited the form, click “Check details and publish” again before confirming.')
        a,b=st.columns(2)
        if a.button('Return to editing'):
            st.session_state.pop('pending_event',None)
            st.rerun()
        if b.button('I checked — publish anyway',type='primary'):
            try:
                event_id=store.create_event(pending,user['id'])
                st.session_state.pop('pending_event',None)
                st.session_state.pop('pending_conflicts',None)
                st.success(f'Published. Event ID: {str(event_id)[:8]}')
                st.rerun()
            except Exception as exc:
                st.error(f'Could not publish: {exc}')


def manage_events():
    st.subheader('My events')
    my_events=[e for e in store.events(include_cancelled=True) if e['created_by']==user['id']]
    if not my_events:
        st.info('No events created yet.')
    for ev in my_events:
        with st.expander(f"{ev['title']} · {ev['event_date']} · {ev['status']}"):
            st.caption(f"{ev['org_name']} | {ev['building']} {ev.get('room') or ''}")
            if ev['status']=='cancelled':
                st.info('This event is canceled and hidden from the student feed.')
                continue
            with st.form('edit_'+str(ev['id'])):
                values=event_fields('edit_'+str(ev['id']),ev)
                submit=st.form_submit_button('Check and save changes')
            if submit:
                values['club_id']=ev['club_id']
                try:
                    validate_event(values)
                    warnings=conflict_warnings(values,store.events(),exclude_id=ev['id'])
                    if warnings:
                        st.session_state['pending_edit_'+str(ev['id'])]=values
                    else:
                        store.update_event(ev['id'],values,user['id'])
                        st.success('Event updated.')
                        st.rerun()
                except Exception as exc:
                    st.error(str(exc))
            pending=st.session_state.get('pending_edit_'+str(ev['id']))
            if pending:
                warnings_panel(conflict_warnings(pending,store.events(),exclude_id=ev['id']))
                if st.button('Confirm update despite warning',key='confirm_edit_'+str(ev['id'])):
                    try:
                        store.update_event(ev['id'],pending,user['id'])
                        st.session_state.pop('pending_edit_'+str(ev['id']),None)
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
            if st.button('Cancel this event',key='cancel_'+str(ev['id'])):
                try:
                    store.cancel_event(ev['id'],user['id'])
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


try:
    clubs=store.clubs()
except Exception as exc:
    st.error(f'Could not load clubs. Run the MVP database migration. Details: {exc}')
    st.stop()

my_clubs=[c for c in clubs if c['owner_id']==user['id']]
col1,col2=st.columns(2)
col1.metric('Clubs I manage',len(my_clubs))
col2.metric('My published events',len([e for e in store.events() if e['created_by']==user['id']]))
registration,publish,manage,tickets=st.tabs(['Register club','Publish event','My events','Support tickets'])
with registration:
    register_club()
with publish:
    publish_panel(clubs)
with manage:
    manage_events()
with tickets:
    st.subheader('My club tickets and support requests')
    st.caption('Event-information tickets for your club arrive here automatically. Other tickets go to client/developer queues.')
    show_tickets(store,user)
    st.divider()
    st.markdown('#### Submit a support ticket')
    submit_ticket_form(store,user['id'],prefix='club_general')
