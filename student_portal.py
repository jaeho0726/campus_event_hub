"""Campus Event Hub v4.1 — UCSD email OTP + My Hub + persistent saved events.

Public event browsing works without external services. Signed-in features require a
Supabase project configured as described in README.md.
"""
from datetime import date
from html import escape as esc
import os
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import streamlit as st
from streamlit_calendar import calendar
from calendar_theme import UCSD_CALENDAR_CSS

from account_store import (
    CLASS_OPTIONS, REMINDER_OPTIONS, add_saved, add_saved_club, format_reminder,
    get_profile, get_verified_user, is_ucsd_email, list_saved, list_saved_clubs, new_client,
    remove_saved, remove_saved_club, save_profile, send_login_code, update_reminder,
    verify_login_code,
)
from event_utils import build_club_summary, filter_clubs, filter_events, load_events
from conflicts import normalize_name
from mvp_store import get_store, is_demo
from portal_ui import submit_ticket_form

BASE = Path(__file__).resolve().parent

# Force the light theme from code, so the site looks right even when the viewer's browser/OS is in
# dark mode and no .streamlit/config.toml is present. Streamlit sends theme settings with every
# script run, so a single rerun at the start of a session lets the very first page load pick it up.
_LIGHT_THEME = {
    'base': 'light', 'primaryColor': '#00629B', 'backgroundColor': '#F7FAFD',
    'secondaryBackgroundColor': '#FFFFFF', 'textColor': '#182B49',
}
for _key, _value in _LIGHT_THEME.items():
    st._config.set_option(f'theme.{_key}', _value)
st.set_page_config(page_title='Campus Event Hub', page_icon='📅', layout='wide')
if not st.session_state.get('_theme_applied'):
    st.session_state['_theme_applied'] = True
    st.rerun()

