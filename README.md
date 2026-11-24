# Campus Event Hub — Three-Portal MVP

A **working prototype** of the UCSD-themed Campus Event Hub, based on the most recent teammate-updated `student_portal.py` with UCSD Navy saved buttons.

The three Streamlit entrypoints share an event/ticket store:

| Portal | Run this file | Local URL | Features |
| --- | --- | --- | --- |
| Student | `student_portal.py` | `http://localhost:8501` | Browse CSV + new club events; save events/clubs; event-specific and general tickets; existing My Hub and calendar |
| Club officer | `club_portal.py` | `http://localhost:8502` | Self-register new clubs; publish/edit/cancel own events; nonblocking conflict warnings; handle own club tickets |
| Client administrator | `client_portal.py` | `http://localhost:8503` | Read-only all-events calendar; filters; location-overlap monitor; ticket queue; basic operational counters |

## Quickest way to demo all three (no SMTP needed)

Run these commands **from this project folder** in three terminals (or on macOS use `bash start_demo.sh` after installing dependencies). The demo uses SQLite on your machine (`data/campus_event_hub_demo.sqlite3`) so all three Streamlit servers see the same updates.

```bash
python3 -m pip install -r requirements.txt

# Terminal 1 — student
MVP_DEMO_MODE=1 python3 -m streamlit run student_portal.py --server.port 8501

# Terminal 2 — club officer
MVP_DEMO_MODE=1 python3 -m streamlit run club_portal.py --server.port 8502

# Terminal 3 — client admin
MVP_DEMO_MODE=1 python3 -m streamlit run client_portal.py --server.port 8503
```

On Windows PowerShell set `$env:MVP_DEMO_MODE="1"` before running each command.

**Demo identities are simulated** (`demo-student`, `demo-officer`, `demo-client`). No OTP, actual account ownership, or real access control is provided in demo mode. **Never deploy with `MVP_DEMO_MODE=1`, including to public Streamlit Cloud.** The seed club **Triton Demo Makers** is fictional and owned by the demo officer. The 60 workshop clubs remain existing, read-only names and cannot be claimed through self-registration. All legacy events from `events_clean.csv` are **synthetic workshop records**, not confirmed real UCSD events.

### End-to-end test

1. Open Club Admin (8502), go to **Publish event**, select Triton Demo Makers, and create a future event with start and end times. If another club-submitted event overlaps, the app displays an informational warning and a **Publish anyway** option. There is **no client approval step**.
2. Refresh Student (8501). The newly published event appears in **Explore Events** and in the calendar if saved. You can file an event-specific ticket through **Event details** or submit a general ticket through **Support**.
3. Revisit Club Admin (8502) → **Support tickets**. Content tickets attached to your club appear there. Update their status after correcting the event.
4. Refresh Client Admin (8503). See all events (including synthetic baseline data) in **All-events calendar**, and inspect ticket status in **Tickets**.
5. To reset local demo data, stop all servers and delete `data/campus_event_hub_demo.sqlite3` (and any associated `-wal`/`-shm` files). Next launch recreates the seed club.

## Live Supabase setup (after SMTP/OTP is ready)

1. Create a Supabase project and copy your **project URL** and **publishable/anon key** into `.streamlit/secrets.toml` using `.streamlit/secrets.toml.example`. Never copy a `service_role` or `sb_secret_...` key into the Streamlit app. Do not commit `secrets.toml`.
2. In Supabase SQL Editor, run **`database/schema.sql`** if you have not run it previously. This file already includes the previous saved-club migration. If your existing project is already configured, the file is idempotent for the standard user tables.
3. Run **`database/mvp_portals.sql`**, then **`database/mvp_reserved_clubs.sql`**, in that exact order. The second script reserves all 60 workshop club names in the database.
4. Configure authentication email OTP and custom SMTP (as discussed earlier). The email templates need `{{ .Token }}` to send numeric codes. Leave `MVP_DEMO_MODE` unset or `0` in your hosting environment. Guest event browsing is available; writing a club, event, or ticket requires verified UCSD sign-in.
5. To grant a specific person Client Admin access, sign in once with their UCSD email, find their `auth.users.id` in Supabase Authentication → Users, then run in **SQL Editor**, replacing the placeholder with that person's real UUID:

   ```sql
   insert into public.hub_admins(user_id) values ('REAL-USER-UUID');
   ```

   Never expose a public Client Admin sign-up form. Club admin permission for the MVP comes from **creating a new club**; only its creator can modify that club's events. This is self-registration, **not** official UCSD officer verification. Existing CSV clubs cannot be claimed automatically.
6. Launch the three apps as in the quickstart above, but **omit `MVP_DEMO_MODE=1`**. If deploying them separately, configure the *same* Supabase URL and publishable key for all three.

### What is enforced in live mode

- Row Level Security restricts event creation/updates to the creator of the specific club, and restricts client-admin privileges to a separately provisioned list. The client has no event-editing API permission.
- Ticket readers are the reporter, responsible club owner (for routed event-data tickets), and client admins. Only club owners and client admins can change ticket status.
- Database-level club-name uniqueness is case-insensitive and normalized for repeated whitespace. The reserved-name seed blocks self-claiming workshop clubs.
- Public student reads only published hub events. Club cancellations hide an event from the public feed.

