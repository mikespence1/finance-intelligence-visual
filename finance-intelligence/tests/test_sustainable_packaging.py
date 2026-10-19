from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
from pptx import Presentation

from src.board_pack import board_pack
from src.finance import build_kpis, compare_scenarios, normalize_ops, normalize_balances

DATA = Path(__file__).resolve().parents[1] / 'data'


def inputs():
    return [pd.read_csv(DATA / f'{name}.csv') for name in ['finance', 'operations', 'balances']]


def test_aggregation_and_no_double_counting():
    f, o, b = inputs()
    monthly = build_kpis(f, o, b)
    annual = build_kpis(f, o, b, 'Year')
    a = annual[annual.scenario == 'actual'].iloc[0]
    months = monthly[monthly.scenario == 'actual']
    assert a['Staff Costs'] == pytest.approx(months['Staff Costs'].sum())
    assert a['EBITDA'] == pytest.approx(a['Revenue'] - a['Cost of Sales'] - a['Operating Expenses'])
    assert a['Headcount'] == months.iloc[-1]['Headcount']
    assert a['Inventory'] == months.iloc[-1]['Inventory']
    assert a['scrap_tonnes'] == pytest.approx(months.scrap_tonnes.sum())
    assert a['Return Rate %'] == pytest.approx(100 * months.returned_orders.sum() / months.orders_shipped.sum())
    assert a['Recycled Input %'] == pytest.approx(100 * months.recycled_input_tonnes.sum() / months.material_input_tonnes.sum())
    assert a['Customer Credit Headroom'] == pytest.approx(a['Customer Credit Limit'] - a['Accounts Receivable'])


def test_forecast_missing_and_zero_denominators():
    f, o, b = inputs()
    kpis = build_kpis(f, o, b)
    c = compare_scenarios(kpis, '2026-12', 'forecast').set_index('Metric')
    assert c.loc['Revenue', 'Variance'] == pytest.approx(c.loc['Revenue', 'Actual'] - c.loc['Revenue', 'Forecast'])
    missing = compare_scenarios(kpis[kpis.scenario != 'forecast'], '2026-12', 'forecast')
    assert missing.Forecast.isna().all()
    o.orders_shipped = 0
    o.material_input_tonnes = 0
    o.recycled_input_tonnes = 0
    c = build_kpis(f, o, b)
    assert c['Return Rate %'].isna().all()
    assert c['Recycled Input %'].isna().all()


def test_legacy_uploads_keep_optional_metrics_unavailable():
    f, o, b = inputs()
    f = f[f.account != 'Staff Costs']
    o = o[['period', 'scenario', 'production_tonnes', 'scrap_tonnes', 'energy_cost']]
    b = b[['period', 'scenario', 'Cash', 'Accounts Receivable', 'Inventory', 'Accounts Payable', 'Debt']]
    c = build_kpis(f, o, b)
    assert c['Staff Costs'].isna().all()
    assert c['Headcount'].isna().all()
    assert c.returned_orders.isna().all()


def test_invalid_new_metrics_fail_validation():
    _, o, b = inputs()
    o.loc[0, 'waste_recovered_tonnes'] = o.loc[0, 'scrap_tonnes'] + 1
    with pytest.raises(ValueError, match='cannot exceed'):
        normalize_ops(o)
    b.loc[0, 'Overdue Receivables'] = b.loc[0, 'Accounts Receivable'] + 1
    with pytest.raises(ValueError, match='cannot exceed'):
        normalize_balances(b)


def test_editable_board_pack_matches_dashboard():
    kpis = build_kpis(*inputs())
    content = board_pack(kpis, '2026-12', 'Month', source='Synthetic sample data')
    deck = Presentation(BytesIO(content))
    assert len(deck.slides) == 11
    assert sum(shape.has_chart for slide in deck.slides for shape in slide.shapes) == 4
    assert sum(shape.has_table for slide in deck.slides for shape in slide.shapes) == 5
    texts = []
    for slide in deck.slides:
        for shape in slide.shapes:
            assert shape.left >= 0 and shape.top >= 0
            assert shape.left + shape.width <= deck.slide_width
            assert shape.top + shape.height <= deck.slide_height
            if shape.has_text_frame:
                texts.append(shape.text)
            if shape.has_table:
                texts.extend(cell.text for row in shape.table.rows for cell in row.cells)
    text = '\n'.join(texts)
    assert 'December 2026' in text
    assert 'Forecast' in text
    assert 'Outstanding Material Payments' in text
    revenue = kpis[(kpis.label == '2026-12') & (kpis.scenario == 'actual')].iloc[0].Revenue
    assert f'AED {revenue:,.0f}' in text