st.markdown('''
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap');
/* UC San Diego palette supplied in the project brand reference. */
:root {
    --ucsd-navy: #182B49;
    --ucsd-blue: #00629B;
    --ucsd-yellow: #FFCD00;
    --ucsd-gold: #C69214;
}
.block-container {max-width: 1160px; padding-top: 1.4rem; padding-bottom: 2.7rem;}
/* ---------- Warm, simple look ---------- */
:root {
    --cream: #F7FAFD; --ink: #182B49; --muted: #46617A; --line: #D7E4EF;
    --serif: 'Newsreader', Georgia, 'Times New Roman', serif;
}
.stApp, [data-testid='stAppViewContainer'] {background: var(--cream); color: var(--ink);}
[data-testid='stHeader'] {background: transparent;}
h1, h2, h3, h4 {font-family: var(--serif) !important; font-weight: 500 !important; letter-spacing: -.01em; color: var(--ink);}

@keyframes fadeIn {from {opacity: 0; transform: translateY(8px);} to {opacity: 1; transform: none;}}
@keyframes heart {0% {transform: scale(1);} 40% {transform: scale(1.12);} 100% {transform: scale(1);}}

/* Hero: just type on the page */
.hero {padding: 2rem 0 1.5rem; margin-bottom: .8rem; border-bottom: 1px solid var(--line); animation: fadeIn .6s ease-out backwards;}
.hero h1 {font-family: var(--serif) !important; font-weight: 500 !important; font-size: 3rem; line-height: 1.1;
          letter-spacing: -.02em; color: var(--ink); margin: 0 0 .9rem; padding: 0;}
.hero h1::after {content: ''; display: block; width: 44px; height: 4px; border-radius: 2px;
                 background: var(--ucsd-yellow); margin-top: .9rem;}
.hero h2 {font-family: inherit !important; font-weight: 400 !important; font-size: 1.15rem; line-height: 1.55;
          color: var(--muted); max-width: 640px; margin: 0; padding: 0;}
@media (max-width: 640px) {.hero h1 {font-size: 2.3rem;} .hero h2 {font-size: 1.05rem;}}

/* Cards: white, quiet, lift a little on hover */
div[class*='st-key-card_'] {
    background: #fff; border: 1px solid var(--line); border-radius: 20px;
    box-shadow: 0 1px 2px rgba(31, 29, 27, .04);
    transition: transform .2s ease, box-shadow .2s ease;
    animation: fadeIn .35s ease-out backwards;
}
div[class*='st-key-card_']:hover {
    transform: translateY(-2px); box-shadow: 0 8px 20px rgba(31, 29, 27, .08);
}
div[class*='st-key-card_']:has(.saved-marker) {background: #FFF9DF; border-color: var(--ucsd-yellow);}
div[data-testid='stElementContainer']:has(.saved-marker), .element-container:has(.saved-marker) {display: none;}

div[class*='st-key-card_'] {padding: 1.15rem 1.3rem 1.2rem; gap: .35rem;}
div[class*='st-key-card_'] h4 {font-size: 1.5rem; line-height: 1.2; padding: 0; margin: 0;}
div[class*='st-key-card_'] div[data-testid='stMarkdownContainer'] {margin-bottom: 0;}   /* undo Streamlit's built-in -1rem */
div[class*='st-key-card_'] div[data-testid='stHeadingWithActionElements'] {margin-bottom: 0;}
div[class*='st-key-card_'] > :last-child {margin-top: auto;}      /* buttons sit at the bottom */
div[class*='st-key-card_'] > :last-child {padding-top: .9rem;}
/* smaller link icon so the top row stays compact */
div[class*='st-key-card_'] div[data-testid='stColumn']:nth-child(2) div[data-testid='stButton'] button {min-height: 2rem; height: 2rem; padding: 0 .55rem;}
/* cards in the same row stretch to equal height */
div[data-testid='stHorizontalBlock']:has(div[class*='st-key-card_']) {align-items: stretch;}
div[data-testid='stColumn']:has(div[class*='st-key-card_']) > div[data-testid='stVerticalBlock'] {height: 100%;}
div[data-testid='stLayoutWrapper']:has(> div[class*='st-key-card_']) {flex: 1 1 auto;}
div[data-testid='stColumn'] div[class*='st-key-card_'] {flex: 1 1 auto;}
.kicker {font-size: .88rem; color: var(--muted); margin: 0;}
.host {font-weight: 600; font-size: .98rem; padding-top: .2rem; margin: 0 0 .35rem;}
.meta {color: var(--muted); font-size: .95rem; margin: .12rem 0;}
.food {font-size: .88rem; margin-top: .3rem;}

/* Buttons: black outline pills, fill in on hover; saved = filled */
div[data-testid='stButton'] button, div[data-testid='stPopover'] button,
a[data-testid='stBaseLinkButton-secondary'] {
    border-radius: 999px; border: 1px solid var(--ink); background: transparent; color: var(--ink);
    transition: background-color .2s ease, color .2s ease, transform .15s ease;
}
div[data-testid='stButton'] button p, div[data-testid='stPopover'] button p {color: inherit;}
div[data-testid='stButton'] button:not([kind='primary']):hover:not(:disabled),
div[data-testid='stPopover'] button:hover,
a[data-testid='stBaseLinkButton-secondary']:hover {background: var(--ink); color: #fff; border-color: var(--ink);}
div[data-testid='stButton'] button:not([kind='primary']):hover:not(:disabled) p,
div[data-testid='stPopover'] button:hover p {color: #fff;}
div[data-testid='stButton'] button:active:not(:disabled) {transform: scale(.97);}
div[class*='st-key-card_']:has(.saved-marker) > :last-child div[data-testid='stButton'] button {
    background: var(--ucsd-navy); color: #fff; border-color: var(--ucsd-navy); animation: heart .35s ease-out;
}
div[class*='st-key-card_']:has(.saved-marker) > :last-child div[data-testid='stButton'] button p {color: #fff;}

/* The rest */
div[data-testid='stMetric'] {background: #fff; border: 1px solid var(--line); border-radius: 16px;
                             padding: .8rem 1.1rem; width: fit-content; min-width: 9rem;}
div[data-testid='stExpander'] {background: #fff; border-radius: 16px;}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {animation: none !important; transition: none !important;}
}

/* The selected 'Clubs I'm interested in' button is the only primary st.button.
   Streamlit otherwise puts white labels on primary colors; use navy on yellow. */
button[kind='primary'], button[data-testid='stBaseButton-primary'] {
    background-color: var(--ucsd-yellow) !important;
    border-color: var(--ucsd-yellow) !important;
    color: var(--ucsd-navy) !important;
    font-weight: 700 !important;
}
button[kind='primary']:hover, button[data-testid='stBaseButton-primary']:hover {
    background-color: #FFE066 !important;
    border-color: #FFE066 !important;
    color: var(--ucsd-navy) !important;
}
button[kind='primary']:focus-visible,
button[data-testid='stBaseButton-primary']:focus-visible {
    outline: 3px solid var(--ucsd-blue) !important;
    outline-offset: 2px;
}
</style>
''', unsafe_allow_html=True)
@st.cache_data(show_spinner=False)
def get_legacy_events():
    """Workshop dataset is synthetic and read-only."""
    return load_events(BASE / 'data' / 'events_clean.csv')


