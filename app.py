"""Campus Event Hub | DataWorks consulting showcase prototype.
Run: streamlit run app.py
All events and survey data are SYNTHETIC workshop examples, not live UCSD listings.
"""
from datetime import datetime, timedelta, date
from pathlib import Path
import html
import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent
st.set_page_config(page_title="Campus Event Hub | DataWorks", page_icon="📅", layout="wide")

st.markdown("""<style>
.block-container {max-width: 1180px; padding-top: 1.6rem;}
h1, h2, h3 {letter-spacing: -.025em;}
[data-testid="stMetric"] {background: #f5f8fc; border-radius: 12px; padding: .7rem 1rem;}
.event-card {border:1px solid #dce2ed; border-radius:14px; padding:1rem 1.15rem; margin:.45rem 0 .3rem; background:var(--secondary-background-color);}
.event-card .eyebrow {font-size:.82rem; opacity:.8; margin-bottom:.3rem;}
.event-card .heading {font-size:1.18rem; font-weight:700; margin-bottom:.3rem;}
.event-card .detail {font-size:.92rem; line-height:1.6;}
.muted {opacity:.7;font-size:.82rem;}
</style>""", unsafe_allow_html=True)

@st.cache_data
def load_events():
    df = pd.read_csv(BASE / "events_clean.csv")
    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    df["time_conflict"] = df["time_conflict"].astype(str).str.lower().eq("true")
    df["free_food"] = df["free_food"].astype(str).str.lower().eq("true")
    df["event_id"] = (df["org_name"].fillna("") + "|" + df["event_date"].dt.strftime("%Y-%m-%d") + "|" + df["title"].fillna("")).str.lower()
    return df

@st.cache_data
def load_survey():
    return pd.read_csv(BASE / "survey_clean.csv")


