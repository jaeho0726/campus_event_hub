# Campus Event Hub — v1.4 patch

- Visible dividers through the **timed** week/day columns, not only the all-day header. Implemented on FullCalendar `fc-timegrid-col-frame` with full-height pseudo-elements in the iframe stylesheet.
- In local demo mode, Club Admin has a **Test as (demo account)** selector with `demo-officer` (seeded club), `demo-new-officer-a`, and `demo-new-officer-b` (initially no club).
- New officer accounts automatically see club registration; after creating a club they automatically see the management dashboard.
- On switching test identities, clears draft/current-club state so one officer's draft is not mistakenly used by another.
- Does not alter Supabase authorization, real sign-in, event publication, or ticket logic.
- Upgrade from v1.3: overwrite only `calendar_theme.py` and `portal_ui.py`; keep your SQLite demo data and secrets.
- The calendar CSS requires verification in a local Streamlit browser: package-based UI testing was not available in the artifact environment.
