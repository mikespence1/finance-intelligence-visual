from pathlib import Path

import pytest
AppTest = pytest.importorskip('streamlit.testing.v1', reason='Optional legacy Streamlit UI').AppTest


APP = Path(__file__).resolve().parents[1] / 'app.py'


def test_dashboard_periods_and_report_cards(monkeypatch):
    import src.ai

    calls = []

    def commentary(*args, **kwargs):
        calls.append((args, kwargs))
        return ('## Executive summary\nSummary for the board.\n'
                '## Performance vs budget\nPerformance details.\n'
                '## Risks and questions\nQuestions to review.\n'
                '## Proposed actions\nReview pricing.')

    monkeypatch.setattr(src.ai, 'generate_board_commentary', commentary)
    app = AppTest.from_file(str(APP)).run(timeout=30)
    assert not app.exception
    assert app.selectbox[0].format_func(app.selectbox[0].value) == 'December 2026'
    metric_labels = {metric.label for metric in app.metric}
    assert {'Headcount', 'Staff Costs', 'Variance To Budget', 'Variance To Forecast'}.issubset(metric_labels)
    app.sidebar.radio(key='reporting_page').set_value('Sustainability & Operations').run()
    assert not app.exception
    assert {'Material Wastage', 'Returned Orders'}.issubset({metric.label for metric in app.metric})
    app.sidebar.selectbox[0].select('Quarter').run()
    assert not app.exception
    assert 'Q4 2026' in app.subheader[0].value
    app.sidebar.selectbox[0].select('Year').run()
    assert not app.exception
    assert app.subheader[0].value == '2026 · Jan–Dec'
    app.sidebar.radio(key='reporting_page').set_value('AI Report').run()
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert len(calls) == 1
    assert calls[0][1]['currency'] == 'AED'
    assert calls[0][1]['baseline'] == 'both'
    assert {'Budget', 'Forecast', 'Variance vs Budget', 'Variance vs Forecast'}.issubset(calls[0][0][0].columns)
    app.sidebar.selectbox[1].select('forecast').run()
    assert not app.exception
    assert any('vs forecast' in metric.delta for metric in app.metric if metric.delta)
    assert not any(s.value == 'Executive Summary' for s in app.subheader)
    app.sidebar.selectbox[1].select('both').run()
    assert any(s.value == 'Executive Summary' for s in app.subheader)
    app.run()
    assert len(calls) == 1
    assert any(s.value == 'Executive Summary' for s in app.subheader)
    app.sidebar.selectbox[0].select('Month').run()
    assert not any(s.value == 'Executive Summary' for s in app.subheader)


def test_chat_answers_clear_and_reset_with_currency(monkeypatch):
    import src.query_agent
    calls = []

    def ask(*args, **kwargs):
        calls.append(args[0])
        return {'status': 'answered', 'answer': 'Synthetic performance answer.', 'limitation': '',
                'source_ids': ['S1'], 'evidence': [{'Source ID': 'S1', 'Metric': 'Revenue', 'Value': 100}]}

    monkeypatch.setattr(src.query_agent, 'ask_data', ask)
    app = AppTest.from_file(str(APP)).run(timeout=30)
    app.sidebar.radio(key='reporting_page').set_value('Ask Your Data').run()
    app.chat_input[0].set_value('What is revenue?').run(timeout=30)
    assert not app.exception
    assert calls == ['What is revenue?']
    assert len(app.chat_message) == 2
    app.run()
    assert len(calls) == 1
    assert len(app.chat_message) == 2
    app.sidebar.text_input[0].input('USD').run()
    assert not app.exception
    assert not app.chat_message
    app.chat_input[0].set_value('What is revenue?').run(timeout=30)
    app.button(key='clear_data_chat').click().run()
    assert not app.chat_message


def test_sidebar_navigation_and_combined_board_export():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    assert not app.exception
    assert not app.tabs
    assert app.sidebar.radio(key='reporting_page').value == 'Financial Performance'
    assert not app.chat_input
    app.sidebar.radio(key='reporting_page').set_value('Board Pack').run(timeout=30)
    assert not app.exception
    table = app.dataframe[0].value
    assert {'Actual', 'Budget', 'Forecast', 'Variance vs Budget', 'Variance vs Forecast'}.issubset(table.columns)
    assert not app.chat_input
    app.sidebar.selectbox[1].select('forecast').run(timeout=30)
    assert not app.exception
    assert 'Forecast' in app.dataframe[0].value.columns
    assert 'Budget' not in app.dataframe[0].value.columns
