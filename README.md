# Campus Event Hub — v4

A student-facing Streamlit prototype built from the DataWorks workshop's synthetic event dataset. **My Hub is the default/first page**. Anyone can browse event listings and save events temporarily. With a configured Supabase project, a verified `@ucsd.edu` email account can sign in, save events persistently, and edit an optional profile.

## What's working / what's planned

| Function | Status |
|---|---|
| Homepage / My Hub first | Implemented |
| Public Explore Events and Explore Clubs | Implemented |
| Search, filters, event details, pagination | Implemented |
| Source link icon if a valid HTTP(S) URL exists | Implemented (sample CSV has no URLs) |
| Guest saved events | Implemented (temporary Streamlit session state) |
| Passwordless @ucsd.edu email OTP | Code implemented; requires Supabase + real email delivery setup |
| Persistent, per-account saved events | Code + SQL/RLS implemented; requires configured Supabase |
| Optional display name, class standing, major | Code + SQL/RLS implemented; requires configured Supabase |
| Default and per-event reminder choice | Preference storage implemented; requires configured Supabase |
| Automatic email reminder delivery | **Not implemented; no emails are sent on event dates** |
| Current student enrollment verification | **Not implemented** (email ownership ≠ current enrollment) |

**Reminder choices:** I don't want a reminder (the default); 24 hours before; 3 hours before; 1 hour before. These are **stored settings only**, not an active email notification service.

The dataset is synthetic workshop data, not verified UCSD announcements. Do not present the listings as real events. No live event data, official source URLs, or official UCSD login integrations are included. Store this disclosure in any user-test briefing and consulting presentation even though the student-facing homepage isn't cluttered with a demo-data banner.

## 1. Run locally

From the extracted `campus_event_hub_v4` directory:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Before configuring Supabase, the public pages and temporary guest saves still work. My Hub shows an honest configuration notice; it does not simulate authentication.

## 2. Configure real UCSD email authentication + database

### 2.1 Create a Supabase project

Create a project at https://supabase.com/dashboard. Under **Project Settings → API / Connect**, copy the **Project URL** and **publishable/anon key**. Do NOT use a **secret** or **service_role** key in Streamlit.

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and replace the placeholders:

```toml
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_ANON_KEY = "YOUR-PUBLISHABLE-OR-ANON-KEY"
```

`.streamlit/secrets.toml` is gitignored. In Streamlit Community Cloud, paste the same values into the app's **Secrets** settings. Do not publish token values in screenshots, GitHub, or a team chat.

### 2.2 Create and secure the tables

Run the entire contents of [`supabase/schema.sql`](supabase/schema.sql) in the Supabase **SQL Editor**. This creates:

- `profiles`: user ID, optional name/class/major, default reminder preference
- `saved_events`: one record per user and event, with per-event reminder preference
- RLS policies: users can read/write only their own records, and only with a UCSD-domain email claim
- A **Before User Created hook** function that can reject non-UCSD signups server-side

**Required security configuration:** In **Authentication → Hooks → Before User Created**, enable the Postgres function `public.restrict_ucsd_signup`. The app also checks the domain locally, but the hook is necessary to block signup attempts that bypass the Streamlit form. RLS is separately enabled for every personal-data table. Do not disable RLS.

Keep **Confirm email enabled** under Authentication's email provider settings. Do not turn it off to bypass delivery configuration.

### 2.3 Turn sign-in emails into one-time codes

Under **Authentication → Email Templates**, change both relevant templates (**Magic Link / OTP** and **Confirm signup**) so the message contains the raw OTP token instead of only the confirmation URL, e.g.:

```html
<h2>Your Campus Event Hub verification code</h2>
<p>Enter this code in the website: <strong>{{ .Token }}</strong></p>
```

This works with `sign_in_with_otp()` and `verify_otp(..., type='email')` in `account_store.py`. Do not include a verification code in logs.

### 2.4 Set up email sending for real test users

