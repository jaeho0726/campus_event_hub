"""Regression checks for visible timed-grid separators and local demo onboarding."""
from pathlib import Path
from calendar_theme import UCSD_CALENDAR_CSS

ROOT = Path(__file__).resolve().parents[1]


def test_timed_day_lane_has_full_height_separator():
    # Header-only CSS would not satisfy the core issue reported by the user.
    assert '.fc-timegrid-cols .fc-timegrid-col-frame::before' in UCSD_CALENDAR_CSS
    assert 'top:0;' in UCSD_CALENDAR_CSS
    assert 'bottom:0;' in UCSD_CALENDAR_CSS
    assert 'background-color:#91B1CA;' in UCSD_CALENDAR_CSS
    assert 'pointer-events:none;' in UCSD_CALENDAR_CSS


def test_demo_new_officer_selector_is_local_only():
    src = (ROOT / 'portal_ui.py').read_text()
    section = src.split('def identity(store, role):')[1].split('if store is None:')[0]
    assert 'if is_demo():' in section
    assert "if role == 'club':" in section
    assert 'demo-new-officer-a' in section
    assert 'demo-new-officer-b' in section
    assert "st.selectbox('Test as (demo account)'" in section
    assert 'if not club_names.get(demo_id):' in section
    assert "st.session_state.pop(name, None)" in section


def test_first_time_officer_can_register_without_affecting_seed_account(monkeypatch, tmp_path):
    import mvp_store
    monkeypatch.setenv('MVP_DEMO_MODE', '1')
    monkeypatch.setattr(mvp_store, 'DB_PATH', tmp_path / 'demo.sqlite3')
    store = mvp_store.LocalStore()
    assert any(c['owner_id'] == 'demo-officer' for c in store.clubs())
    assert not any(c['owner_id'] == 'demo-new-officer-a' for c in store.clubs())
    club_id = store.create_club({
        'org_name': 'Fictional First-time Test Club',
        'category': 'Technology', 'org_size': 'Small',
        'description': 'A fictitious organization for the onboarding test.',
    }, 'demo-new-officer-a')
    assert any(c['id'] == club_id and c['owner_id'] == 'demo-new-officer-a' for c in store.clubs())
    assert not any(c['owner_id'] == 'demo-new-officer-b' for c in store.clubs())
