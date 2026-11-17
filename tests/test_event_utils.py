import unittest
from pathlib import Path
from datetime import date
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from event_utils import load_events, filter_events, build_club_summary, filter_clubs

ROOT = Path(__file__).resolve().parents[1]

class TestEventUtils(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = load_events(ROOT / 'data' / 'events_clean.csv')

    def test_count_and_unique_ids(self):
        self.assertEqual(len(self.events), 501)
        self.assertTrue(self.events.event_id.is_unique)

    def test_text_search(self):
        results = filter_events(self.events, 'Python')
        self.assertGreater(len(results), 0)
        for _, row in results.iterrows():
            self.assertTrue(any('python' in str(row[c]).lower() for c in ['title','org_name','location','category']))

    def test_category(self):
        results = filter_events(self.events, categories=['Tech'])
        self.assertTrue((results.category == 'Tech').all())

    def test_date(self):
        results = filter_events(self.events, start_date=date(2026, 11, 1), end_date=date(2026, 11, 10))
        self.assertTrue((results.event_date.dt.date >= date(2026, 11, 1)).all())
        self.assertTrue((results.event_date.dt.date <= date(2026, 11, 10)).all())

    def test_exact_club(self):
        results = filter_events(self.events, club='AI Builders')
        self.assertTrue((results.org_name == 'AI Builders').all())

if __name__ == '__main__': unittest.main()


def test_club_directory_filter_and_stable_ids():
    clubs = build_club_summary(load_events(ROOT / 'data' / 'events_clean.csv'))
    assert len(clubs) == 60
    assert clubs.club_id.is_unique
    assert set(clubs.org_size) <= {'small', 'medium', 'large'}
    assert filter_clubs(clubs, search='ai builder').org_name.tolist() == ['AI Builders']
    tech = filter_clubs(clubs, categories=['Tech'])
    assert not tech.empty
    assert all('Tech' in tags for tags in tech.category_tags)
    small = filter_clubs(clubs, sizes=['Small'])
    assert not small.empty
    assert all(size == 'small' for size in small.org_size)
    combined = filter_clubs(clubs, categories=['Tech'], sizes=['Small'])
    assert all('Tech' in tags and size == 'small'
               for tags, size in zip(combined.category_tags, combined.org_size))
