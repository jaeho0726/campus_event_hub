"""Campus Event Hub — read-only event monitoring + support ticket dashboard."""
from datetime import datetime
import pandas as pd
import streamlit as st
from streamlit_calendar import calendar
from calendar_theme import UCSD_CALENDAR_CSS

from conflicts import conflict_warnings
from mvp_store import get_store, is_demo
from portal_ui import identity, show_tickets, style_portal

st.set_page_config(page_title='Client Admin | Campus Event Hub',layout='wide')
style_portal()
st.title('Client Admin Portal')
st.caption('Monitor published events and handle exceptional support cases. This portal does not approve, reschedule, or edit club events.')
store=get_store()
user=identity(store,'client')
try:
    authorized=store.is_admin(user['id'])
except Exception as exc:
    st.error(f'Administrator access could not be checked: {exc}')
    st.stop()
if not authorized:
    st.error('Your account does not have Client Admin access.')
    st.stop()

try:
    live_events=store.events()
    tickets=store.tickets(user_id=user['id'],admin=True)
except Exception as exc:
    st.error(f'Could not load shared data. Check database/mvp_portals.sql: {exc}')
    st.stop()

legacy=pd.read_csv('data/events_clean.csv')
legacy['event_date']=pd.to_datetime(legacy['event_date'],errors='coerce').dt.strftime('%Y-%m-%d')


def all_calendar_records():
    all_rows=[]
    for _,e in legacy.iterrows():
        try:
            start=datetime.strptime(str(e['start_time']),'%I:%M %p').strftime('%H:%M')
        except ValueError:
            continue
        all_rows.append({'title':str(e['title']),'club':str(e['org_name']),'date':str(e['event_date']),
                         'start':start,'end':'Unknown', 'location':str(e['location']),
                         'category':str(e['category']),'source':'Workshop demo CSV'})
    for e in live_events:
        location=str(e.get('building') or '')
        if e.get('room'):
            location+=' · '+str(e['room'])
        all_rows.append({'title':e['title'],'club':e.get('org_name') or '',
                         'date':str(e['event_date'])[:10],'start':str(e['start_time'])[:5],
                         'end':str(e['end_time'])[:5], 'location':location,
                         'category':e['category'],'source':'Club submission'})
    return pd.DataFrame(all_rows)


def calendar_page():
    st.subheader('All Events Calendar')
    st.caption('Workshop records have no end time; their calendar slots show start times only. Club submissions include full start/end times.')
    records=all_calendar_records()
    clubs=sorted(records['club'].dropna().astype(str).unique())
    venues=sorted(records['location'].dropna().astype(str).unique())
    a,b,c=st.columns(3)
    selected_club=a.selectbox('Club',['All']+clubs)
    selected_venue=b.selectbox('Location',['All']+venues)
    selected_source=c.selectbox('Listing source',['All','Workshop demo CSV','Club submission'])
    filtered=records.copy()
    if selected_club!='All':
        filtered=filtered[filtered.club==selected_club]
    if selected_venue!='All':
        filtered=filtered[filtered.location==selected_venue]
    if selected_source!='All':
        filtered=filtered[filtered.source==selected_source]
    entries=[]
    for _,e in filtered.iterrows():
        start=f"{e['date']}T{e['start']}:00"
        submitted=e['source']=='Club submission'
        entry={'title':e['title'],'start':start,'allDay':False,
               'backgroundColor':'#182B49' if submitted else '#EAF3FA',
               'borderColor':'#182B49' if submitted else '#00629B',
               'textColor':'#FFFFFF' if submitted else '#182B49',
               'classNames':['hub-event--submitted' if submitted else 'hub-event--legacy'],
               'extendedProps':{'club':e['club'],'location':e['location'],'source':e['source']}}
        if e['end']!='Unknown':
            entry['end']=f"{e['date']}T{e['end']}:00"
        entries.append(entry)
    options={
      'initialView':'timeGridWeek',
      'themeSystem':'standard',
      'headerToolbar':{'left':'prev,next today','center':'title','right':'dayGridMonth,timeGridWeek,timeGridDay,listWeek'},
      'height':620,
      'slotMinTime':'08:00:00','slotMaxTime':'23:00:00',
      'nowIndicator':True,
      # Avoid cramming many synthetic workshop events into nearly invisible
      # overlapping slivers; FullCalendar shows a +more link for excess.
      'slotEventOverlap':False,
      'eventMaxStack':3,
      'moreLinkClick':'popover',
      'eventMinHeight':24,
    }
    calendar(events=entries,options=options,custom_css=UCSD_CALENDAR_CSS,key='admin_calendar')
    st.caption('Navy with yellow accent: club-submitted events. Pale blue with blue outline: synthetic workshop events. Crowded times show +more; use the table below for full locations. Listings are not room reservations.')
    st.markdown('#### Event details, including locations')
    st.dataframe(filtered.sort_values(['date','start']),hide_index=True,use_container_width=True,
                 column_order=['date','start','end','club','title','location','source'])


def monitor_conflicts():
    st.subheader('Potential location overlaps')
    st.caption('Only newly submitted events have reliable end times. These checks do not verify real university reservations.')
    pairs=[]
    for i,event in enumerate(live_events):
        potential=conflict_warnings(event,live_events[i+1:])
        for item in potential:
            if item['severity'] != 'same_time':
                pairs.append({'event_a':event['title'],'club_a':event['org_name'],
                              'event_b':item['event']['title'],'club_b':item['event']['org_name'],
                              'date':event['event_date'],'building':event['building'],
                              'severity':item['severity'],'overlap_minutes':item['minutes']})
    if not pairs:
        st.success('No same-building or same-room overlaps among published club submissions.')
    else:
        st.warning(f'{len(pairs)} potential location overlap(s) among submitted events.')
        st.dataframe(pd.DataFrame(pairs),use_container_width=True,hide_index=True)
    st.caption('No approval or cancellation controls are provided to client admins.')


def support_page():
    st.subheader('Ticket Management')
    st.caption('Content issues go to the responsible club where possible. Technical issues are identified for developer follow-up; no automatic code repair is claimed.')
    unresolved=sum(t['status']!='resolved' for t in tickets)
    a,b,c=st.columns(3)
    a.metric('Open / in progress',unresolved)
    b.metric('Routed to clubs',sum(t['route']=='club' and t['status']!='resolved' for t in tickets))
    c.metric('Technical issues',sum(t['route']=='developer' and t['status']!='resolved' for t in tickets))
    show_tickets(store,user,admin=True)


cal_tab,tickets_tab,conflicts_tab=st.tabs(['All-events calendar','Tickets','Conflict monitoring'])
with cal_tab:
    calendar_page()
with tickets_tab:
    support_page()
with conflicts_tab:
    monitor_conflicts()