def get_events():
    """Show baseline CSV events plus new club-admin publications from shared storage."""
    baseline = get_legacy_events()
    store = get_store()
    if store is None:
        return baseline
    try:
        live = store.events()
    except Exception as exc:
        st.warning(f'Live club submissions could not load. Run the MVP database migration. Details: {exc}')
        return baseline
    if not live:
        return baseline
    rows=[]
    for e in live:
        location = str(e.get('building') or '')
        if e.get('room'):
            location += ' · ' + str(e['room'])
        rows.append({
            'event_id':'hub-'+str(e['id']),
            'org_name':e.get('org_name') or '',
            'org_size':str(e.get('org_size') or '').lower(),
            'category':e['category'],
            'title':e['title'],
            'event_date':pd.to_datetime(e['event_date']),
            'start_time':pd.to_datetime(str(e['start_time'])[:5],format='%H:%M').strftime('%I:%M %p').lstrip('0'),
            'end_time':str(e['end_time'])[:5],
            'location':location,
            'platforms':'Campus Event Hub · club-submitted',
            'external_url':e.get('external_url') or '',
            'free_food':bool(e.get('free_food')),
            'time_conflict':False,
        })
    return (pd.concat([baseline,pd.DataFrame(rows)],ignore_index=True)
            .sort_values(['event_date','start_time','title']).reset_index(drop=True))


def get_clubs(event_df):
    """Include registered clubs even if they have not published an event yet."""
    import hashlib
    summary=build_club_summary(event_df)
    store=get_store()
    if store is None:
        return summary
    try:
        registered=store.clubs()
    except Exception:
        return summary
    existing=set(summary['club_id'])
    rows=[]
    for club in registered:
        club_id=hashlib.sha1(normalize_name(club['org_name']).encode('utf-8')).hexdigest()[:16]
        if club_id not in existing:
            rows.append({'club_id':club_id,'org_name':club['org_name'],
                         'org_size':str(club['org_size']).lower(),
                         'categories':club['category'],
                         'category_tags':(club['category'],)})
    if rows:
        summary=pd.concat([summary,pd.DataFrame(rows)],ignore_index=True)
    return summary.sort_values('org_name').reset_index(drop=True)


def get_auth_config() -> tuple[str, str]:
    """Read secrets without failing when the user hasn't set up Supabase yet."""
    url = os.environ.get('SUPABASE_URL', '')
    key = os.environ.get('SUPABASE_ANON_KEY', '')
    if not (url and key):
        try:
            url = url or st.secrets.get('SUPABASE_URL', '')
            key = key or st.secrets.get('SUPABASE_ANON_KEY', '')
        except Exception:
            # st.secrets may be unavailable in a fresh local installation.
            pass
    if not url.startswith('https://') or not key or 'YOUR-PROJECT' in url:
        return '', ''
    return url, key


def session_client():
    """A separate Supabase auth client for EACH Streamlit browser session."""
    url, key = get_auth_config()
    if not (url and key):
        return None
    if '_supabase_client' not in st.session_state:
        st.session_state['_supabase_client'] = new_client(url, key)
    return st.session_state['_supabase_client']


def current_user():
    """Re-check identity with Supabase rather than trusting user-input email."""
    client = session_client()
    if client is None:
        return None
    try:
        return get_verified_user(client)
    except Exception:
        # Network errors or expired logins should not block public event browsing.
        return None


def sign_out():
    client = st.session_state.get('_supabase_client')
    if client is not None:
        try:
            client.auth.sign_out()
        except Exception:
            pass
    st.session_state.pop('_supabase_client', None)
    st.session_state.pop('pending_email', None)


def readable_url(value):
    if not isinstance(value, str):
        return ''
    url = value.strip()
    parsed = urlsplit(url)
    return url if parsed.scheme in ('http', 'https') and parsed.netloc else ''


def source_icon(event, namespace):
    link = readable_url(event.get('external_url', ''))
    if link:
        st.link_button('🔗', link, help='Open original event announcement')
    else:
        st.button('🔗', disabled=True,
                  key=f'no_link_{namespace}_{event["event_id"]}',
                  help='Link not provided')


def get_saved_map(user):
    if user is None:
        return {event_id: None for event_id in st.session_state.guest_saved_events}
    try:
        return list_saved(session_client(), user['id'])
    except Exception:
        st.error('Unable to load your saved events. Check your Supabase tables and connection.')
        return None


