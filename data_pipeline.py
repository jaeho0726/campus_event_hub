"""Regenerate demo cleaned CSVs from events.csv and survey.csv.
Derived from the supplied Workshop 1 notebook Part 6.
"""
import pandas as pd

# Part 6 · Save clean starter data (just run it)
_raw = pd.read_csv('events.csv')
_CAT = {'general meeting': 'General Meeting', 'gbm': 'General Meeting', 'gen meeting': 'General Meeting',
        'social': 'Social', 'social event': 'Social', 'tech': 'Tech', 'technology': 'Tech',
        'cultural': 'Cultural', 'culture': 'Cultural', 'career/professional': 'Career/Professional',
        'career': 'Career/Professional', 'professional development': 'Career/Professional',
        'arts': 'Arts', 'art & design': 'Arts', 'sports/rec': 'Sports/Rec', 'recreation': 'Sports/Rec',
        'sports': 'Sports/Rec', 'service': 'Service', 'volunteering': 'Service', 'community service': 'Service'}
_TRUST = {'Campus calendar': 0, 'Club website': 1, 'Email newsletter': 2, 'Discord': 3, 'Instagram': 4, 'Flyer': 5}


def _clock(t):
    """'6:00 PM', '18:00', '6pm' -> '6:00 PM'."""
    t = str(t).strip().lower().replace(' ', '')
    pm, am = t.endswith('pm'), t.endswith('am')
    h, m = (t.replace('pm', '').replace('am', '').split(':') + ['0'])[:2]
    h, m = int(h), int(m)
    h = h + 12 if pm and h != 12 else (0 if am and h == 12 else h)
    return f"{(h % 12) or 12}:{m:02d} {'PM' if h >= 12 else 'AM'}"


_raw['category'] = _raw['category'].str.lower().str.strip().map(_CAT)
_raw['start_time'] = _raw['start_time'].map(_clock)
_raw['title_norm'] = (_raw['title'].str.lower().str.replace('[repost]', '', regex=False)
                      .str.replace('(reminder)', '', regex=False).str.replace('!', '', regex=False).str.strip())
_raw['event_date'] = pd.to_datetime(_raw['event_date'])
_raw['posted_date'] = pd.to_datetime(_raw['posted_date'])
_KEY = ['org_name', 'event_date', 'title_norm']
_grp = _raw.groupby(_KEY)
events_clean = (_raw.assign(_trust=_raw['posted_on'].map(_TRUST))
                .sort_values('_trust', kind='mergesort')
                .drop_duplicates(_KEY, keep='first')
                .set_index(_KEY)
                .assign(platforms=_grp['posted_on'].agg(lambda s: ', '.join(sorted(s.unique()))),
                        n_posts=_grp.size(),
                        time_conflict=_grp['start_time'].nunique() > 1,
                        first_posted=_grp['posted_date'].min())
                .reset_index())
events_clean['title'] = events_clean['title_norm'].str.title()
events_clean['notice_days'] = (events_clean['event_date'] - events_clean['first_posted']).dt.days
events_clean = (events_clean[['org_name', 'org_size', 'category', 'title', 'event_date', 'start_time', 'location',
                              'platforms', 'n_posts', 'time_conflict', 'first_posted', 'notice_days',
                              'rsvp_count', 'attendance', 'free_food']]
                .sort_values(['event_date', 'org_name']).reset_index(drop=True))
events_clean.to_csv('events_clean.csv', index=False)
pd.read_csv('survey.csv').drop_duplicates().to_csv('survey_clean.csv', index=False)
print(f'Saved events_clean.csv ({len(events_clean)} real events) and survey_clean.csv')
events_clean.head()