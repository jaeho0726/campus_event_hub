"""Streamlit components shared by Club, Client, and Student portals."""
from datetime import datetime

import streamlit as st
from account_store import get_verified_user, is_ucsd_email, send_login_code, verify_login_code
from mvp_store import is_demo

CATEGORY_OPTIONS = ['Tech', 'Cultural', 'Career/Professional', 'Social', 'Arts', 'Service', 'Sports/Rec', 'General Meeting', 'Other']
CLUB_CATEGORIES = ['Technology', 'Cultural', 'Academic', 'Professional', 'Social', 'Arts', 'Service', 'Sports/Recreation', 'Other']
TICKET_TYPES = {
    'Incorrect event information': 'event_info',
    'Website bug': 'website_bug',
    'Account/login problem': 'account',
    'Other / feedback': 'other',
}
STATUS_LABEL = {'open':'Open', 'in_progress':'In progress', 'resolved':'Resolved'}


def style_portal():
    """High-contrast UCSD light theme used by BOTH admin portals.

    Streamlit's main CSS does not style the calendar iframe. The calendar theme
    is defined separately in calendar_theme.py and passed to calendar().
    """
    st.markdown(r'''<style>
    :root {
      --ucsd-navy:#182B49; --ucsd-blue:#00629B; --ucsd-yellow:#FFCD00;
      --ucsd-bg:#F7FAFD; --ucsd-pale:#EAF3FA; --ucsd-line:#D7E4EF;
      --ucsd-muted:#46617A;
      color-scheme:light;
    }
    .stApp, [data-testid="stAppViewContainer"],
    [data-testid="stMain"], [data-testid="stMainBlockContainer"] {
      background-color:var(--ucsd-bg) !important;
      color:var(--ucsd-navy) !important;
    }
    [data-testid="stHeader"] {background-color:var(--ucsd-bg) !important;}
    .block-container {padding-top:1.7rem; padding-bottom:3rem; max-width:1250px;}
    h1,h2,h3,h4,h5,h6, [data-testid="stHeadingWithActionElements"] {
      color:var(--ucsd-navy) !important;
    }
    /* Base text stays navy, but do not override every nested span. On
       colored surfaces those elements must inherit white text instead. */
    [data-testid="stMarkdownContainer"] {color:var(--ucsd-navy);}
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p,
    [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] label,
    [data-testid="stMarkdownContainer"] small {
      color:var(--ucsd-muted) !important;
    }
    .hub-managed-club {
      background:#FFFFFF; border:1px solid #B7CDE0;
      border-left:5px solid var(--ucsd-blue); border-radius:12px;
      padding:1rem 1.25rem; margin:0.8rem 0 1.2rem;
    }
    .hub-managed-club__eyebrow {font-size:.72rem; letter-spacing:.08em; font-weight:700; color:var(--ucsd-blue);}
    .hub-managed-club__name {font-size:1.5rem; font-weight:750; line-height:1.5; color:var(--ucsd-navy);}
    .hub-managed-club__meta {font-size:.86rem; color:var(--ucsd-muted);}
    /* Form labels, text-entry fields and select menus must stay readable even
       when a browser has previously saved a dark Streamlit theme. */
    [data-testid="stTextInput"] [data-baseweb="input"],
    [data-testid="stTextArea"] [data-baseweb="textarea"],
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
    [data-testid="stDateInput"] [data-baseweb="input"],
    [data-testid="stTimeInput"] [data-baseweb="input"],
    [data-testid="stNumberInput"] [data-baseweb="input"],
    [data-baseweb="popover"] [role="listbox"] {
      background-color:#FFFFFF !important;
      color:var(--ucsd-navy) !important;
      border-color:var(--ucsd-line) !important;
    }
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stDateInput"] input,
    [data-testid="stTimeInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] [data-baseweb="select"] *,
    [data-testid="stMultiSelect"] [data-baseweb="select"] *,
    [data-baseweb="popover"] [role="option"] {
      color:var(--ucsd-navy) !important;
      -webkit-text-fill-color:var(--ucsd-navy) !important;
    }
    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stTextArea"] textarea::placeholder {
      color:#657D91 !important; -webkit-text-fill-color:#657D91 !important;
      opacity:1 !important;
    }
    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus {
      outline-color:var(--ucsd-blue) !important;
    }

    /* Streamlit uses BaseWeb wrappers that can retain dark backgrounds even
       when the main app is light. These selectors also reach nested nodes. */
    [data-testid="stTextInput"] [data-baseweb="base-input"],
    [data-testid="stTextInput"] [data-baseweb="input"],
    [data-testid="stTextArea"] [data-baseweb="base-input"],
    [data-testid="stTextArea"] [data-baseweb="textarea"],
    [data-testid="stDateInput"] [data-baseweb="base-input"],
    [data-testid="stDateInput"] [data-baseweb="input"],
    [data-testid="stTimeInput"] [data-baseweb="base-input"],
    [data-testid="stTimeInput"] [data-baseweb="input"],
    [data-testid="stNumberInput"] [data-baseweb="base-input"],
    [data-testid="stNumberInput"] [data-baseweb="input"],
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
      background:#FFFFFF !important;
      background-color:#FFFFFF !important;
      border-color:var(--ucsd-line) !important;
      color:var(--ucsd-navy) !important;
      -webkit-text-fill-color:var(--ucsd-navy) !important;
    }
    /* Native form input backgrounds, not only their outer wrappers. */
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stDateInput"] input,
    [data-testid="stTimeInput"] input,
    [data-testid="stNumberInput"] input {
      background-color:#FFFFFF !important;
      color:var(--ucsd-navy) !important;
      -webkit-text-fill-color:var(--ucsd-navy) !important;
      caret-color:var(--ucsd-blue) !important;
    }
    /* Dropdown popup menus live outside the selectbox widget tree. */
    [data-baseweb="popover"],
    [data-baseweb="popover"] > div,
    [data-baseweb="menu"],
    [data-baseweb="menu"] > div,
    [role="listbox"] {
      background-color:#FFFFFF !important;
      color:var(--ucsd-navy) !important;
    }
    [role="option"], [role="option"] * {
      color:var(--ucsd-navy) !important;
      -webkit-text-fill-color:var(--ucsd-navy) !important;
    }
    [data-testid="stForm"], [data-testid="stExpander"] {
      background-color:#FFFFFF !important; border-color:var(--ucsd-line) !important;
      border-radius:12px;
    }
    div[data-testid="stMetric"] {
      background-color:#FFFFFF !important; border:1px solid var(--ucsd-line) !important;
      border-radius:12px; padding:0.85rem 1rem;
    }
    [data-testid="stMetricLabel"] *, [data-testid="stMetricValue"] * {
      color:var(--ucsd-navy) !important;
    }
    div[data-testid="stButton"] button,
    div[data-testid="stFormSubmitButton"] button,
    [data-testid="stDownloadButton"] button {
      border-radius:9px !important; border:1px solid var(--ucsd-blue) !important;
      background-color:#FFFFFF !important; color:var(--ucsd-blue) !important;
      font-weight:600;
    }
    div[data-testid="stButton"] button p,
    div[data-testid="stFormSubmitButton"] button p {color:inherit !important;}
    div[data-testid="stButton"] button:hover,
    div[data-testid="stFormSubmitButton"] button:hover {
      background-color:var(--ucsd-pale) !important; border-color:var(--ucsd-navy) !important;
      color:var(--ucsd-navy) !important;
    }
    button[kind="primary"], button[data-testid="stBaseButton-primary"] {
      background:var(--ucsd-blue) !important; color:#FFFFFF !important;
      border-color:var(--ucsd-blue) !important;
    }
    button[kind="primary"] p, button[data-testid="stBaseButton-primary"] p {
      color:#FFFFFF !important;
    }
    button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
      background:var(--ucsd-navy) !important; border-color:var(--ucsd-navy) !important;
      color:#FFFFFF !important;
    }
    [data-testid="stTabs"] [role="tab"] {color:var(--ucsd-muted) !important; font-weight:600;}
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {color:var(--ucsd-blue) !important;}
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] {background:var(--ucsd-blue) !important;}
    [data-testid="stAlert"] {background:#EAF3FA !important; border:1px solid #B8D4E8 !important;}
    [data-testid="stAlert"] p, [data-testid="stAlert"] strong,
    [data-testid="stAlert"] [data-testid="stMarkdownContainer"] * {
      color:var(--ucsd-navy) !important;
    }
    [data-testid="stDataFrame"], [data-testid="stTable"] {background:#FFFFFF !important;}
    :focus-visible {outline-color:var(--ucsd-blue);}
    </style>''',unsafe_allow_html=True)


