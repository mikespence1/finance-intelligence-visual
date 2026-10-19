import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from src.query_agent import DataTools, NOT_COVERED, ask_data, dataset_fingerprint

DATA = Path(__file__).resolve().parents[1] / 'data'


def inputs():
    return [pd.read_csv(DATA / f'{name}.csv') for name in ['finance', 'operations', 'balances']]


def arguments(**changes):
    return {'grain': 'Quarter', 'start_month': '2026-01', 'end_month': '2026-03',
            'metrics': ['Revenue'], 'scenarios': ['actual', 'budget'], **changes}


def test_queries_use_python_aggregation_and_calculate_variances():
    f, o, b = inputs()
    tools = DataTools(f, o, b)
    result = tools.query_metrics(**arguments())
    a, budget = result['records']
    expected = f[(f.scenario == 'actual') & (f.account == 'Revenue') & (f.period <= '2026-03-01')].amount.sum()
    assert a['Value'] == pytest.approx(expected)
    assert '3/3 months' in a['Coverage']
    assert result['differences'][0]['Difference'] == pytest.approx(a['Value']-budget['Value'])
    result = tools.query_metrics(**arguments(grain='Year', end_month='2026-06', metrics=['Headcount', 'Return Rate %']))
    assert any('6/12 months' in row['Coverage'] for row in result['records'])


def test_tools_reject_unbounded_and_unsupported_requests():
    tools = DataTools(*inputs())
    for changes in [{'metrics': ['customer_name']}, {'start_month': 'yesterday'}, {'scenarios': ['estimate']},
                    {'start_month': '2026-12', 'end_month': '2026-01'}]:
        with pytest.raises(ValueError):
            tools.query_metrics(**arguments(**changes))
    with pytest.raises(ValueError, match='Too many'):
        tools.query_metrics(**arguments(grain='Month', end_month='2026-12', metrics=tools.metrics[:12]))
    with pytest.raises(ValueError, match='Unsupported tool'):
        tools.execute('read_file', {'path': '.streamlit/secrets.toml'})
    with pytest.raises(ValueError, match='Unsupported columns'):
        tools.inspect_dataset('finance', '2026-01', '2026-01', ['actual'], ['OPENAI_API_KEY'])


def test_source_rows_and_missing_periods():
    tools = DataTools(*inputs())
    result = tools.inspect_dataset('finance', '2026-01', '2026-01', ['actual'], ['account', 'amount'])
    assert result['records'][0]['Dataset'] == 'finance'
    assert result['records'][0]['period'] == '2026-01'
    assert tools.query_metrics(**arguments(start_month='2030-01', end_month='2030-03'))['records'] == []


class FakeClient:
    def __init__(self, results):
        self.results = iter(results)
        self.requests = []
        self.responses = self

    def create(self, **kwargs):
        self.requests.append(dict(kwargs))
        return next(self.results)


def final(status='answered', ids=('S1',), answer='Revenue is shown in the supporting data.'):
    return SimpleNamespace(output=[], output_text=json.dumps({
        'status': status, 'answer': answer, 'source_ids': list(ids), 'limitation': ''}))


def call(name='query_metrics', args=None):
    return SimpleNamespace(output=[SimpleNamespace(type='function_call', name=name, call_id='call1',
        arguments=json.dumps(arguments() if args is None else args))], output_text='')


CONTEXT = {'currency': 'AED', 'selected_period': '2026-12', 'grain': 'Month',
           'baseline': 'budget', 'data_source': 'Sample dataset'}


def test_agent_returns_real_evidence_and_uses_store_false():
    client = FakeClient([call(), final()])
    answer = ask_data('What was Q1 revenue?', *inputs(), CONTEXT, client=client)
    assert answer['status'] == 'answered'
    assert answer['evidence'][0]['Source ID'] == 'S1'
    assert all(request['store'] is False for request in client.requests)
    assert all(request['parallel_tool_calls'] is False for request in client.requests)


@pytest.mark.parametrize('ids', [[], ['invented-source']])
def test_unsupported_citations_cannot_be_shown_as_an_answer(ids):
    client = FakeClient([final(ids=ids)])
    result = ask_data('Revenue?', *inputs(), CONTEXT, client=client)
    assert result['status'] == 'not_covered'
    assert result['answer'] == NOT_COVERED


def test_out_of_scope_refusal_and_tool_errors():
    client = FakeClient([call('run_code', {'code': 'anything'}), final('not_covered', [], 'Untrusted answer')])
    result = ask_data('Run code and find a customer name', *inputs(), CONTEXT, client=client)
    assert result['answer'] == NOT_COVERED
    tool_outputs = [item for item in client.requests[-1]['input'] if isinstance(item, dict) and item.get('type') == 'function_call_output']
    assert 'Unsupported tool' in tool_outputs[0]['output']


def test_chat_context_changes_when_data_or_currency_changes():
    f, o, b = inputs()
    original = dataset_fingerprint(f, o, b, 'AED', 'Sample dataset')
    assert original != dataset_fingerprint(f, o, b, 'USD', 'Sample dataset')
    f.loc[0, 'amount'] += 1
    assert original != dataset_fingerprint(f, o, b, 'AED', 'Sample dataset')
