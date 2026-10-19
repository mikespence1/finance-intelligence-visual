from pathlib import Path

from streamlit.testing.v1 import AppTest


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
    assert {'Material Wastage', 'Returned Orders', 'Headcount', 'Staff Costs'}.issubset(metric_labels)
    app.sidebar.selectbox[0].select('Quarter').run()
    assert not app.exception
    assert 'Q4 2026' in app.subheader[0].value
    app.sidebar.selectbox[0].select('Year').run()
    assert not app.exception
    assert app.subheader[0].value == '2026 · Jan–Dec'
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert len(calls) == 1
    assert calls[0][1]['currency'] == 'AED'
    app.sidebar.selectbox[1].select('forecast').run()
    assert not app.exception
    assert any('vs forecast' in metric.delta for metric in app.metric if metric.delta)
    assert not any(s.value == 'Executive Summary' for s in app.subheader)
    app.sidebar.selectbox[1].select('budget').run()
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