def ics_escape(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def calendar_file(event):
    dt = datetime.strptime(event["event_date"].strftime("%Y-%m-%d") + " " + event["start_time"], "%Y-%m-%d %I:%M %p")
    end = dt + timedelta(hours=1)  # Duration unknown; mark as an assumption in the event.
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//DataWorks//Campus Event Hub Demo//EN",
             "BEGIN:VEVENT", f"UID:{abs(sum((i+1)*ord(c) for i,c in enumerate(event['event_id'])))}@campuseventhub.demo",
             f"DTSTAMP:{stamp}", f"DTSTART:{dt:%Y%m%dT%H%M%S}", f"DTEND:{end:%Y%m%dT%H%M%S}",
             f"SUMMARY:{ics_escape(event['title'] + ' — ' + event['org_name'])}",
             f"LOCATION:{ics_escape(event['location'])}",
             f"DESCRIPTION:{ics_escape('Demo event from synthetic DataWorks data. Confirm details with the club. One-hour duration is assumed.')}",
             "BEGIN:VALARM", "TRIGGER:-P1D", "ACTION:DISPLAY", "DESCRIPTION:Upcoming campus event", "END:VALARM",
             "END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(lines) + "\r\n"


def show_event(event, idx):
    cat = html.escape(str(event["category"]))
    title = html.escape(str(event["title"]))
    org = html.escape(str(event["org_name"]))
    location = html.escape(str(event["location"]))
    date_label = event["event_date"].strftime("%a, %b %-d, %Y")
    time = html.escape(str(event["start_time"]))
    tags = (" · 🍕 Free food" if event["free_food"] else "") + (" · ⚠️ Time discrepancy in source listings" if event["time_conflict"] else "")
    st.markdown(f'''<div class="event-card"><div class="eyebrow">{cat} · {html.escape(str(event['org_size']).title())} club</div>
      <div class="heading">{title}</div><div class="detail"><b>{org}</b><br>📅 {date_label} at {time} &nbsp;·&nbsp; 📍 {location}<br>
      <span class="muted">Listed on: {html.escape(str(event['platforms']))}{html.escape(tags)}</span></div></div>''', unsafe_allow_html=True)
    a, b, c = st.columns([1, 1, 2])
    is_following = org in st.session_state.followed_clubs
    if a.button("✓ Following" if is_following else "+ Follow club", key=f"follow_{idx}_{event['event_id']}"):
        if is_following: st.session_state.followed_clubs.remove(org)
        else: st.session_state.followed_clubs.add(org)
        st.rerun()
    b.download_button("🔔 Add reminder", data=calendar_file(event), file_name=f"event_{idx}.ics",
                      mime="text/calendar", key=f"ics_{idx}_{event['event_id']}")
    with c.popover("Source details"):
        st.write("Source platform(s):", event["platforms"])
        st.caption("The workshop dataset does not contain original post URLs. Links will be enabled when the club submits verified URLs.")
        if event["time_conflict"]: st.warning("Cross-posts had conflicting times. Confirm the start time with the organizer.")
        st.caption("Calendar reminder assumes a one-hour event because event duration is not in the source data.")


events = load_events()
if "followed_clubs" not in st.session_state: st.session_state.followed_clubs = set()
if "interests" not in st.session_state: st.session_state.interests = []

st.title("📅 Campus Event Hub")
st.caption("A DataWorks consulting prototype for easier club-event discovery at UC San Diego")
st.info("**Demo dataset:** 501 synthetic workshop events (September 28–December 4, 2026). This is not a live university calendar. Event details and times are illustrative.")

browse, for_you, about = st.tabs(["🔎 Browse events", "✨ For you", "📊 Evidence & pilot"])

with st.sidebar:
    st.header("Your interests")
    categories = sorted(events["category"].dropna().unique().tolist())
    st.multiselect("I'm interested in", options=categories, key="interests")
    st.caption("Preferences are stored only for this browser session. No account or student information is collected.")
    st.divider()
    st.markdown(f"**Following {len(st.session_state.followed_clubs)} clubs**")
    if st.session_state.followed_clubs:
        for org in sorted(st.session_state.followed_clubs): st.caption("• " + org)
    else: st.caption("Follow a club from an event card to personalize your feed.")

with browse:
    st.subheader("Find events across campus")
    c1, c2, c3 = st.columns([2, 1, 1])
    query = c1.text_input("Search by club, event, or location", placeholder="e.g., workshop, Robotics, Price Center")
    selected_categories = c2.multiselect("Category", categories)
    size_choice = c3.selectbox("Club size", ["All", "Small", "Medium", "Large"])
    c4, c5 = st.columns([1, 1])
    upcoming_only = c4.checkbox("Upcoming events only", value=True)
    food_only = c5.checkbox("Free food only", value=False)
    filtered = events.copy()
    if query.strip():
        mask = (filtered[["org_name", "title", "location"]].fillna("").astype(str)
                .apply(lambda col: col.str.contains(query.strip(), case=False, regex=False)).any(axis=1))
        filtered = filtered[mask]
    if selected_categories: filtered = filtered[filtered["category"].isin(selected_categories)]
    if size_choice != "All": filtered = filtered[filtered["org_size"].str.lower() == size_choice.lower()]
    if upcoming_only: filtered = filtered[filtered["event_date"].dt.date >= date.today()]
    if food_only: filtered = filtered[filtered["free_food"]]
    filtered = filtered.sort_values(["event_date", "start_time", "org_name"])
    st.write(f"**{len(filtered)} events found**")
    if filtered.empty:
        st.warning("No events match these filters. Try turning off 'Upcoming events only' to explore the historical demo data.")
    else:
        limit = st.selectbox("Events per page", [10, 20, 50], index=0)
        max_page = max(1, (len(filtered) + limit - 1) // limit)
        page = st.number_input("Page", min_value=1, max_value=max_page, value=1, step=1)
        for idx, ev in filtered.iloc[(page-1)*limit:page*limit].iterrows(): show_event(ev, idx)

with for_you:
    st.subheader("Events matched to your interests")
    interests = st.session_state.interests
    follows = st.session_state.followed_clubs
    if not interests and not follows:
        st.write("Choose interest categories in the sidebar, or follow clubs in the Browse tab, to build your personalized feed.")
    else:
        recommendations = events.copy()
        recommendations = recommendations[recommendations["event_date"].dt.date >= date.today()].copy()
        recommendations["match_score"] = (recommendations["category"].isin(interests).astype(int) * 1
                                          + recommendations["org_name"].isin(follows).astype(int) * 3)
        recommendations = recommendations[recommendations["match_score"] > 0]
        recommendations = recommendations.sort_values(["match_score", "event_date"], ascending=[False, True])
        st.caption("Rule-based recommendations: followed clubs rank first; matching categories also count. No behavioral tracking or model training.")
        st.write(f"**{len(recommendations)} matching upcoming events**")
        if recommendations.empty: st.warning("No upcoming matches in this limited demo dataset. Try another interest or switch to Browse.")
        for idx, ev in recommendations.head(15).iterrows(): show_event(ev, f"rec_{idx}")

with about:
    st.subheader("Why build this?")
    survey = load_survey()
    missed_rate = survey["missed_event"].eq("Yes").mean()
    missed = survey[survey["missed_event"].eq("Yes")]
    discovery_rate = missed["reason_missed"].isin(["Didn't know it was happening", "Found out too late"]).mean()
    satisfaction = survey["discovery_satisfaction"].mean()
    m1, m2, m3 = st.columns(3)
    m1.metric("Missed an event", f"{missed_rate:.1%}")
    m2.metric("Missed due to discovery/timing", f"{discovery_rate:.1%}")
    m3.metric("Discovery satisfaction", f"{satisfaction:.2f} / 5")
    st.caption("Baseline figures are calculated from the synthetic, deduplicated workshop survey; not verified real-world UCSD metrics.")
    st.write("**Proposed pilot targets (by Week 10)**: missed-event rate below 50%; mean discovery satisfaction above 3.0/5.")
    st.write("**How to evaluate:** survey pilot participants before use and after the pilot with the same questions; also track aggregated search-to-event-detail and calendar-download counts after consent/privacy review.")
    st.warning("**Known gaps:** no original platform links, true event duration, organizer verification, live ingestion, user accounts, or server-scheduled reminders. Conflicting start times were resolved by source ranking and are flagged for verification.")
    st.caption("Data pipeline: Workshop 1 notebook Part 6 → events_clean.csv + survey_clean.csv → this Streamlit site.")