def get_saved_club_ids(user):
    """Guest: temporary session set. Signed in: account-owned Supabase records."""
    if user is None:
        return set(st.session_state.guest_saved_clubs)
    try:
        return list_saved_clubs(session_client(), user['id'])
    except Exception:
        st.error('Unable to load saved clubs. Run database/saved_clubs_migration.sql in Supabase SQL Editor and check your connection.')
        return None


def toggle_club(club_id, user, saved_ids):
    if saved_ids is None:
        return
    saved = club_id in saved_ids
    if user is None:
        if saved:
            st.session_state.guest_saved_clubs.discard(club_id)
        else:
            st.session_state.guest_saved_clubs.add(club_id)
    else:
        try:
            if saved:
                remove_saved_club(session_client(), user['id'], club_id)
            else:
                add_saved_club(session_client(), user['id'], club_id)
        except Exception:
            st.error('Could not update saved clubs. Check Supabase and the saved_clubs table.')
            return
    if saved and st.session_state.get('selected_saved_club') == club_id:
        st.session_state.pop('selected_saved_club', None)
    elif not saved:
        st.session_state.selected_saved_club = club_id
    st.toast('Club removed from your list' if saved else 'Club saved! Find it in My Hub',
             icon='💔' if saved else '♥')
    st.rerun()


def club_card(club, namespace, user, saved_ids):
    """Club directory card: identity, inferred categories, size, and Save club."""
    club_id = str(club['club_id'])
    saved = saved_ids is not None and club_id in saved_ids
    with st.container(border=True, key=f'card_club_{namespace}_{club_id}'):
        if saved:
            st.markdown('<span class="saved-marker"></span>', unsafe_allow_html=True)
        st.markdown(f'<div class="kicker">{esc(str(club["org_size"]).title())} club</div>', unsafe_allow_html=True)
        st.markdown(f"#### {club['org_name']}")
        st.markdown(f'<div class="meta">{esc(str(club["categories"]))}</div>', unsafe_allow_html=True)
        if st.button('♥ Saved club' if saved else '♡ Save club',
                     key=f'club_save_{namespace}_{club_id}',
                     use_container_width=True, disabled=saved_ids is None):
            toggle_club(club_id, user, saved_ids)


def show_club_cards(df, namespace, user, saved_ids, page_size=12):
    """Show only club cards (no event listings) and bottom pagination."""
    if df.empty:
        st.info('No clubs match. Try changing the search or filters.')
        return
    pages = (len(df) + page_size - 1) // page_size
    key = f'{namespace}_page'
    page = min(max(st.session_state.get(key, 1), 1), pages)
    visible = df.iloc[(page - 1) * page_size:page * page_size]
    for start in range(0, len(visible), 2):
        cols = st.columns(2)
        for col, (_, club) in zip(cols, visible.iloc[start:start + 2].iterrows()):
            with col:
                club_card(club, namespace, user, saved_ids)
    st.markdown('')
    show_pagination(pages, namespace)


def interested_clubs_panel(user, saved_ids, saved_events):
    """Saved club buttons switch the event feed below them; then My saved events follows."""
    st.markdown('### Clubs I’m interested in')
    st.caption('Choose a saved club to see its upcoming events. Save more clubs in Explore Clubs.')
    if saved_ids is None:
        return
    saved_clubs = club_summary[club_summary['club_id'].isin(saved_ids)]
    if saved_clubs.empty:
        st.info('No saved clubs yet. Go to Explore Clubs and select ♡ Save club.')
        return
    missing = len(saved_ids) - len(saved_clubs)
    if missing:
        st.warning(f'{missing} saved club(s) are no longer in the available club data.')
    options = saved_clubs.to_dict('records')
    valid_ids = set(saved_clubs['club_id'])
    active = st.session_state.get('selected_saved_club')
    if active not in valid_ids:
        active = options[0]['club_id']
        st.session_state.selected_saved_club = active

    # Clickable club buttons, arranged in rows of up to three.
    for start in range(0, len(options), 3):
        cols = st.columns(3)
        for col, club in zip(cols, options[start:start + 3]):
            club_id = club['club_id']
            with col:
                if st.button(club['org_name'], key=f'select_club_{club_id}',
                             type='primary' if active == club_id else 'secondary',
                             use_container_width=True):
                    st.session_state.selected_saved_club = club_id
                    st.rerun()

    selected = saved_clubs[saved_clubs['club_id'] == active].iloc[0]
    st.markdown(f"#### Upcoming events — {selected['org_name']}")
    upcoming = filter_events(events, club=selected['org_name'], start_date=date.today())
    if upcoming.empty:
        st.info('This club has no upcoming events in the current dataset.')
    else:
        st.caption(f'{len(upcoming)} upcoming event(s)')
        show_cards(upcoming, f'club_upcoming_{active}', user, saved_events, page_size=4)

    st.caption('To stop following a club, use the Saved club button on its Explore Clubs card.')