**Security testing:** Live RLS policies require separate integration testing in your own Supabase project before public use. This deliverable was tested locally, **not** against your Supabase account. Do not publicly launch self-registration without adding rate limiting, abuse protection, stronger officer identity checks, and account recovery rules.


## Theme and contrast fixes (UCSD refresh)

The three portals now share UCSD Navy (`#182B49`), Blue (`#00629B`), and
Yellow (`#FFCD00`) on white or pale-blue backgrounds. The admin portals use
`portal_ui.style_portal()` to keep labels, form fields, cards, and buttons
readable; `.streamlit/config.toml` declares a light base theme.

**Calendar-specific fix:** the calendar is rendered inside its own iframe,
so Streamlit's outer CSS does not apply to it. Both the Student saved-event
calendar and Client all-events calendar now use the separate
`calendar_theme.UCSD_CALENDAR_CSS` passed as `custom_css`. Calendar day cells
are white, headers are pale blue, primary controls are UCSD blue, and
submitted/legacy events use navy/blue rather than gold or brown.

After replacing files, stop all three Streamlit servers and run
`bash start_demo.sh` again. If a tab still looks dark, hard-refresh the tab
(`Cmd+Shift+R` on macOS) so the embedded calendar stylesheet reloads.
This is a style-only change; no event, ticket, permission, or storage logic
was intentionally changed. Browser-level visual verification is still needed.

## Intentional MVP limitations

- **Legacy workshop data:** 501 synthetic CSV events are not actual real-time listings. They lack end times and room identifiers, so they cannot be used for reliable time/room conflict detection. Calendar slots for these show their recorded *start* only; if the calendar supplies a default visual duration, it is **not** a known event duration.
- **Location warnings:** Only compare two club-submitted events on the same day with known end times. Same-time, same-building, and same-room warnings are **nonblocking** and **do not establish room availability or booking rights**.
- **Tickets:** Routing is immediate in the database. Event-info reports linked to an owned club go to that owner. Unlinked/legacy reports go to the client queue; technical reports are tagged for developers but **no automatic email, GitHub integration, or software auto-repair is implemented**. Interns monitor unresolved exceptions. Do not enter sensitive personal information into ticket descriptions.
- **Reminders:** The student website retains existing preferences, but email reminder sending is **not yet implemented**.
- **Multi-officer delegation:** One creator per newly registered club in this MVP. Inviting extra club officers and reclaiming old CSV clubs are deferred.
- **Maintenance:** The two-hour weekly operations budget is a **design target**, not an observed outcome. Measure real workload during pilot usage.
- **Outcome measure:** The proposed 30% faster median event-discovery time is a **target**, not a measured result. See `usability_test_template.csv` to record participant trials and calculate actual results; successful/correct searches must also be tracked.

## Project files

```text
student_portal.py                    Student portal (existing design + feed/tickets)
club_portal.py                Club self-service portal
client_portal.py              Client monitoring portal
mvp_store.py                  Shared SQLite demo / Supabase storage API
portal_ui.py                  Login, design and ticket widgets
start_demo.sh                 Launch all 3 local demos with one command (Mac/Linux)
conflicts.py                  Pure overlap detection + form validation
account_store.py              Existing Supabase authentication and saved items
event_utils.py                Existing CSV parsing, filtering, club summaries
requirements.txt              Python dependencies
database/schema.sql           Existing accounts/bookmarks schema
database/mvp_portals.sql      NEW database tables, permissions and RLS
database/mvp_reserved_clubs.sql  NEW 60 existing club names
usability_test_template.csv   Empty template for measuring discovery time
.streamlit/config.toml        UCSD color theme
.streamlit/secrets.toml.example   Config template, no credentials
```

## Metric for the DataWorks showcase

Suggested primary outcome is **median seconds to correctly find a specified event** through existing fragmented discovery channels vs. Campus Event Hub. Use comparable tasks, counterbalance which interface is tested first, and measure task correctness. For correct trials, percent reduction = `(baseline_median - hub_median) / baseline_median * 100`; also report failure rates. Sample results are **not prefilled** as actual evidence.

Supabase RLS reference: https://supabase.com/docs/guides/database/postgres/row-level-security

Dependency note: Browser-level UI testing was unavailable in the artifact build environment because Streamlit was not installed and package downloads were blocked. All existing/new Python unit tests passed and all source files passed syntax compilation; please run the local three-portal smoke test above before presenting.

Streamlit multipage reference: https://docs.streamlit.io/develop/concepts/multipage-apps/overview

## Readability update v1.1

- Student entrypoint has been **renamed from `website.py` to `student_portal.py`**. The start script and all README commands use the new name; there is no duplicate `website.py`.
- Admin form inputs, BaseWeb dropdowns and the local-demo notice use explicit light backgrounds and high-contrast navy text even if a browser retains dark-mode preferences.
- Calendar club submissions are **navy cards with white text and a yellow stripe**; synthetic workshop records are **light-blue cards with navy text and a blue border**. Cards have spacing and borders, and crowded week views use a `+more` link instead of squeezing unlimited entries onto tiny slivers.
- This update does not change event authorization, database schema, tickets, or event publishing.
- After replacing code, stop all three running servers (Ctrl+C), then run `bash start_demo.sh`, followed by a hard refresh (Cmd+Shift+R). If you previously deployed `website.py` as an entrypoint, change that deployment's entrypoint to `student_portal.py`.
