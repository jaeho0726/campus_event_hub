"""Data loading and filtering for the Campus Event Hub Streamlit MVP."""
from hashlib import sha1
from pathlib import Path
import pandas as pd


POSSIBLE_URL_COLUMNS = ['source_url', 'event_url', 'external_url', 'url', 'link']


def load_events(csv_path: str | Path) -> pd.DataFrame:
    """Load cleaned events, generating a stable ID for each unique event."""
    df = pd.read_csv(csv_path)
    required = {'org_name', 'category', 'title', 'event_date',
                'start_time', 'location', 'platforms'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required event columns: {sorted(missing)}")

    df['event_date'] = pd.to_datetime(df['event_date'], errors='coerce')
    df = df.dropna(subset=['event_date']).copy()
    for col in ['org_name', 'category', 'title', 'start_time', 'location', 'platforms']:
        df[col] = df[col].fillna('').astype(str)
    for col in ['time_conflict', 'free_food']:
        if col not in df:
            df[col] = False
        df[col] = df[col].astype(str).str.lower().eq('true')
    if 'org_size' not in df:
        df['org_size'] = ''

    url_col = next((col for col in POSSIBLE_URL_COLUMNS if col in df.columns), None)
    if url_col is None:
        df['external_url'] = ''
    else:
        df['external_url'] = df[url_col].fillna('').astype(str)

    # The cleaned workshop dataset has one row per real event.
    def make_id(row):
        key = '|'.join((row['org_name'].strip().casefold(),
                        row['event_date'].strftime('%Y-%m-%d'),
                        row['title'].strip().casefold()))
        return sha1(key.encode('utf-8')).hexdigest()[:16]

    if 'event_id' not in df.columns:
        df['event_id'] = df.apply(make_id, axis=1)
    df['event_id'] = df['event_id'].fillna('').astype(str).str.strip()
    if (df['event_id'] == '').any():
        raise ValueError('All events need a nonempty event_id.')
    if df['event_id'].duplicated().any():
        raise ValueError('The cleaned CSV contains duplicated event identities.')
    return df.sort_values(['event_date', 'start_time', 'title']).reset_index(drop=True)


def filter_events(events: pd.DataFrame, query: str = '', categories=None,
                  start_date=None, end_date=None, club: str | None = None) -> pd.DataFrame:
    """Filter events by search text, category, dates, and optional exact club name."""
    result = events
    if query.strip():
        cols = ['title', 'org_name', 'location', 'category']
        match = (result[cols].fillna('').astype(str)
                 .apply(lambda s: s.str.contains(query.strip(), case=False, regex=False))
                 .any(axis=1))
        result = result.loc[match]
    if categories:
        result = result[result['category'].isin(categories)]
    if club is not None:
        result = result[result['org_name'] == club]
    if start_date is not None:
        result = result[result['event_date'].dt.date >= start_date]
    if end_date is not None:
        result = result[result['event_date'].dt.date <= end_date]
    return result.sort_values(['event_date', 'start_time', 'title']).copy()



def build_club_summary(events: pd.DataFrame) -> pd.DataFrame:
    """One row per club; categories are inferred from its listed event types.

    These are not verified club descriptions or UCSD official classifications.
    'General Meeting' is omitted when a club has other, more informative tags.
    """
    import hashlib

    rows = []
    for name, group in events.groupby('org_name', sort=True):
        raw_tags = sorted(set(group['category'].dropna().astype(str)))
        specific_tags = [tag for tag in raw_tags if tag != 'General Meeting']
        tags = specific_tags or raw_tags
        sizes = group['org_size'].dropna().astype(str).str.strip().str.lower()
        size = sizes.mode().iloc[0] if not sizes.empty else 'unspecified'
        club_id = hashlib.sha1(name.strip().casefold().encode('utf-8')).hexdigest()[:16]
        rows.append({
            'club_id': club_id,
            'org_name': name,
            'org_size': size,
            'categories': ', '.join(tags),
            'category_tags': tuple(tags),
        })
    columns = ['club_id', 'org_name', 'org_size', 'categories', 'category_tags']
    return pd.DataFrame(rows, columns=columns).sort_values('org_name').reset_index(drop=True)


def filter_clubs(clubs: pd.DataFrame, search: str = '', categories=None, sizes=None) -> pd.DataFrame:
    """Filter the club directory by name, inferred event tags, and club size."""
    result = clubs
    if search.strip():
        result = result[result['org_name'].str.contains(search.strip(), case=False, regex=False)]
    if categories:
        chosen = set(categories)
        result = result[result['category_tags'].map(lambda tags: bool(chosen.intersection(tags)))]
    if sizes:
        chosen_sizes = {size.casefold() for size in sizes}
        result = result[result['org_size'].str.casefold().isin(chosen_sizes)]
    return result.sort_values('org_name').copy()