Supabase's hosted default SMTP service is for limited testing and generally sends only to project-team-authorized email addresses, with very low rate limits. To test with other student addresses, configure an approved **custom SMTP provider** or Supabase's **Send Email hook** in Authentication settings. Verification emails are sent by **Supabase Auth**, not by the app itself.

For an initial test, use a couple of your own/team-controlled `@ucsd.edu` email addresses; don't invite random students before login and privacy testing is completed.

### 2.5 Verify end-to-end

1. Run the app. It should open to **My Hub** automatically.
2. Browse as a guest, save one event, and confirm it appears in My Hub temporarily.
3. Enter a valid `@ucsd.edu` address; request a code. Retrieve it from that account's inbox.
4. Enter the code to sign in. My Hub should show the verified email.
5. Choose **Import guest saves** if applicable, or save a new event through Explore Events.
6. Open **My Hub → My Events** and verify that the event is listed.
7. Save a per-event reminder choice (including **I don't want a reminder**).
8. Open **My Profile**; optionally enter your name, class standing, or major. Save.
9. Open **Notification Settings** and choose a default reminder for **new** saves.
10. Sign out, sign back in from a new session, and confirm saved events, profile, and settings remain.
11. With a second account, verify that the first account's records are **not visible or editable**. Test RLS directly before any public deployment.
12. Try a non-UCSD address in the app; it must be rejected before an OTP request. Test the **server-side Before User Created hook** independently too.

For both login and RLS, a live Supabase project is needed for end-to-end verification; the included local tests mock network/database operations.

## 3. How preferences work

- **My Hub opens first.** Public browsing is available at all times; login is optional.
- When logged out, saved events are only in `st.session_state`. They disappear when that browser session ends.
- When signed in, saved events are stored in the `saved_events` database table under the authenticated user's ID, protected by RLS.
- Optional **My Profile** fields are not needed at registration and may be left empty.
- **Notification Settings** defines the default reminder preference for **newly saved events**.
- **My Events** lets a signed-in user override the preference for any saved event.
- **No reminder** is the default. Selecting 24/3/1 hours is a stored future delivery preference, not proof an email is scheduled.
- Auth tokens live in the current **Streamlit server session**. A browser refresh/reconnect or app restart may require signing in again. The database records themselves survive re-login; this prototype does not implement durable browser cookies.

## 4. Architecture

```text
app.py                   Streamlit interface + My Hub first navigation
account_store.py         Supabase OTP + profile + saved events CRUD
 event_utils.py           Load, search, filter, summarize events
 data/events_clean.csv    501 synthetic events; stable event IDs persisted to CSV
 supabase/schema.sql      Database definitions + RLS + optional signup hook
 .streamlit/secrets.toml.example  Template for local credentials
 tests/                   Unit/data-processing tests (not a live service test)
```

`event_id` values are now explicitly included in `events_clean.csv`, rather than recalculated every time a date/title changes. Preserve IDs for existing events when introducing real data. The CSV doesn't have real original announcement URLs, so link icons for those examples are disabled.

## 5. Future: actual email reminders

A later version needs a scheduled worker/email provider, cancellation, status tracking, opt-in/unsubscribe, event-time timezone handling (America/Los_Angeles), and update handling when an event time changes. Keep reminders off by default. Do not send automatic messages for synthetic events to anyone who has not explicitly consented to testing.

## 6. Tests

```bash
python -m pytest -q
```

The included tests validate deterministic data processing and account/database-call logic using fakes. They **do not** verify live OTP delivery, the Streamlit browser UI, or production RLS behavior. Those require configuration in §2 and a real test project.

## Documentation links

- Streamlit navigation: https://docs.streamlit.io/develop/api-reference/navigation/st.navigation
- Supabase Python OTP sign-in: https://supabase.com/docs/reference/python/auth-signinwithotp
- Supabase Python OTP verification: https://supabase.com/docs/reference/python/auth-verifyotp
- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase Before User Created hook: https://supabase.com/docs/guides/auth/auth-hooks/before-user-created-hook
- Supabase Email Templates: https://supabase.com/docs/guides/auth/auth-email-templates
- Supabase Auth SMTP: https://supabase.com/docs/guides/auth/auth-smtp
