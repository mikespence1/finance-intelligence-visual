import pandas as pd

from src.presentation import format_metric, narrative_sections, period_label, performance_chart


def test_period_labels_are_readable_and_preserve_year():
    assert period_label('2026-01', 'Month') == 'January 2026'
    assert period_label('2026Q4', 'Quarter') == 'Q4 2026 · Oct–Dec'
    assert period_label('2026', 'Year') == '2026 · Jan–Dec'


def test_missing_metrics_are_not_shown_as_numbers():
    assert format_metric(float('nan'), 'Revenue', 'AED') == 'No Data'
    assert format_metric(25, 'DSO', 'AED') == '25.0 days'


def test_narrative_sections_keep_body_and_support_heading_variants():
    text = ('## Executive summary\nRevenue improved.\n\n'
            '**Performance vs budget:**\n- Margin below plan.\n'
            '### Risks and questions\nValidate demand.\n'
            '4. Proposed actions\nReview pricing.')
    sections = narrative_sections(text)
    assert len(sections) == 4
    assert sections[1] == ('Performance vs budget', '- Margin below plan.')
    assert sections[-1][1] == 'Review pricing.'
    assert narrative_sections('Plain report body.') == [('Overview', 'Plain report body.')]


def test_chart_keeps_missing_budget_gaps_and_selected_period():
    data = pd.DataFrame([
        {'label': '2026-01', 'scenario': 'actual', 'Revenue': 100},
        {'label': '2026-02', 'scenario': 'actual', 'Revenue': 200},
        {'label': '2026-02', 'scenario': 'budget', 'Revenue': 180},
    ])
    chart = performance_chart(data, 'Revenue', 'Month', '2026-02', 'AED')
    assert pd.isna(chart.data[0].y[0])
    assert chart.data[0].connectgaps is False
    assert chart.layout.shapes[0].x0 == 1
    assert list(chart.layout.xaxis.ticktext) == ['Jan<br>2026', 'Feb<br>2026']
    assert chart.layout.xaxis.type == 'linear'
    assert list(chart.data[0].x) == [0, 1]
    assert list(chart.layout.xaxis.range) == [-.35, 1.35]


def test_trends_share_axis_coordinates_for_all_reporting_grains():
    for grain, labels in [('Month', ['2026-01', '2026-12']),
                          ('Quarter', ['2026Q1', '2026Q4']), ('Year', ['2026'])]:
        data = pd.DataFrame([{'label': label, 'scenario': scenario, 'Revenue': 100 + i}
                             for i, label in enumerate(labels) for scenario in ['actual', 'budget', 'forecast']])
        for baseline in ['budget', 'forecast']:
            chart = performance_chart(data, 'Revenue', grain, labels[-1], 'AED', baseline)
            assert all(trace.type == 'scatter' and trace.mode == 'lines+markers' for trace in chart.data)
            assert all(list(trace.x) == list(range(len(labels))) for trace in chart.data)
            assert chart.layout.shapes[0].x0 == len(labels)-1
            assert chart.layout.xaxis.range[0] < chart.layout.shapes[0].x0 < chart.layout.xaxis.range[1]


def test_combined_chart_has_three_distinct_trends_and_missing_forecast_gaps():
    data = pd.DataFrame([
        {'label': '2026-01', 'scenario': 'actual', 'Revenue': 100},
        {'label': '2026-02', 'scenario': 'actual', 'Revenue': 120},
        {'label': '2026-01', 'scenario': 'budget', 'Revenue': 110},
        {'label': '2026-02', 'scenario': 'budget', 'Revenue': 115},
        {'label': '2026-02', 'scenario': 'forecast', 'Revenue': 118},
    ])
    chart = performance_chart(data, 'Revenue', 'Month', '2026-02', 'AED', 'both')
    assert [trace.name for trace in chart.data] == ['Budget', 'Forecast', 'Actual']
    assert len({trace.line.dash for trace in chart.data}) == 3
    assert pd.isna(chart.data[1].y[0])
    assert len(narrative_sections('## Performance vs budget and forecast\nBoth comparisons.')) == 1
    assert narrative_sections('## Performance vs budget and forecast\nBoth comparisons.')[0][1] == 'Both comparisons.'
