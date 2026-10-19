import pandas as pd
from src.finance import build_kpis, compare_scenarios


def test_quarter_flow_sum_stock_last_and_weighted_margin():
    fin=[]; ops=[]; bal=[]
    for i, revenue in enumerate([100,200,300],1):
        dt=f'2026-{i:02d}-01'
        for account, amount in [('Revenue',revenue),('Cost of Sales',revenue*.5),('Operating Expenses',10)]:
            fin.append(dict(period=dt, scenario='actual', account=account, amount=amount))
        ops.append(dict(period=dt, scenario='actual',production_tonnes=10,scrap_tonnes=i,energy_cost=5))
        bal.append(dict(period=dt,scenario='actual',Cash=i*100,**{'Accounts Receivable':40,'Inventory':50,'Accounts Payable':30,'Debt':10}))
    q=build_kpis(pd.DataFrame(fin),pd.DataFrame(ops),pd.DataFrame(bal),'Quarter')
    r=q.iloc[0]
    assert r['Revenue']==600
    assert r['Gross Profit']==300
    assert r['EBITDA']==270
    assert r['Cash']==300
    assert r['Gross Margin %']==50
    assert r['Scrap Rate %']==100*6/36
    assert r['Days']==90


def test_invalid_account_fails():
    from src.finance import normalize_finance
    try:
        normalize_finance(pd.DataFrame([{'period':'2026-01-01','scenario':'actual','account':'Unsupported','amount':1}]))
    except ValueError:
        return
    assert False, 'Invalid account should fail'
