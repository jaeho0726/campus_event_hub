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


def test_demo_banner_and_fields_use_light_contrast():
    source = (ROOT / 'portal_ui.py').read_text()
    assert 'hub-demo-banner' in source
    assert 'st.markdown(\'<div class="hub-demo-banner">' in source
    assert 'background-color:#FFFFFF !important;' in source


def test_theme_is_explicitly_light():
    source = (ROOT / '.streamlit/config.toml').read_text()
    assert 'base = "light"' in source
    assert 'primaryColor = "#00629B"' in source
    assert 'textColor = "#182B49"' in source
