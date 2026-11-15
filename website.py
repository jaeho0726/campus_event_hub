"""Campus Event Hub — student-facing Streamlit MVP.

Run: streamlit run app.py
"""
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
import pandas as pd
import streamlit as st
from event_utils import load_events, filter_events, build_club_summary

BASE = Path(__file__).resolve().parent
st.set_page_config(page_title='Campus Event Hub', page_icon='📅', layout='wide')

st.markdown('''
<style>
.block-container {max-width: 1160px; padding-top: 1.4rem; padding-bottom: 2.5rem;}
.hero {background: linear-gradient(110deg,#112d4e,#225b82); padding: 1.9rem 2rem;
       border-radius: 18px; color: white; margin-bottom: 1.2rem;}
.hero h1 {color:white; font-size:2.1rem; line-height:1.25; margin:0 0 .45rem;}
.hero p {color:#e3eef9; font-size:1.01rem; margin:0;}
div[data-testid='stVerticalBlockBorderWrapper'] {border-radius:14px;}
.club-highlight {background: rgba(51,77,117,.22); border: 1px solid rgba(122,152,201,.25);
                 padding: 1rem 1.1rem; border-radius: 16px; margin: .4rem 0 1rem;}
.club-name {font-size: 1.35rem; font-weight: 700; margin-bottom: .35rem;}
.club-meta {color: #d6dff1; margin: 0;}
.small-note {color: #9aa5b1; font-size: .92rem;}
</style>
''', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def get_events():
    return load_events(BASE / 'data' / 'events_clean.csv')


@st.cache_data(show_spinner=False)
def get_club_summary(events_df: pd.DataFrame):
    return build_club_summary(events_df)


def usable_source_url(url):
    """Return a valid HTTP(S) announcement URL, or an empty string."""
    if not isinstance(url, str):
        return ''
    clean_url = url.strip()
    parts = urlsplit(clean_url)
    if parts.scheme in ('http', 'https') and parts.netloc:
        return clean_url
    return ''


def source_icon(url: str, event_id: str, namespace: str):
    """Render a small link icon in the event card's top-right corner."""
    valid_url = usable_source_url(url)
    if valid_url:
        st.link_button('🔗', valid_url, help='Open original event announcement')
    else:
        st.button('🔗', key=f'missing_link_{namespace}_{event_id}',
                  disabled=True, help='Link not provided')


def event_card(event: pd.Series, namespace: str):
    """Draw event information and a session-only Save/Unsave control."""
    event_id = event['event_id']
    with st.container(border=True):
        size_text = str(event.get('org_size', '')).title()
        kicker = f"{event['category']}"
        if size_text:
            kicker += f" · {size_text} club"
        category_col, link_col = st.columns([8, 1], vertical_alignment='center')
        with category_col:
            st.caption(kicker)
        with link_col:
            source_icon(event.get('external_url', ''), event_id, namespace)
        st.markdown(f"#### {event['title']}")
        st.write(f"**{event['org_name']}**")
        st.write(f"📅 {event['event_date'].strftime('%a, %b %d, %Y')} · 🕒 {event['start_time']}")
        st.write(f"📍 {event['location']}")
        save_col, details_col = st.columns(2)
        is_saved = event_id in st.session_state.saved_events
        if save_col.button('✓ Saved' if is_saved else '☆ Save event',
                           key=f"save_{namespace}_{event_id}", use_container_width=True):
            if is_saved:
                st.session_state.saved_events.remove(event_id)
            else:
                st.session_state.saved_events.add(event_id)
            st.rerun()
        with details_col.popover('Event details', use_container_width=True):
            st.markdown(f"**Host:** {event['org_name']}")
            st.markdown(f"**Category:** {event['category']}")
            st.markdown(f"**Where:** {event['location']}")
            st.markdown(f"**When:** {event['event_date'].strftime('%B %d, %Y')} at {event['start_time']}")
            st.markdown(f"**Listed on:** {event['platforms']}")
            if event.get('free_food', False):
                st.write('🍕 Food mentioned in listing')
            if event.get('time_conflict', False):
                st.warning('Multiple listings disagreed about the time. Verify with the organizer.')
            if not usable_source_url(event.get('external_url', '')):
                st.caption('Link not provided for this event.')


def show_pagination(total_pages: int, key: str):
    page_key = f'{key}_page'
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    st.session_state[page_key] = min(max(st.session_state[page_key], 1), total_pages)

    prev_col, page_col, next_col = st.columns([1, 3, 1])
    with prev_col:
        if st.button('‹ Previous', key=f'{key}_prev', disabled=st.session_state[page_key] <= 1,
                     use_container_width=True):
            st.session_state[page_key] -= 1
            st.rerun()
    with page_col:
        st.markdown(
            f"<div style='text-align:center; padding-top:.45rem;'><strong>Page {st.session_state[page_key]} of {total_pages}</strong></div>",
            unsafe_allow_html=True
        )
    with next_col:
        if st.button('Next ›', key=f'{key}_next', disabled=st.session_state[page_key] >= total_pages,
                     use_container_width=True):
            st.session_state[page_key] += 1
            st.rerun()
    return st.session_state[page_key]



def show_cards(df: pd.DataFrame, key: str, page_size: int = 12):
    if df.empty:
        st.info('No events match. Try changing your search or filters.')
        return
    total_pages = (len(df) + page_size - 1) // page_size
    page = st.session_state.get(f'{key}_page', 1)
    if page > total_pages:
        st.session_state[f'{key}_page'] = total_pages
        page = total_pages
    visible = df.iloc[(page - 1) * page_size:page * page_size]
    for start in range(0, len(visible), 2):
        cols = st.columns(2)
        for col, (_, event) in zip(cols, visible.iloc[start:start + 2].iterrows()):
            with col:
                event_card(event, key)
    st.markdown('')
    show_pagination(total_pages, key)



events = get_events()
club_summary = get_club_summary(events)
if 'saved_events' not in st.session_state:
    st.session_state.saved_events = set()

st.markdown('''<div class="hero">
<h1>Discover what’s happening on campus.</h1>
<p>One place to explore student organizations, browse events, and find your community at UC San Diego.</p>
</div>''', unsafe_allow_html=True)

browse, clubs, saved = st.tabs(['🔎 Explore events', '🏛️ Explore clubs', '☆ Saved events'])

with browse:
    st.subheader('Find your next event')
    search_col, category_col = st.columns([2, 1])
    keyword = search_col.text_input('Search events, clubs, or locations',
                                    placeholder='Try Python, workshop, Geisel Library')
    category_list = sorted(events['category'].unique().tolist())
    categories = category_col.multiselect('Event category', category_list)
    with st.expander('More filters'):
        show_upcoming = st.checkbox('Upcoming only', value=True,
                                   help='Show events happening today or later.')
        start = st.date_input('From date', value=None, key='date_from')
        end = st.date_input('Through date', value=None, key='date_to')
        if start and end and start > end:
            st.error('The start date must be on or before the end date.')
            st.stop()
    earliest = max(date.today(), start) if show_upcoming and start else (date.today() if show_upcoming else start)
    matches = filter_events(events, keyword, categories, earliest, end)
    st.write(f'**{len(matches)} events found**')
    if not matches.empty:
        st.caption('Events are sorted by date. Save events to keep a short list during this session.')
    show_cards(matches, 'browse')

with clubs:
    st.subheader('Explore student organizations')
    st.write('Search for a club, choose one, and browse its upcoming or listed events.')
    club_search = st.text_input('Search for a club', placeholder='Try App Makers, Picnic Society, Chess Club')
    filtered_clubs = club_summary
    if club_search.strip():
        mask = filtered_clubs['org_name'].str.contains(club_search.strip(), case=False, regex=False)
        filtered_clubs = filtered_clubs.loc[mask].copy()
    st.write(f'**{len(filtered_clubs)} clubs found**')

    if filtered_clubs.empty:
        st.info('No matching clubs.')
    else:
        selected_club = st.selectbox('Choose a club', filtered_clubs['org_name'].tolist())
        club_row = filtered_clubs[filtered_clubs['org_name'] == selected_club].iloc[0]
        club_events = filter_events(events, club=selected_club)

        st.markdown(
            f"""
            <div class='club-highlight'>
                <div class='club-name'>{selected_club}</div>
                <p class='club-meta'><strong>Club size:</strong> {str(club_row['org_size']).title() or 'Not specified'} &nbsp; | &nbsp;
                <strong>Categories:</strong> {club_row['categories']} &nbsp; | &nbsp;
                <strong>Events listed:</strong> {club_row['event_count']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        metric1, metric2, metric3 = st.columns(3)
        metric1.metric('Events listed', int(club_row['event_count']))
        next_event_text = club_row['next_event'].strftime('%b %d, %Y') if pd.notna(club_row['next_event']) else 'N/A'
        metric2.metric('Next listed date', next_event_text)
        metric3.metric('Primary size', str(club_row['org_size']).title() or 'N/A')
        st.markdown(f"##### Events from {selected_club}")
        show_cards(club_events, 'clubs')

with saved:
    st.subheader('Your saved events')
    st.caption('Saved events are kept only in this browser session. Accounts and emailed reminders are planned for a later phase.')
    saved_events = events[events['event_id'].isin(st.session_state.saved_events)]
    st.write(f'**{len(saved_events)} saved events**')
    if saved_events.empty:
        st.info('Browse events and select ☆ Save event to build your list.')
    else:
        show_cards(saved_events, 'saved')
        if st.button('Clear saved events'):
            st.session_state.saved_events.clear()
            st.rerun()
