"""Bounded, read-only data tools. No generated Python, SQL, web or file access."""
import hashlib
import json
import os
from pathlib import Path
import re

import pandas as pd

from src.ai import openai_client
from src.finance import build_kpis, normalize_finance, normalize_ops, normalize_balances
from src.presentation import format_metric, period_label

NOT_COVERED = "This question is not covered by the application's available data, so I can't answer it reliably."
ROOT = Path(__file__).resolve().parents[1]


def dataset_fingerprint(finance, operations, balances, currency, source):
    digest = hashlib.sha256((currency + source).encode())
    for frame in [finance, operations, balances]:
        digest.update(frame.to_json(date_format='iso', orient='split').encode())
    return digest.hexdigest()


class DataTools:
    def __init__(self, finance, operations, balances, currency='AED'):
        self.frames = dict(zip(['finance', 'operations', 'balances'],
                               [normalize_finance(finance), normalize_ops(operations), normalize_balances(balances)]))
        self.currency = currency
        self.monthly = build_kpis(*self.frames.values())
        self.metrics = [c for c in self.monthly.columns if c not in ['label', 'scenario']]
        for name, frame in self.frames.items():
            allowed = {'period', 'scenario', 'account', 'amount'} if name == 'finance' else set(self.metrics) | {'period', 'scenario'}
            self.frames[name] = frame[[c for c in frame.columns if c in allowed]]
        self.evidence = []

    def record(self, row):
        if len(self.evidence) >= 500:
            raise ValueError('Retrieval limit reached; ask a narrower question')
        row = {'Source ID': f'S{len(self.evidence)+1}', **row}
        self.evidence.append(row)
        return row

    def catalog(self):
        return {'metrics': self.metrics,
                'datasets': {name: list(frame.columns) for name, frame in self.frames.items()},
                'months': sorted(self.monthly.label.unique()),
                'scenarios': sorted(self.monthly.scenario.unique()), 'currency': self.currency,
                'unsupported_dimensions': ['customer identity', 'SKU', 'supplier identity', 'return reason', 'employee identity', 'verified root causes']}

    def filtered(self, start_month, end_month, scenarios):
        if not all(isinstance(m, str) and re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', m) for m in [start_month, end_month]):
            raise ValueError('Use YYYY-MM month boundaries')
        if start_month > end_month:
            raise ValueError('Start month must not follow end month')
        if not scenarios or not set(scenarios).issubset({'actual', 'budget', 'forecast'}):
            raise ValueError('Choose actual, budget or forecast')
        return {name: frame[(frame.period.dt.strftime('%Y-%m') >= start_month) &
                            (frame.period.dt.strftime('%Y-%m') <= end_month) &
                            frame.scenario.isin(scenarios)].copy() for name, frame in self.frames.items()}

    def query_metrics(self, grain, start_month, end_month, metrics, scenarios):
        if grain not in ['Month', 'Quarter', 'Year'] or not metrics or len(metrics) > 12 or not set(metrics).issubset(self.metrics):
            raise ValueError('Choose up to 12 catalog metrics and Month, Quarter or Year')
        frames = self.filtered(start_month, end_month, scenarios)
        if frames['finance'].empty:
            return {'error': 'No finance data for the requested range/scenario', 'records': []}
        kpis = build_kpis(*frames.values(), grain=grain)
        if len(kpis) * len(metrics) > 180:
            raise ValueError('Too many results; narrow the date range, metrics or scenarios')
        records = []
        for _, row in kpis.iterrows():
            period = pd.Period(row.label, freq={'Month': 'M', 'Quarter': 'Q', 'Year': 'Y'}[grain])
            expected = pd.period_range(period.start_time, period.end_time, freq='M')
            coverage = {}
            for name, frame in frames.items():
                dates = frame.loc[frame.scenario == row.scenario, 'period'].dt.to_period('M')
                coverage[name] = f'{dates[dates.isin(expected)].nunique()}/{len(expected)} months'
            for metric in metrics:
                value = None if pd.isna(row[metric]) else float(row[metric])
                records.append(self.record({'Metric': metric, 'Period': period_label(row.label, grain),
                    'Scenario': row.scenario, 'Value': value, 'Display': format_metric(row[metric], metric, self.currency),
                    'Sources': 'finance / operations / balances; src/finance.py definitions',
                    'Coverage': '; '.join(f'{k}: {v}' for k, v in coverage.items()),
                    'Requested Window': f'{start_month} to {end_month}'}))
        # Return server-calculated period and planning differences, rather than asking
        # the language model to perform financial arithmetic.
        differences = []
        for metric in metrics:
            for scenario in scenarios:
                history = kpis[kpis.scenario == scenario].sort_values('label')
                if len(history) > 1:
                    first, last = history.iloc[0], history.iloc[-1]
                    differences.append(self.difference(metric, last[metric], first[metric],
                        f'{scenario}: {last.label} minus {first.label}'))
            for label in kpis.label.unique():
                rows = kpis[kpis.label == label].set_index('scenario')
                for baseline in ['budget', 'forecast']:
                    if 'actual' in rows.index and baseline in rows.index:
                        differences.append(self.difference(metric, rows.loc['actual', metric], rows.loc[baseline, metric],
                            f'{label}: actual minus {baseline}'))
        return {'records': records, 'differences': differences,
                'note': 'Flows sum; stocks/headcount use last closing month; ratios recompute. Coverage is month presence, not reconciliation. Days ratios use the full calendar window.'}

    def difference(self, metric, value, baseline, comparison):
        delta = None if pd.isna(value) or pd.isna(baseline) else float(value-baseline)
        relative = None if delta is None or baseline == 0 else float(delta/baseline*100)
        return self.record({'Metric': metric, 'Comparison': comparison, 'Difference': delta,
                            'Difference Unit': 'percentage points' if '%' in metric else 'metric units',
                            'Relative Difference %': relative, 'Sources': 'Calculated from retrieved KPI records'})

    def inspect_dataset(self, dataset, start_month, end_month, scenarios, columns):
        if dataset not in self.frames or not columns or len(columns) > 10:
            raise ValueError('Choose a catalog dataset and up to 10 columns')
        # Only normalized, supported columns are exposed, not arbitrary extra uploads.
        allowed = {'finance': {'period', 'scenario', 'account', 'amount'},
                   'operations': set(self.metrics) | {'period', 'scenario'},
                   'balances': set(self.metrics) | {'period', 'scenario'}}
        if not set(columns).issubset(set(self.frames[dataset].columns) & allowed[dataset]):
            raise ValueError('Unsupported columns')
        frame = self.filtered(start_month, end_month, scenarios)[dataset]
        if len(frame) > 80:
            raise ValueError('Too many source rows; narrow the date range or use query_metrics')
        frame = frame[list(dict.fromkeys(['period', 'scenario'] + columns))].copy()
        frame['period'] = frame.period.dt.strftime('%Y-%m')
        rows = json.loads(frame.to_json(orient='records'))
        return {'records': [self.record({'Dataset': dataset, **row}) for row in rows],
                'note': 'Source rows; do not treat omitted or missing values as zero.'}

    def execute(self, name, arguments):
        if name not in ['query_metrics', 'inspect_dataset']:
            raise ValueError('Unsupported tool')
        return getattr(self, name)(**arguments)


def function_tools():
    common = {'start_month': {'type': 'string', 'description': 'Inclusive YYYY-MM'},
              'end_month': {'type': 'string', 'description': 'Inclusive YYYY-MM'},
              'scenarios': {'type': 'array', 'items': {'type': 'string', 'enum': ['actual', 'budget', 'forecast']}}}
    specs = [
        ('query_metrics', 'Calculate supported KPIs, trends, first/last period changes, and planning variances in Python. Use Year with a month range for YTD totals.',
         {**common, 'grain': {'type': 'string', 'enum': ['Month', 'Quarter', 'Year']},
          'metrics': {'type': 'array', 'items': {'type': 'string'}}}),
        ('inspect_dataset', 'Retrieve bounded source records from the supported input schemas. Use query_metrics for aggregations.',
         {**common, 'dataset': {'type': 'string', 'enum': ['finance', 'operations', 'balances']},
          'columns': {'type': 'array', 'items': {'type': 'string'}}}),
    ]
    return [{'type': 'function', 'name': name, 'description': description, 'strict': True,
             'parameters': {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}}
            for name, description, props in specs]


def ask_data(question, finance, operations, balances, context, history=(), client=None):
    if not question.strip() or len(question) > 4000:
        raise ValueError('Enter a question of up to 4,000 characters')
    tools = DataTools(finance, operations, balances, context['currency'])
    definitions = (ROOT / 'DATA_DICTIONARY.md').read_text(encoding='utf-8')
    instructions = (ROOT / 'prompts' / 'data_agent.md').read_text(encoding='utf-8')
    instructions += '\nApplication context: ' + json.dumps(context)
    instructions += '\nCatalog: ' + json.dumps(tools.catalog())
    instructions += '\nDefinitions [D1]:\n' + definitions
    conversation = [{'role': m['role'], 'content': m['content'][:6000]} for m in history[-6:] if m['role'] in ['user', 'assistant']]
    conversation.append({'role': 'user', 'content': question})
    client = client or openai_client()
    schema = {'type': 'object', 'properties': {
        'status': {'type': 'string', 'enum': ['answered', 'partial', 'not_covered', 'clarification']},
        'answer': {'type': 'string'}, 'limitation': {'type': 'string'},
        'source_ids': {'type': 'array', 'items': {'type': 'string'}}},
        'required': ['status', 'answer', 'limitation', 'source_ids'], 'additionalProperties': False}
    for _ in range(4):
        response = client.responses.create(
            model=os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini'), store=False,
            instructions=instructions, input=conversation, tools=function_tools(),
            parallel_tool_calls=False, max_output_tokens=1800,
            text={'format': {'type': 'json_schema', 'name': 'data_answer', 'strict': True, 'schema': schema}})
        calls = [item for item in response.output if item.type == 'function_call']
        if calls:
            conversation.extend(response.output)
            if len(calls) > 2:
                break
            for call in calls:
                try:
                    result = tools.execute(call.name, json.loads(call.arguments))
                except (ValueError, TypeError, KeyError) as error:
                    result = {'error': str(error)}
                conversation.append({'type': 'function_call_output', 'call_id': call.call_id,
                                     'output': json.dumps(result, allow_nan=False)})
            continue
        try:
            answer = json.loads(response.output_text)
            status, ids = answer['status'], answer['source_ids']
            if not isinstance(answer['answer'], str) or not isinstance(answer['limitation'], str):
                raise ValueError('Invalid response')
            valid = {row['Source ID'] for row in tools.evidence} | {'D1'}
            if status not in ['answered', 'partial', 'not_covered', 'clarification'] or not isinstance(ids, list) or not set(ids).issubset(valid):
                raise ValueError('Invalid citations')
            if status in ['answered', 'partial'] and not ids:
                raise ValueError('No evidence')
            if status == 'not_covered':
                answer['answer'] = NOT_COVERED
            answer['evidence'] = [row for row in tools.evidence if row['Source ID'] in ids]
            return answer
        except (ValueError, KeyError, TypeError):
            break
    return {'status': 'not_covered', 'answer': NOT_COVERED,
            'limitation': 'A supported answer with verifiable source references could not be produced. Try a specific metric, period and comparison.',
            'source_ids': [], 'evidence': []}