def toggle_save(event_id, user, saved_map):
    if saved_map is None:
        return
    is_saved = event_id in saved_map
    if user is None:
        if is_saved:
            st.session_state.guest_saved_events.discard(event_id)
        else:
            st.session_state.guest_saved_events.add(event_id)
    else:
        try:
            client = session_client()
            if is_saved:
                remove_saved(client, user['id'], event_id)
            else:
                default_hours = get_profile(client, user['id']).get('default_reminder_hours')
                add_saved(client, user['id'], event_id, default_hours)
        except Exception:
            st.error('Could not update saved events. Check your Supabase connection and RLS policies.')
            return
    st.toast('Removed from your saved events' if is_saved else 'Event saved! Find it in My Hub',
             icon='💔' if is_saved else '♥')
    st.rerun()


def event_card(event, namespace, user, saved_map):
    event_id = str(event['event_id'])
    is_saved = saved_map is not None and event_id in saved_map
    with st.container(border=True, key=f'card_ev_{namespace}_{event_id}'):
        if is_saved:
            st.markdown('<span class="saved-marker"></span>', unsafe_allow_html=True)
        size = str(event.get('org_size', '')).title()
        top_left, top_right = st.columns([8, 1], vertical_alignment='center')
        with top_left:
            kicker = esc(str(event['category'])) + (f' · {esc(size)} club' if size else '')
            st.markdown(f'<div class="kicker">{kicker}</div>', unsafe_allow_html=True)
        with top_right:
            source_icon(event, namespace)
        st.markdown(f"#### {event['title']}")
        food = '<div class="food">🍕 Food mentioned</div>' if event.get('free_food', False) else ''
        st.markdown(
            f'<div class="host">{esc(str(event["org_name"]))}</div>'
            f'<div class="meta">{event["event_date"].strftime("%a, %b %d, %Y")} · {esc(str(event["start_time"]))}</div>'
            f'<div class="meta">{esc(str(event["location"]))}</div>{food}',
            unsafe_allow_html=True,
        )
        save_col, details_col = st.columns(2)
        if save_col.button('♥ Saved' if is_saved else '♡ Save event',
                           key=f'save_{namespace}_{event_id}',
                           use_container_width=True, disabled=saved_map is None):
            toggle_save(event_id, user, saved_map)
        with details_col.popover('Event details', use_container_width=True):
            st.write(f"**Host:** {event['org_name']}")
            st.write(f"**Category:** {event['category']}")
            st.write(f"**Where:** {event['location']}")
            st.write(f"**When:** {event['event_date'].strftime('%B %d, %Y')} at {event['start_time']}")
            st.write(f"**Listed on:** {event['platforms']}")
            if event.get('free_food', False):
                st.write('🍕 Food mentioned in listing')
            if event.get('time_conflict', False):
                st.warning('Listings disagreed on this event’s time. Verify with the organizer.')
            if not readable_url(event.get('external_url', '')):
                st.caption('Link not provided for this event.')
            st.divider()
            st.markdown('**Report an issue with this event**')
            portal_store=get_store()
            ticket_user=('demo-student' if is_demo() else (user or {}).get('id'))
            if portal_store is None or not ticket_user:
                st.caption('Sign in through My Hub to submit a ticket.')
            else:
                related=next((c['id'] for c in portal_store.clubs()
                              if normalize_name(c['org_name']) == normalize_name(str(event['org_name']))), None)
                submit_ticket_form(portal_store,ticket_user,
                    prefix='event_'+str(namespace)+'_'+str(event_id),
                    event_ref=str(event_id),club_id=related)


def show_pagination(total_pages, key):
    state_key = f'{key}_page'
    st.session_state[state_key] = min(max(st.session_state.get(state_key, 1), 1), total_pages)
    prev_col, count_col, next_col = st.columns([1, 3, 1])
    with prev_col:
        if st.button('‹ Previous', key=f'{key}_prev',
                     disabled=st.session_state[state_key] <= 1, use_container_width=True):
            st.session_state[state_key] -= 1
            st.rerun()
    with count_col:
        st.markdown(
            f"<div style='text-align:center;padding-top:.45rem'>"
            f"<strong>Page {st.session_state[state_key]} of {total_pages}</strong></div>",
            unsafe_allow_html=True,
        )
    with next_col:
        if st.button('Next ›', key=f'{key}_next',
                     disabled=st.session_state[state_key] >= total_pages,
                     use_container_width=True):
            st.session_state[state_key] += 1
            st.rerun()