def identity(store, role):
    """Get a server-verified identity, or explicitly simulated identity in local demo."""
    if is_demo():
        st.caption('Local demo · simulated account; not for public deployment.')
        if role == 'club':
            # These are local, fake identities — never used for production auth.
            # Officer A/B have no seeded clubs; switching lets testers walk
            # through the exact first-time registration path independently.
            account_ids = ['demo-officer', 'demo-new-officer-a', 'demo-new-officer-b']
            club_names = {}
            for club in store.clubs():
                club_names.setdefault(club['owner_id'], []).append(club['org_name'])

            def account_label(account_id):
                title = {
                    'demo-officer': 'Existing officer — Triton Demo Makers',
                    'demo-new-officer-a': 'New officer A',
                    'demo-new-officer-b': 'New officer B',
                }[account_id]
                owned = club_names.get(account_id, [])
                if owned:
                    return f"{title} · {', '.join(owned)}" if account_id != 'demo-officer' else title
                return f'{title} · no club registered'

            demo_id = st.selectbox('Test as (demo account)', account_ids,
                                   format_func=account_label,
                                   key='demo_club_test_identity')
            if st.session_state.get('_last_demo_club_identity') != demo_id:
                # Don't carry draft / active-club state across fake accounts.
                for name in ('active_club_id', 'available_club_name',
                             'pending_event', 'pending_conflicts'):
                    st.session_state.pop(name, None)
                for name in list(st.session_state.keys()):
                    if name.startswith('pending_edit_'):
                        st.session_state.pop(name, None)
                st.session_state['_last_demo_club_identity'] = demo_id
            if not club_names.get(demo_id):
                st.caption('First-time officer test: enter an unused club name, check availability, and complete registration. No email setup needed.')
            else:
                st.caption('Returning officer test: use the dashboard to publish, edit, or cancel events for your club.')
        else:
            demo_id={'student':'demo-student','client':'demo-client'}[role]
        return {'id':demo_id,'email':f'{demo_id}@example.invalid'}
    if store is None:
        st.error('Supabase is not configured. See README.md or start with MVP_DEMO_MODE=1.')
        st.stop()
    from mvp_store import SupabaseStore
    if not isinstance(store,SupabaseStore):
        st.stop()
    client=store.client
    user=None
    try:
        user=get_verified_user(client)
    except Exception:
        pass
    if user:
        col1,col2=st.columns([4,1])
        col1.caption('Signed in as '+user['email'])
        if col2.button('Sign out',key=f'signout_{role}'):
            client.auth.sign_out()
            st.rerun()
        return user
    st.info('UCSD email verification required for this portal. You can browse events without signing in on the student website.')
    with st.form(f'{role}_send_code'):
        email=st.text_input('UCSD email',key=f'{role}_email')
        send=st.form_submit_button('Send verification code')
    if send:
        if not is_ucsd_email(email):
            st.error('Enter a valid @ucsd.edu email address.')
        else:
            try:
                send_login_code(client,email)
                st.session_state[f'{role}_pending_email']=email.strip().lower()
                st.success('Code requested; check your inbox.')
            except Exception:
                st.error('Could not send code. Check Supabase SMTP and rate limits.')
    if st.session_state.get(f'{role}_pending_email'):
        with st.form(f'{role}_verify_code'):
            code=st.text_input('Verification code',type='password')
            check=st.form_submit_button('Verify')
        if check:
            try:
                verify_login_code(client,st.session_state[f'{role}_pending_email'],code)
                st.session_state.pop(f'{role}_pending_email',None)
                st.rerun()
            except Exception:
                st.error('Could not verify the code.')
    st.stop()


