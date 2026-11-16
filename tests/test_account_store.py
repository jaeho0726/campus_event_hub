"""Unit tests for account helpers, using a fake local database.

These do not replace live Supabase auth, RLS, or email-delivery testing.
"""
from types import SimpleNamespace
import pytest

from account_store import (
    REMINDER_OPTIONS, add_saved, format_reminder, get_profile,
    get_verified_user, is_ucsd_email, list_saved,
    remove_saved, save_profile, send_login_code, update_reminder,
)


class Query:
    def __init__(self, store, table):
        self.store, self.table = store, table
        self.action = 'select'
        self.filters = []
        self.payload = None
        self.columns = None
        self.max_rows = None

    def select(self, columns):
        self.action = 'select'
        self.columns = columns.split(', ')
        return self

    def eq(self, col, value):
        self.filters.append((col, value))
        return self

    def limit(self, count):
        self.max_rows = count
        return self

    def upsert(self, payload, on_conflict=None):
        self.action = 'upsert'
        self.payload = dict(payload)
        self.conflict = tuple(on_conflict.split(','))
        return self

    def update(self, payload):
        self.action = 'update'
        self.payload = dict(payload)
        return self

    def delete(self):
        self.action = 'delete'
        return self

    def execute(self):
        data = self.store[self.table]
        matches = [row for row in data
                   if all(row.get(k) == v for k, v in self.filters)]
        if self.action == 'select':
            rows = matches[:self.max_rows] if self.max_rows is not None else matches
            if self.columns:
                rows = [{k: row.get(k) for k in self.columns} for row in rows]
            return SimpleNamespace(data=rows)
        if self.action == 'upsert':
            found = next((row for row in data if all(
                row.get(k) == self.payload[k] for k in self.conflict)), None)
            if found is None:
                data.append(dict(self.payload))
            else:
                found.update(self.payload)
        elif self.action == 'delete':
            for row in matches:
                data.remove(row)
        elif self.action == 'update':
            for row in matches:
                row.update(self.payload)
        return SimpleNamespace(data=[])


class FakeClient:
    def __init__(self):
        self.db = {'profiles': [], 'saved_events': []}

    def table(self, name):
        return Query(self.db, name)


def test_email_validation():
    assert is_ucsd_email('student@ucsd.edu')
    assert is_ucsd_email('Student@UCSD.EDU ')
    for invalid in ['student@gmail.com', 'student@ucsd.edu.evil.com',
                    'student@sub.ucsd.edu', 'student@@ucsd.edu', '', 'ucsd.edu']:
        assert not is_ucsd_email(invalid)


def test_reminder_choices():
    assert list(REMINDER_OPTIONS.values()) == [None, 24, 3, 1]
    assert format_reminder(None) == "I don't want a reminder"
    assert format_reminder(3) == '3 hours before'


def test_saved_events_are_separated_by_account():
    c = FakeClient()
    add_saved(c, 'user-a', 'event-1', 24)
    add_saved(c, 'user-b', 'event-2', None)
    assert list_saved(c, 'user-a') == {'event-1': 24}
    assert list_saved(c, 'user-b') == {'event-2': None}
    update_reminder(c, 'user-a', 'event-1', 1)
    assert list_saved(c, 'user-a') == {'event-1': 1}
    assert list_saved(c, 'user-b') == {'event-2': None}
    remove_saved(c, 'user-a', 'event-1')
    assert list_saved(c, 'user-a') == {}
    assert list_saved(c, 'user-b') == {'event-2': None}


def test_updating_default_does_not_erase_optional_profile():
    c = FakeClient()
    save_profile(c, 'abc', display_name='Student', class_standing='Second-year', major='Math')
    save_profile(c, 'abc', default_reminder_hours=24,
                 fields=('default_reminder_hours',))
    profile = get_profile(c, 'abc')
    assert profile['display_name'] == 'Student'
    assert profile['class_standing'] == 'Second-year'
    assert profile['major'] == 'Math'
    assert profile['default_reminder_hours'] == 24


def test_invalid_reminder_is_rejected():
    c = FakeClient()
    with pytest.raises(ValueError):
        add_saved(c, 'abc', 'event', 99)
    with pytest.raises(ValueError):
        update_reminder(c, 'abc', 'event', 2)


def test_otp_request_rejects_non_ucsd_before_network_call():
    class FakeAuth:
        def __init__(self):
            self.sent = []
        def sign_in_with_otp(self, payload):
            self.sent.append(payload)
    client = SimpleNamespace(auth=FakeAuth())
    with pytest.raises(ValueError):
        send_login_code(client, 'other@gmail.com')
    assert client.auth.sent == []
    send_login_code(client, ' STudent@ucsd.edu ')
    assert client.auth.sent[0]['email'] == 'student@ucsd.edu'


def test_server_fetched_user_is_verified_for_domain():
    class FakeAuth:
        def __init__(self, email):
            self.email = email
        def get_user(self):
            return SimpleNamespace(user=SimpleNamespace(id='abc', email=self.email))
    assert get_verified_user(SimpleNamespace(auth=FakeAuth('student@ucsd.edu'))) == {
        'id': 'abc', 'email': 'student@ucsd.edu'}
    assert get_verified_user(SimpleNamespace(auth=FakeAuth('nonucsd@gmail.com'))) is None
