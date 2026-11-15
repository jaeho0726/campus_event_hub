# Campus Event Hub — DataWorks v3.3

Student-facing Streamlit prototype centered on **event discovery**.

## Run

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Run from the directory containing `app.py`. In Streamlit, try searching **Python**, selecting a category, and opening an event. The **Upcoming only** filter defaults to on; turn it off if you want to see all example events.

## What's included

- Homepage with student-centered copy
- Explore events: search by event/club/location, filter by category and date, event details
- Explore clubs: find clubs and see their event listings
- Saved events: an in-memory list using `st.session_state` (clears when the session ends)
- Loaded directly from `data/events_clean.csv`, deduplicated by the workshop pipeline

## What changed

Removed the prominent dataset banner, Evidence & Pilot tab, survey KPI cards, the *I'm interested in* selector, the For You recommendations tab, and following clubs. Those belong in consulting materials or a later feature phase.

## Data provenance and safety

**All 501 listings are synthetic workshop examples, not real UCSD announcements.** Do not publish them as actual campus events or use their times/locations to make real plans. In any public demo or pilot, clearly identify the sample listings as examples (e.g., in accompanying presentation or tester instructions). Some event times were resolved from conflicting source entries, and there are no verified source URLs. An event-details popover notes these limitations.

To move to real events, replace `data/events_clean.csv` with a file following the same schema, after confirming organizer accuracy and permissions. Add a verified `source_url`, proper event durations, and event updates to the pipeline before treating the output as authoritative.

## Authentication and reminders — future development

**Not implemented.** Entering `@ucsd.edu` is not identity verification. A real login requires an approved identity provider and a verified address, preferably institutional SSO (institutional authorization may be needed). A real emailed reminder requires users' opt-in, a database, a scheduler, and a transactional email integration; do not store passwords or SMTP secrets in this repository.

Consider allowing public browsing and requiring sign-in for cross-session saved events and reminders. This first version has no student account storage, email delivery, or tracking.

## Structure

- `app.py`: Streamlit pages and UI
- `event_utils.py`: Data loading and filtering
- `data/events_clean.csv`: Sample cleaned dataset
- `tests/test_event_utils.py`: Basic data and filter tests (run with `python -m unittest discover -s tests`)

## v3.1 card change

The source link control is now a **🔗 icon in the top-right of every event card**, next to its category. Verified `http://` or `https://` URLs open the external announcement; missing or invalid URLs show a disabled icon with a “Link not provided” tooltip and a note in Event details. Only **Save event** and **Event details** remain in the bottom action row.

## v3.2 update
The homepage hero now displays **Campus Event Hub** as the main H1 title and the campus discovery tagline as a secondary H2 heading, with responsive typography for smaller screens.

## v3.3 update
Removed icons from the three top navigation tabs. The tabs now read **Explore events**, **Explore clubs**, and **Saved events**, with no other UI or feature changes.