def submit_ticket_form(store, user_id, *, prefix, event_ref='', club_id=None):
    """Require authentication except explicit local demo; route by category automatically."""
    with st.form(f'ticket_form_{prefix}'):
        label=st.selectbox('Issue type',list(TICKET_TYPES),key=f'ticket_type_{prefix}')
        description=st.text_area('What happened? (10–2000 characters)',max_chars=2000,
                                 placeholder='Describe the issue and what you expected to happen...',key=f'ticket_desc_{prefix}')
        submitted=st.form_submit_button('Submit ticket')
    if submitted:
        try:
            ticket_id=store.create_ticket({
                'event_ref':event_ref or None,'club_id':club_id,
                'category':TICKET_TYPES[label],'description':description,
            },user_id)
            st.success('Ticket submitted: '+str(ticket_id)[:8]+'. You can track its status in this portal.')
            return ticket_id
        except (ValueError,PermissionError) as exc:
            st.error(str(exc))
        except Exception:
            st.error('Ticket submission failed. Check the database schema and connection.')
    return None


def show_tickets(store, user, admin=False):
    try:
        tickets=store.tickets(user_id=user['id'],admin=admin)
    except Exception as exc:
        st.error(f'Could not load tickets: {exc}')
        return
    if not tickets:
        st.info('No tickets yet.')
        return
    if admin:
        route_filter=st.selectbox('Ticket route', ['All','club','developer','client'])
        if route_filter!='All':
            tickets=[t for t in tickets if t['route']==route_filter]
    for ticket in tickets:
        title=f"{ticket['category'].replace('_',' ').title()} · {STATUS_LABEL.get(ticket['status'], ticket['status'])} · {ticket['id'][:8]}"
        with st.expander(title):
            st.write(ticket['description'])
            st.caption(f"Route: {ticket['route']} | Linked event: {ticket.get('event_ref') or 'None'} | Reporter: {str(ticket['reporter_id'])[:8]}")
            can_edit = admin or (ticket['route']=='club' and any(
                c['id']==ticket.get('club_id') and c['owner_id']==user['id'] for c in store.clubs()))
            if can_edit:
                choices=list(STATUS_LABEL)
                current=ticket['status'] if ticket['status'] in choices else 'open'
                with st.form('ticket_update_'+str(ticket['id'])):
                    status=st.selectbox('Status',choices,format_func=lambda x:STATUS_LABEL[x],index=choices.index(current))
                    if st.form_submit_button('Update status'):
                        try:
                            store.update_ticket(ticket['id'],status,user['id'],is_admin=admin)
                            st.success('Ticket updated.')
                            st.rerun()
                        except Exception as exc:
                            st.error(f'Update failed: {exc}')