def show_cards(df, namespace, user, saved_map, page_size=12):
    if df.empty:
        st.info('No events match. Try changing your search or filters.')
        return
    pages = (len(df) + page_size - 1) // page_size
    page_key = f'{namespace}_page'
    page = min(max(st.session_state.get(page_key, 1), 1), pages)
    visible = df.iloc[(page - 1) * page_size:page * page_size]
    for start in range(0, len(visible), 2):
        cols = st.columns(2)
        for col, (_, event) in zip(cols, visible.iloc[start:start + 2].iterrows()):
            with col:
                event_card(event, namespace, user, saved_map)
    st.markdown('')
    show_pagination(pages, namespace)


def login_panel():
    st.markdown('### UCSD email sign-in')
    if session_client() is None:
        st.info('Account sign-in is not configured yet. Public browsing and temporary saving still work. '
                'See the README to connect Supabase.')
        return
    st.write('Sign in with your **@ucsd.edu** email to keep events across sessions and edit your profile. '
             'Name, class standing, and major are optional.')
    with st.form('send_code'):
        email = st.text_input('UCSD email', placeholder='yourname@ucsd.edu')
        requested = st.form_submit_button('Send verification code')
    if requested:
        if not is_ucsd_email(email):
            st.error('Enter a valid @ucsd.edu email address.')
        else:
            try:
                send_login_code(session_client(), email)
                st.session_state.pending_email = email.strip().lower()
                st.success('Verification requested. Check your UCSD inbox for the code.')
            except Exception:
                st.error('Could not send a code. Check the email configuration or rate limits and retry.')
    if st.session_state.get('pending_email'):
        st.caption(f"Verifying: {st.session_state.pending_email}")
        with st.form('verify_code'):
            code = st.text_input('Verification code', type='password', placeholder='6-digit code')
            confirmed = st.form_submit_button('Verify and sign in')
        if confirmed:
            try:
                verify_login_code(session_client(), st.session_state.pending_email, code)
                st.session_state.pop('pending_email', None)
                st.rerun()
            except ValueError as error:
                st.error(str(error))
            except Exception:
                st.error('Code could not be verified. Check the code and try again.')


def saved_events_panel(user, saved_map):
    st.markdown('### My saved events')
    if user is None:
        st.caption('Guest saves last only as long as this Streamlit browser session.')
    else:
        st.caption('Saved to your verified UCSD account. Your choices remain after signing out.')
    if saved_map is None:
        return
    saved_count = len(saved_map)
    st.metric('Saved events', saved_count)
    if not saved_count:
        st.info('Nothing saved yet. Visit Explore Events and select ♡ Save event.')
        return
    matching = events[events['event_id'].isin(saved_map)]
    missing_count = saved_count - len(matching)
    if missing_count:
        st.warning(f'{missing_count} saved event(s) are no longer in the current event data.')
    show_cards(matching, 'myhub', user, saved_map, page_size=6)

    if user:
        st.markdown('#### Event reminder preferences')
        st.caption('Preferences are stored now. **Automatic reminder emails are not active yet.**')
        for _, event in matching.iterrows():
            event_id = str(event['event_id'])
            with st.expander(f"{event['title']} — {event['org_name']}"):
                current_label = format_reminder(saved_map.get(event_id))
                options = list(REMINDER_OPTIONS)
                with st.form(key=f'reminder_form_{event_id}'):
                    selected = st.selectbox('Email reminder preference', options,
                                            index=options.index(current_label),
                                            key=f'reminder_select_{event_id}')
                    apply_choice = st.form_submit_button('Save reminder preference')
                if apply_choice:
                    try:
                        update_reminder(session_client(), user['id'], event_id,
                                        REMINDER_OPTIONS[selected])
                        st.success('Preference saved. Email delivery is not active yet.')
                        st.rerun()
                    except Exception:
                        st.error('Could not save reminder preference.')


