"""Startup concurrency and idempotence regression tests."""
from concurrent.futures import ThreadPoolExecutor
import sqlite3

import mvp_store


def test_parallel_portal_startup_does_not_duplicate_seed(tmp_path, monkeypatch):
    monkeypatch.setenv('MVP_DEMO_MODE', '1')
    monkeypatch.setattr(mvp_store, 'DB_PATH', tmp_path / 'concurrent.sqlite3')
    with ThreadPoolExecutor(max_workers=9) as pool:
        results = list(pool.map(lambda _: mvp_store.LocalStore().clubs(), range(9)))
    assert all(len(rows) == 1 for rows in results)
    with sqlite3.connect(mvp_store.DB_PATH) as db:
        assert db.execute('select count(*) from clubs').fetchone()[0] == 1
        assert db.execute('select count(*) from published_events').fetchone()[0] == 1


def test_repeat_startup_preserves_user_content(tmp_path, monkeypatch):
    monkeypatch.setenv('MVP_DEMO_MODE', '1')
    monkeypatch.setattr(mvp_store, 'DB_PATH', tmp_path / 'repeat.sqlite3')
    store = mvp_store.LocalStore()
    club_id = store.create_club({
        'org_name':'Independent Test Club', 'category':'Academic',
        'org_size':'Small','description':'Created by test account',
    }, 'test-owner')
    for _ in range(5):
        mvp_store.LocalStore()
    assert any(c['id'] == club_id for c in mvp_store.LocalStore().clubs())
    with sqlite3.connect(mvp_store.DB_PATH) as db:
        assert db.execute('select count(*) from published_events').fetchone()[0] == 1


def test_client_dashboard_has_no_operations_panel():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / 'client_portal.py').read_text()
    assert 'Maintenance overview' not in src
    assert 'Weekly target: operate' not in src
    assert "'All-events calendar','Tickets','Conflict monitoring'" in src
