"""Pure event validation and potential-overlap checks (not room booking)."""
from datetime import date, datetime, time
import re


def normalize_name(value: str) -> str:
    return ' '.join(value.strip().casefold().split())


def validate_event(values: dict) -> None:
    required = ('title', 'event_date', 'start_time', 'end_time', 'building', 'category', 'description')
    for key in required:
        if not str(values.get(key, '')).strip():
            raise ValueError(f'{key.replace("_", " ").title()} is required.')
    day = date.fromisoformat(str(values['event_date']))
    start = time.fromisoformat(str(values['start_time']))
    end = time.fromisoformat(str(values['end_time']))
    if end <= start:
        raise ValueError('End time must be later than start time (overnight events are not supported yet).')
    if len(str(values['title'])) > 150 or len(str(values['description'])) > 2000:
        raise ValueError('Event title or description is too long.')
    if day < date.today():
        raise ValueError('Event date cannot be in the past.')
    url = str(values.get('external_url') or '').strip()
    if url and not re.fullmatch(r'https?://[^\s/]+(?:/[^\s]*)?', url, flags=re.I):
        raise ValueError('Announcement URL must start with https:// or http://.')


def overlap_minutes(a_start, a_end, b_start, b_end) -> int:
    """Time-only overlap for events on the same calendar day. Adjacent slots don't overlap."""
    def parse(x):
        return time.fromisoformat(str(x)[:8])
    s = max(parse(a_start), parse(b_start))
    e = min(parse(a_end), parse(b_end))
    dt = datetime.combine(date(2026, 1, 1), e) - datetime.combine(date(2026, 1, 1), s)
    return max(0, int(dt.total_seconds() // 60))


def conflict_warnings(proposed: dict, existing: list[dict], exclude_id=None) -> list[dict]:
    """Only confidently compare events with known end times; warnings never block publish."""
    warnings = []
    for event in existing:
        if str(event.get('id')) == str(exclude_id) or event.get('status', 'published') != 'published':
            continue
        if str(event.get('event_date')) != str(proposed['event_date']):
            continue
        if not event.get('end_time'):
            continue
        minutes = overlap_minutes(proposed['start_time'], proposed['end_time'],
                                  event['start_time'], event['end_time'])
        if not minutes:
            continue
        same_building = normalize_name(str(proposed.get('building') or '')) == normalize_name(str(event.get('building') or ''))
        a_room = normalize_name(str(proposed.get('room') or ''))
        b_room = normalize_name(str(event.get('room') or ''))
        if same_building and a_room and b_room and a_room == b_room:
            severity = 'same_room'
        elif same_building:
            severity = 'same_building'
        else:
            severity = 'same_time'
        warnings.append({'event': event, 'minutes': minutes, 'severity': severity})
    rank = {'same_room': 0, 'same_building': 1, 'same_time': 2}
    return sorted(warnings, key=lambda w: (rank[w['severity']], -w['minutes']))
