from io import BytesIO
import json
from pathlib import Path

import pandas as pd
from pptx import Presentation
import pytest
from fastapi.testclient import TestClient

from backend import main


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, 'sessions', {})
    with TestClient(main.app) as client:
        yield client


def test_dashboard_comparison_and_period_filters(client):
    response = client.get('/api/dashboard')
    assert response.status_code == 200
    data = response.json()
    assert data['period'] == '2026-12'
    assert len(data['periods']) == 12
    assert {'Budget', 'Forecast', 'Variance vs Budget', 'Variance vs Forecast'}.issubset(data['comparison'][0])
    assert response.headers['cache-control'] == 'no-store'
    assert client.cookies.get('finance_session')
    assert 'HttpOnly' in response.headers['set-cookie']
    for grain, expected in [('Quarter', 4), ('Year', 1)]:
        data = client.get('/api/dashboard', params={'grain': grain}).json()
        assert len(data['periods']) == expected
    assert client.get('/api/dashboard?baseline=forecast').json()['comparison'][0].get('Budget') is None
    assert client.get('/api/dashboard?period=2030-01').status_code == 422
    assert client.get('/api/dashboard?grain=Week').status_code == 422


def files():
    return {name: (f'{name}.csv', (main.ROOT / 'data' / f'{filename}.csv').read_bytes(), 'text/csv')
            for name, filename in [('finance', 'finance'), ('operations', 'operations'), ('balances', 'balances')]}


def test_uploads_are_validated_and_isolated(client):
    original = client.get('/api/dashboard').json()
    uploads = files()
    finance = pd.read_csv(BytesIO(uploads['finance'][1]))
    finance.loc[finance.account == 'Revenue', 'amount'] *= 1.5
    uploads['finance'] = ('finance.csv', finance.to_csv(index=False).encode(), 'text/csv')
    assert client.post('/api/datasets/upload', files=uploads).status_code == 200
    updated = client.get('/api/dashboard').json()
    assert updated['source'] == 'Uploaded Data'
    assert updated['version'] != original['version']
    assert updated['comparison'][0]['Actual'] == pytest.approx(original['comparison'][0]['Actual'] * 1.5)
    with TestClient(main.app) as other:
        assert other.get('/api/dashboard').json()['source'] == 'Synthetic Sample Data'
    assert client.post('/api/datasets/upload', files={'finance': ('bad.csv', b'bad\n1'), **{k: v for k, v in files().items() if k != 'finance'}}).status_code == 422
    assert client.get('/api/dashboard').json()['version'] == updated['version']
    assert client.post('/api/datasets/sample').status_code == 200
    assert client.get('/api/dashboard').json()['source'] == 'Synthetic Sample Data'


@pytest.mark.parametrize('kind', ['csv', 'xlsx', 'pptx'])
def test_board_exports(client, kind):
    client.get('/api/dashboard')
    response = client.get(f'/api/exports/{kind}?period=2026-12')
    assert response.status_code == 200
    assert f'2026-12.{kind}' in response.headers['content-disposition']
    if kind == 'csv':
        frame = pd.read_csv(BytesIO(response.content))
        assert {'Budget', 'Forecast', 'Actual', 'Reporting Period', 'Currency'}.issubset(frame.columns)
    elif kind == 'xlsx':
        assert pd.ExcelFile(BytesIO(response.content)).sheet_names == ['Board KPIs', 'KPI History']
    else:
        assert len(Presentation(BytesIO(response.content)).slides) == 11


def test_ai_endpoints_and_chat_lifecycle(client, monkeypatch):
    calls = []
    def ask(*args, **kwargs):
        calls.append(kwargs['history'][:])
        return {'status': 'answered', 'answer': 'Grounded test answer.', 'limitation': '', 'source_ids': ['S1'],
                'evidence': [{'Source ID': 'S1', 'Metric': 'Revenue', 'Value': 100}]}
    monkeypatch.setattr(main, 'ask_data', ask)
    monkeypatch.setattr(main, 'generate_board_commentary', lambda *a, **k: '## Executive summary\nTest briefing.')
    assert client.post('/api/commentary', json={}).json()['sections'][0]['title'] == 'Executive Summary'
    assert client.post('/api/chat', json={'question': 'What is revenue?'}).status_code == 200
    assert len(client.get('/api/chat').json()['messages']) == 2
    assert client.post('/api/chat', json={'question': 'And budget?'}).status_code == 200
    assert len(calls[-1]) == 2
    assert client.get('/api/chat?currency=USD').json()['messages'] == []
    client.post('/api/chat', json={'question': 'Revenue?', 'currency': 'USD'})
    assert client.delete('/api/chat').json()['messages'] == []
    client.post('/api/chat', json={'question': 'Revenue?'})
    client.post('/api/datasets/sample')
    assert client.get('/api/chat').json()['messages'] == []


def test_api_failures_do_not_expose_configuration(client, monkeypatch):
    def fail(*a, **k):
        raise RuntimeError('private-token-must-not-leak')
    monkeypatch.setattr(main, 'generate_board_commentary', fail)
    response = client.post('/api/commentary', json={})
    assert response.status_code == 503
    assert 'private-token' not in response.text
    assert client.post('/api/chat', json={'question': ' '}).status_code == 422
    assert client.post('/api/datasets/sample', headers={'Origin': 'https://unrelated.example'}).status_code == 403
    assert 'OPENAI_API_KEY' not in json.dumps(client.get('/api/dashboard').json())


def test_expired_workspace_does_not_silently_show_sample_data(client):
    client.get('/api/dashboard')
    main.sessions.clear()
    response = client.get('/api/dashboard')
    assert response.status_code == 409
    assert 'expired' in response.json()['detail']
    assert 'Max-Age=0' in response.headers['set-cookie']
    assert client.get('/api/dashboard').json()['source'] == 'Synthetic Sample Data'
