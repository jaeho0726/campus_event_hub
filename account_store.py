"""UCSD email authentication and per-user Supabase data operations.

A Supabase client belongs to ONE Streamlit browser session; never cache it globally.
Always use Supabase's public/anon key with Row Level Security (RLS), never the
service-role key. This module does not send reminder emails.
"""
import re
from typing import Any

REMINDER_OPTIONS = {
    "I don't want a reminder": None,
    '24 hours before': 24,
    '3 hours before': 3,
    '1 hour before': 1,
}

CLASS_OPTIONS = [
    'Not specified', 'First-year', 'Second-year', 'Third-year',
    'Fourth-year', 'Transfer', 'Graduate', 'Other',
]


def is_ucsd_email(address: str) -> bool:
    """Check format before requesting a code; server still verifies ownership."""
    return bool(re.fullmatch(r'[a-zA-Z0-9._%+\-]+@ucsd\.edu', address.strip(), re.I))


def format_reminder(hours: int | None) -> str:
    for label, value in REMINDER_OPTIONS.items():
        if value == hours:
            return label
    return "I don't want a reminder"


def new_client(url: str, anon_key: str):
    """Create a session-isolated Supabase client (never cache_resource)."""
    from supabase import create_client
    return create_client(url, anon_key)


def send_login_code(client: Any, email: str) -> None:
    """Supabase OTP email template MUST contain {{ .Token }} to send a code."""
    email = email.strip().lower()
    if not is_ucsd_email(email):
        raise ValueError('Please enter a valid @ucsd.edu email address.')
    client.auth.sign_in_with_otp({'email': email, 'options': {'should_create_user': True}})


def verify_login_code(client: Any, email: str, code: str) -> dict:
    """Verify the OTP with Supabase, then retrieve the server-validated user."""
    email = email.strip().lower()
    if not is_ucsd_email(email):
        raise ValueError('Please enter a valid @ucsd.edu email address.')
    if not re.fullmatch(r'\d{6,8}', code.strip()):
        raise ValueError('Enter the numeric verification code from your email.')
    client.auth.verify_otp({'email': email, 'token': code.strip(), 'type': 'email'})
    verified = get_verified_user(client)
    if verified is None or verified['email'] != email:
        client.auth.sign_out()
        raise ValueError('The email address could not be verified.')
    return verified


def get_verified_user(client: Any) -> dict | None:
    """Read identity from Supabase Auth, not self-reported form values."""
    response = client.auth.get_user()
    user = getattr(response, 'user', None)
    if user is None or not is_ucsd_email(str(getattr(user, 'email', ''))):
        return None
    return {'id': str(user.id), 'email': str(user.email).strip().lower()}


def get_profile(client: Any, user_id: str) -> dict:
    rows = (client.table('profiles').select('user_id, display_name, class_standing, major, default_reminder_hours')
            .eq('user_id', user_id).limit(1).execute().data or [])
    return rows[0] if rows else {}


def save_profile(client: Any, user_id: str, *, display_name=None,
                 class_standing=None, major=None, default_reminder_hours=None,
                 fields: tuple[str, ...] = ('display_name', 'class_standing', 'major')) -> None:
    """Upsert only requested fields; don't clear other saved preferences."""
    values = {'display_name': display_name, 'class_standing': class_standing,
              'major': major, 'default_reminder_hours': default_reminder_hours}
    # Include existing fields so an upsert never clears unrelated profile choices.
    current = get_profile(client, user_id)
    payload = {'user_id': user_id}
    for field in ('display_name', 'class_standing', 'major', 'default_reminder_hours'):
        payload[field] = values[field] if field in fields else current.get(field)
    client.table('profiles').upsert(payload, on_conflict='user_id').execute()


def list_saved(client: Any, user_id: str) -> dict[str, int | None]:
    rows = (client.table('saved_events').select('event_id, reminder_hours')
            .eq('user_id', user_id).execute().data or [])
    return {str(row['event_id']): row.get('reminder_hours') for row in rows}


def add_saved(client: Any, user_id: str, event_id: str, reminder_hours=None) -> None:
    if reminder_hours not in (None, 1, 3, 24):
        raise ValueError('Unsupported reminder preference')
    payload = {'user_id': user_id, 'event_id': event_id, 'reminder_hours': reminder_hours}
    client.table('saved_events').upsert(payload, on_conflict='user_id,event_id').execute()


def remove_saved(client: Any, user_id: str, event_id: str) -> None:
    (client.table('saved_events').delete()
     .eq('user_id', user_id).eq('event_id', event_id).execute())


def update_reminder(client: Any, user_id: str, event_id: str, hours: int | None) -> None:
    if hours not in (None, 1, 3, 24):
        raise ValueError('Unsupported reminder preference')
    (client.table('saved_events').update({'reminder_hours': hours})
     .eq('user_id', user_id).eq('event_id', event_id).execute())