def profile_panel(user):
    try:
        profile = get_profile(session_client(), user['id'])
    except Exception:
        st.error('Unable to load your profile. Check database setup.')
        return
    st.markdown('### My profile')
    st.write(f"**Verified email:** {user['email']}")
    st.caption('Everything below is optional. Leave fields blank if you prefer.')
    standing = profile.get('class_standing') or 'Not specified'
    if standing not in CLASS_OPTIONS:
        standing = 'Not specified'
    with st.form('profile_form'):
        display_name = st.text_input('Display name (optional)',
                                     value=profile.get('display_name') or '', max_chars=80)
        selected_standing = st.selectbox('Class standing (optional)', CLASS_OPTIONS,
                                         index=CLASS_OPTIONS.index(standing))
        major = st.text_input('Major (optional)',
                              value=profile.get('major') or '', max_chars=120)
        submitted = st.form_submit_button('Save profile')
    if submitted:
        try:
            save_profile(session_client(), user['id'],
                         display_name=display_name.strip() or None,
                         class_standing=None if selected_standing == 'Not specified' else selected_standing,
                         major=major.strip() or None)
            st.success('Profile saved.')
            st.rerun()
        except Exception:
            st.error('Could not save profile. Check the database configuration.')


def notifications_panel(user):
    st.markdown('### Notification settings')
    st.info('Email reminders are planned but **not sent by this version**. '
            'Your preferences will be ready for the later delivery integration.')
    try:
        profile = get_profile(session_client(), user['id'])
    except Exception:
        st.error('Unable to load notification settings.')
        return
    selected = format_reminder(profile.get('default_reminder_hours'))
    labels = list(REMINDER_OPTIONS)
    with st.form('default_reminder'):
        choice = st.selectbox('Default for newly saved events', labels,
                              index=labels.index(selected))
        st.caption('You can override this for individual events in My saved events. '
                   'Changing the default does not change previously saved events.')
        save = st.form_submit_button('Save default preference')
    if save:
        try:
            save_profile(session_client(), user['id'],
                         default_reminder_hours=REMINDER_OPTIONS[choice],
                         fields=('default_reminder_hours',))
            st.success('Default preference saved.')
            st.rerun()
        except Exception:
            st.error('Could not save notification settings.')


def page_my_hub():
    st.subheader('My Hub')
    user = current_user()
    if user is None:
        st.write('Welcome to your personal space. Browse as a guest, or verify a UCSD email '
                 'to keep events and preferences saved across sessions.')
        login_panel()
        st.divider()
        interested_clubs_panel(None, get_saved_club_ids(None), get_saved_map(None))
        st.divider()
        saved_events_panel(None, get_saved_map(None))
        return

    left, right = st.columns([4, 1], vertical_alignment='center')
    with left:
        st.success(f"Signed in: {user['email']}")
    with right:
        st.button('Sign out', on_click=sign_out, use_container_width=True)
    guest_event_count = len(st.session_state.guest_saved_events)
    guest_club_count = len(st.session_state.guest_saved_clubs)
    if guest_event_count or guest_club_count:
        st.info(f'You have {guest_club_count} guest club save(s) and '
                f'{guest_event_count} guest event save(s). Import them into your account.')
        if st.button('Import guest saves'):
            try:
                client = session_client()
                default_hours = get_profile(client, user['id']).get('default_reminder_hours')
                for club_id in list(st.session_state.guest_saved_clubs):
                    add_saved_club(client, user['id'], club_id)
                    st.session_state.guest_saved_clubs.discard(club_id)
                for event_id in list(st.session_state.guest_saved_events):
                    # Don't overwrite an existing event's reminder preference.
                    if event_id not in list_saved(client, user['id']):
                        add_saved(client, user['id'], event_id, default_hours)
                    st.session_state.guest_saved_events.discard(event_id)
                st.rerun()
            except Exception:
                st.error('Could not import all guest saves. Check the saved_clubs migration and retry.')

    overview_tab, profile_tab, settings_tab = st.tabs([
        'My Events & Clubs', 'My Profile', 'Notification Settings'
    ])
    with overview_tab:
        interested_clubs_panel(user, get_saved_club_ids(user), get_saved_map(user))
        st.divider()
        saved_events_panel(user, get_saved_map(user))
    with profile_tab:
        profile_panel(user)
    with settings_tab:
        notifications_panel(user)


def page_events():
    st.subheader('Find your next event')
    user = current_user()
    keyword_col, category_col = st.columns([2, 1])
    query = keyword_col.text_input('Search events, clubs, or locations',
                                   placeholder='Try Python, workshop, Geisel Library')
    categories = category_col.multiselect('Event category',
                                           sorted(events['category'].unique().tolist()))
    with st.expander('More filters'):
        upcoming = st.checkbox('Upcoming only', value=True)
        from_date = st.date_input('From date', value=None, key='date_from')
        through_date = st.date_input('Through date', value=None, key='date_to')
        if from_date and through_date and from_date > through_date:
            st.error('The start date must be on or before the end date.')
            st.stop()
    earliest = (max(date.today(), from_date) if from_date else date.today()) if upcoming else from_date
    matches = filter_events(events, query, categories, earliest, through_date)
    st.write(f'**{len(matches)} events found**')
    st.caption('You can save events without signing in; sign in through My Hub to save them permanently.')
    show_cards(matches, 'browse', user, get_saved_map(user))


