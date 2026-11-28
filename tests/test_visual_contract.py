"""Static regression checks for the UCSD visual/entrypoint contract."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_student_portal_renamed_and_launcher_updated():
    assert (ROOT / 'student_portal.py').is_file()
    assert not (ROOT / 'website.py').exists()
    script = (ROOT / 'start_demo.sh').read_text()
    assert 'streamlit run student_portal.py' in script
    assert 'streamlit run website.py' not in script


def test_calendar_has_source_specific_contrast():
    from calendar_theme import UCSD_CALENDAR_CSS
    assert '.hub-event--legacy' in UCSD_CALENDAR_CSS
    assert '.hub-event--submitted' in UCSD_CALENDAR_CSS
    assert '-webkit-text-fill-color:#FFFFFF !important;' in UCSD_CALENDAR_CSS
    assert '-webkit-text-fill-color:#182B49 !important;' in UCSD_CALENDAR_CSS


def test_all_events_marks_event_types_and_limits_stack():
    source = (ROOT / 'client_portal.py').read_text()
    assert "'classNames':['hub-event--submitted' if submitted else 'hub-event--legacy']" in source
    assert "'eventMaxStack':3" in source
    assert "'slotEventOverlap':False" in source


def test_demo_marker_is_subtle_and_fields_use_light_contrast():
    source = (ROOT / 'portal_ui.py').read_text()
    assert 'Local demo · simulated account' in source
    assert 'LOCAL DEMO MODE' not in source
    assert 'background-color:#FFFFFF !important;' in source


def test_theme_is_explicitly_light():
    source = (ROOT / '.streamlit/config.toml').read_text()
    assert 'base = "light"' in source
    assert 'primaryColor = "#00629B"' in source
    assert 'textColor = "#182B49"' in source


def test_club_setup_is_conditional_and_time_zone_label_is_dst_safe():
    source=(ROOT / 'club_portal.py').read_text()
    assert "if not my_clubs:" in source
    assert "st.tabs(['Publish event','My events','Support tickets'])" in source
    assert "'Start time (PT)'" in source
    assert "'End time (PT)'" in source
    assert 'hub-managed-club__name' in source

def test_calendar_has_vertical_day_separators():
    from calendar_theme import UCSD_CALENDAR_CSS
    assert 'border-left:2px solid #B7CDE0' in UCSD_CALENDAR_CSS
    assert 'td.fc-timegrid-col:nth-child(even)' in UCSD_CALENDAR_CSS
