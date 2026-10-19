import json
import time

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend import main, storage
from backend.storage import WorkspaceStore, WorkspaceConflict, workspaces
from sqlalchemy import select


def payload():
    return {'frames': main.sample(), 'source': 'Uploaded Data', 'version': 'test-data', 'history': []}


def test_data_and_chat_survive_independent_instances_and_restart(tmp_path):
    url = 'sqlite:///' + str(tmp_path / 'shared.sqlite3')
    one, two = WorkspaceStore(url), WorkspaceStore(url)
    state = one.create('secret-browser-token', payload())
    state['history'] = [{'role': 'user', 'content': 'What is revenue?'}]
    one.save(state)
    restored = two.load('secret-browser-token')
    assert restored['history'] == state['history']
    for first, second in zip(state['frames'], restored['frames']):
        pd.testing.assert_frame_equal(first, second, check_dtype=False)
    one.engine.dispose()
    restarted = WorkspaceStore(url)
    assert restarted.load('secret-browser-token')['source'] == 'Uploaded Data'
    assert restarted.load('different-browser-token') is None
    with restarted.engine.connect() as connection:
        key = connection.execute(select(workspaces.c.id)).scalar_one()
        assert key != 'secret-browser-token' and len(key) == 64
    two.engine.dispose()
    restarted.engine.dispose()


def test_stale_updates_cannot_overwrite_new_data_or_resurrect_chat(tmp_path):
    store = WorkspaceStore('sqlite:///' + str(tmp_path / 'conflict.sqlite3'))
    store.create('token', payload())
    first, stale = store.load('token'), store.load('token')
    first['history'] = []
    first['version'] = 'new-data'
    store.save(first)
    stale['history'] = [{'role': 'user', 'content': 'Old data question'}]
    with pytest.raises(WorkspaceConflict):
        store.save(stale)
    assert store.load('token')['version'] == 'new-data'
    assert store.load('token')['history'] == []
    store.engine.dispose()


def test_expiry_deletes_payload_and_invalidates_updates(tmp_path, monkeypatch):
    store = WorkspaceStore('sqlite:///' + str(tmp_path / 'expiry.sqlite3'), ttl=10)
    now = time.time()
    monkeypatch.setattr(storage.time, 'time', lambda: now)
    state = store.create('token', payload())
    monkeypatch.setattr(storage.time, 'time', lambda: now+11)
    assert store.load('token') is None
    with pytest.raises(WorkspaceConflict):
        store.save(state)
    store.engine.dispose()


def test_vercel_requires_shared_database_instead_of_local_fallback(monkeypatch):
    storage.get_store.cache_clear()
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(RuntimeError, match='DATABASE_URL'):
        storage.get_store()
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///ignored.sqlite3')
    with pytest.raises(RuntimeError, match='shared PostgreSQL'):
        storage.get_store()
    storage.get_store.cache_clear()


def test_api_continues_uploaded_workspace_on_another_server(tmp_path, monkeypatch):
    url = 'sqlite:///' + str(tmp_path / 'servers.sqlite3')
    first, second = WorkspaceStore(url), WorkspaceStore(url)
    monkeypatch.setattr(main, 'get_store', lambda: first)
    with TestClient(main.app) as client:
        client.get('/api/dashboard')
        token = client.cookies.get('finance_session')
        state = first.load(token)
        state.update(source='Uploaded Data', history=[{'role': 'user', 'content': 'Saved question'}], history_currency='AED')
        first.save(state)
        monkeypatch.setattr(main, 'get_store', lambda: second)
        assert client.get('/api/dashboard').json()['source'] == 'Uploaded Data'
        assert client.get('/api/chat').json()['messages'][0]['content'] == 'Saved question'
    first.engine.dispose()
    second.engine.dispose()


def test_vercel_configuration_points_to_api_and_excludes_secrets():
    config = json.loads((main.ROOT / 'vercel.json').read_text())
    assert config['framework'] == 'fastapi'
    assert 'backend/main.py' in config['functions']
    assert '.streamlit/**' in config['functions']['backend/main.py']['excludeFiles']