def page_clubs():
    st.subheader('Explore student organizations')
    st.write('Discover clubs by name, category, and size. Save the ones you’re interested in.')
    user = current_user()

    search_col, category_col, size_col = st.columns([2, 1.3, 1])
    with search_col:
        search = st.text_input('Search clubs', placeholder='Try AI Builders or Picnic Society')
    all_categories = sorted({tag for tags in club_summary['category_tags'] for tag in tags})
    with category_col:
        selected_categories = st.multiselect('Club categories', all_categories,
                                             placeholder='All categories')
    with size_col:
        selected_sizes = st.multiselect('Club size', ['Small', 'Medium', 'Large'],
                                        placeholder='All sizes')

    candidates = filter_clubs(club_summary, search, selected_categories, selected_sizes)
    st.write(f'**{len(candidates)} clubs found**')
    st.caption('Club categories are inferred from their event listings, not an official university directory.')
    show_club_cards(candidates, 'clubs', user, get_saved_club_ids(user))

def page_support():
    st.subheader('Help and support')
    st.write('Report website bugs, account problems, or inaccurate event information.')
    st.caption('Content reports linked to a registered club are routed to that club. Technical reports are tracked for developer follow-up.')
    store=get_store()
    user=current_user()
    ticket_user='demo-student' if is_demo() else (user or {}).get('id')
    if store is None:
        st.error('Supabase MVP database not configured.')
    elif ticket_user is None:
        st.info('Sign in using My Hub to submit and track a ticket.')
    else:
        submit_ticket_form(store,ticket_user,prefix='student_general')
        st.markdown('#### Your submitted tickets')
        try:
            rows=[t for t in store.tickets(user_id=ticket_user)
                  if t['reporter_id']==ticket_user]
            if not rows:
                st.info('No tickets submitted yet.')
            for ticket in rows:
                with st.expander(f"{ticket['category'].replace('_',' ').title()} · {ticket['status']} · {str(ticket['id'])[:8]}"):
                    st.write(ticket['description'])
                    st.caption('Routed to '+ticket['route'])
        except Exception as exc:
            st.error(f'Could not load tickets: {exc}')


def page_calendar():
    st.subheader('Calendar view of your saved events')
    st.write('See your saved events in a calendar format. This view is for planning and visualization.')

    events = get_events()
    saved = events[events['event_id'].isin(get_saved_map(current_user()))]

    saved_dict = []

    for i in range(len(saved)):
        saved_dict.append({
            'title': saved.iloc[i]['start_time'] + ': ' + saved.iloc[i]['title'],
            'start': str(saved.iloc[i]['event_date']),
            'end': str(saved.iloc[i]['event_date']),
            'allDay': True,
            'backgroundColor': '#EAF3FA',
            'borderColor': '#00629B',
            'textColor': '#182B49',
            'classNames': ['hub-event--saved'],
        })

    calendar_options = {
        "editable": False,
        "selectable": True,
        "initialView": "dayGridMonth",
        "dayMaxEvents": 4,
        "themeSystem": "standard",
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,listWeek",
        },
    }

    # FullCalendar is inside an iframe; supply its own high-contrast UCSD theme.
    calendar_css = UCSD_CALENDAR_CSS
    state = calendar(events = saved_dict, options = calendar_options, custom_css = calendar_css, key = "my_calendar")


events = get_events()
club_summary = get_clubs(events)
if 'guest_saved_events' not in st.session_state:
    st.session_state.guest_saved_events = set()
if 'guest_saved_clubs' not in st.session_state:
    st.session_state.guest_saved_clubs = set()

st.markdown('''<div class="hero">
<h1>Campus Event Hub</h1>
<h2>Discover what’s happening on campus, explore student organizations, and find your community at UC San Diego!</h2>
</div>''', unsafe_allow_html=True)

# Default landing page: My Hub, with public discovery always available.
pages = [
    st.Page(page_my_hub, title='My Hub', default=True),
    st.Page(page_events, title='Explore Events'),
    st.Page(page_clubs, title='Explore Clubs'),
    st.Page(page_calendar, title='Calendar'),
    st.Page(page_support, title='Support'),
]
selected_page = st.navigation(pages, position='top')
selected_page.run()