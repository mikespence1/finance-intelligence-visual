import json
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.executive import dashboard, source


def test_executive_reconciles_to_invoice_lines():
    sales,plans=source()
    d=dashboard()
    cutoff=pd.Timestamp(d['as_of'])
    mtd=sales[sales.posting_date.between(cutoff.replace(day=1),cutoff)]
    assert d['mtd']==pytest.approx(mtd.net_revenue.sum())
    assert sum(r['net_revenue'] for r in d['customers'])==pytest.approx(d['mtd'])
    assert sum(r['gross_profit'] for r in d['skus'])==pytest.approx((mtd.net_revenue-mtd.cogs).sum())
    prior=sales[sales.posting_date.between('2025-01-01','2025-11-09')].net_revenue.sum()
    assert d['sales_2025']==pytest.approx(prior)
    assert d['vs_2025_pct']==pytest.approx((d['ytd']-prior)/abs(prior)*100)
    assert len(d['history'])==36
    assert sales.quantity.lt(0).any()
    json.dumps(d,allow_nan=False)


def test_filters_and_daily_plans_match_cutoff():
    sales,plans=source()
    d=dashboard(date='2025-02-17',category='paper',location='Dubai')
    mask=(plans.category=='paper')&(plans.location=='Dubai')&plans.date.between('2025-02-01','2025-02-17')
    assert d['budget']==pytest.approx(plans.loc[mask,'budget'].sum())
    daily=sales[(sales.category=='paper')&(sales.location=='Dubai')&(sales.posting_date==pd.Timestamp('2025-02-17'))]
    assert d['daily_revenue']==pytest.approx(daily.net_revenue.sum())
    assert dashboard(date='2024-01-01')['prior_ytd'] is None


def test_executive_endpoint_and_invalid_dates():
    with TestClient(app) as client:
        response=client.get('/api/executive')
        assert response.status_code==200
        assert response.json()['source']=='Synthetic ERP sample'
        assert client.get('/api/executive?date=bad').status_code==422
        assert client.get('/api/executive?date=2027-01-01').status_code==422

def test_period_filters_and_reduced_sample():
    sales, _ = source()
    assert set(sales.location) == {'Abu Dhabi', 'Dubai', 'Other Emirates', 'KSA'}
    assert dashboard()['ytd'] == pytest.approx(60532077.62 / 2)
    for period, start in [('day','2026-11-09'), ('qtd','2026-10-01'), ('ytd','2026-01-01'), ('custom','2026-07-15')]:
        d = dashboard(period=period, start_date='2026-07-15', category='paper', location='KSA')
        expected = sales[(sales.category == 'paper') & (sales.location == 'KSA') & sales.posting_date.between(start,'2026-11-09')]
        assert d['analysis_start'] == start
        assert sum(r['net_revenue'] for r in d['customers']) == pytest.approx(expected.net_revenue.sum())
        assert sum(r['gross_profit'] for r in d['skus']) == pytest.approx(expected.gross_profit.sum())
    with TestClient(app) as client:
        assert client.get('/api/executive?period=custom').status_code == 422
        assert client.get('/api/executive?period=custom&start_date=2027-01-01').status_code == 422
        assert client.get('/api/executive?period=invalid').status_code == 422


def test_cohort_trends_reconcile_and_keep_fixed_entities():
    from backend.executive import cohort_trend
    sales,_=source()
    members=dashboard()['customers'][:3]
    names=[row['customer'] for row in members]
    trend=cohort_trend(date='2026-11-09',category='paper',location='KSA',period='mtd',dimension='customer',members=names,metric='gross_profit')
    for key,start,end in [('current','2026-11-01','2026-11-09'),('last_month','2026-10-01','2026-10-09'),('last_year','2025-11-01','2025-11-09')]:
        subset=sales[sales.customer.isin(names)&(sales.category=='paper')&(sales.location=='KSA')&sales.posting_date.between(start,end)]
        assert trend['points'][-1][key]==pytest.approx(subset.gross_profit.sum())
        assert next(p for p in trend['periods'] if p['key']==key)['value']==pytest.approx(subset.gross_profit.sum())
    assert len(trend['points'])==9
    json.dumps(trend,allow_nan=False)


def test_trend_margins_calendar_boundaries_and_missing_history():
    from backend.executive import cohort_trend
    sales,_=source()
    trend=cohort_trend(date='2024-02-29',period='mtd',dimension='location',members=[],metric='gross_margin')
    assert trend['periods'][2]['end']=='2023-02-28'
    assert trend['periods'][2]['value'] is None
    assert all(row['last_year'] is None for row in trend['points'])
    assert trend['periods'][1]['end']=='2024-01-29'
    subset=sales[sales.posting_date.between('2024-02-01','2024-02-29')]
    assert trend['periods'][0]['value']==pytest.approx(subset.gross_profit.sum()/subset.net_revenue.sum()*100)
    assert len(trend['points'])==29
    custom=cohort_trend(date='2026-03-31',period='custom',start_date='2026-03-15',members=[])
    assert custom['periods'][1]['end']=='2026-02-28'
    assert custom['periods'][1]['start']=='2026-02-15'
    assert custom['points'][-1]['last_month'] is None
    with TestClient(app) as client:
        assert client.get('/api/executive/trend?metric=unknown').status_code==422
        assert client.get('/api/executive/trend?members=Gulf+Retail+25').status_code==200


def test_analysis_period_totals_and_quarter_cutoff_filter_all_visuals():
    from backend.executive import cohort_trend
    sales,plans=source()
    for period,start in [('day','2026-11-09'),('mtd','2026-11-01'),('qtd','2026-10-01'),('ytd','2026-01-01'),('custom','2026-08-12')]:
        data=dashboard(period=period,start_date='2026-08-12',category='paper',location='KSA')
        actual=sales[(sales.category=='paper')&(sales.location=='KSA')&sales.posting_date.between(start,'2026-11-09')]
        plan=plans[(plans.category=='paper')&(plans.location=='KSA')&plans.date.between(start,'2026-11-09')]
        assert data['analysis_revenue']==pytest.approx(actual.net_revenue.sum())
        assert data['analysis_budget']==pytest.approx(plan.budget.sum())
        assert data['analysis_forecast']==pytest.approx(plan.forecast.sum())
        assert sum(row['net_revenue'] for row in data['analysis_history'])==pytest.approx(data['analysis_revenue'])
        assert data['analysis_budget_variance']==pytest.approx(data['analysis_revenue']-data['analysis_budget'])
    trend=cohort_trend(date='2026-11-09',period='day',members=[])
    quarter=next(row for row in trend['periods'] if row['key']=='last_quarter')
    assert quarter['start']==quarter['end']=='2026-08-09'
    assert quarter['value']==pytest.approx(sales.loc[sales.posting_date==pd.Timestamp('2026-08-09'),'net_revenue'].sum())
