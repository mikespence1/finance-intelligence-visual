import json
from types import SimpleNamespace
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from backend import main
from backend.executive import source, dashboard
from backend.storage import WorkspaceStore
from src.executive_agent import ExecutiveDataTools, ask_executive


def arguments(**changes):
    return dict(start_date='2026-11-01',end_date='2026-11-09',group_by='total',category='',location='',customer='',sku='',sort_by='net_revenue',direction='desc',limit=20,compare_start_date='',compare_end_date='',**{}) | changes


def test_erp_totals_plans_rankings_and_weighted_margin():
    sales,plans=source(); tools=ExecutiveDataTools(sales,plans)
    row=tools.query_executive(**arguments(category='paper',location='KSA'))['records'][0]
    sample=sales[(sales.category=='paper') & (sales.location=='KSA') & sales.posting_date.between('2026-11-01','2026-11-09')]
    assert row['net_revenue']==pytest.approx(sample.net_revenue.sum())
    assert row['gross_margin']==pytest.approx(sample.gross_profit.sum()/sample.net_revenue.sum()*100)
    assert row['budget']==pytest.approx(dashboard(category='paper',location='KSA')['budget'])
    assert row['budget_variance']==pytest.approx(row['net_revenue']-row['budget'])
    for direction in ['asc','desc']:
        rows=tools.query_executive(**arguments(group_by='customer',sort_by='gross_profit',direction=direction,limit=5))['records']
        expected=sales[sales.posting_date.between('2026-11-01','2026-11-09')].groupby('customer').gross_profit.sum().sort_values(ascending=direction=='asc').head(5)
        assert [r['group'] for r in rows]==list(expected.index)
        assert all(r['budget'] is None and r['forecast'] is None for r in rows)


def test_comparisons_missing_coverage_and_limits():
    tools=ExecutiveDataTools(*source())
    row=tools.query_executive(**arguments(start_date='2026-01-01',compare_start_date='2025-01-01',compare_end_date='2025-11-09'))['records'][0]
    assert row['net_revenue_change_pct']==pytest.approx(dashboard()['vs_2025_pct'])
    row=tools.query_executive(**arguments(start_date='2020-01-01',end_date='2020-01-02'))['records'][0]
    assert row['net_revenue'] is None
    assert row['budget'] is None
    assert row['Actual coverage complete'] is False
    json.dumps(row,allow_nan=False)
    for changes in [dict(group_by='supplier'),dict(sort_by='secret'),dict(limit=101),dict(customer='nonexistent'),dict(start_date='invalid'),dict(direction='unsafe')]:
        with pytest.raises(ValueError): tools.query_executive(**arguments(**changes))
    with pytest.raises(ValueError,match='Unsupported tool'): tools.execute('run_code',{})


class FakeClient:
    def __init__(self): self.responses=self;self.requests=[]
    def create(self,**kwargs):
        self.requests.append(kwargs)
        if len(self.requests)==1:
            return SimpleNamespace(output=[SimpleNamespace(type='function_call',name='query_executive',call_id='erp1',arguments=json.dumps(arguments(group_by='customer',limit=1)))],output_text='')
        return SimpleNamespace(output=[],output_text=json.dumps(dict(status='answered',answer='Top customer shown in supporting data [S1].',limitation='',source_ids=['S1'])))


def test_agent_returns_real_erp_evidence_without_live_api():
    client=FakeClient()
    reply=ask_executive('Who is the top customer?',*source(),dict(currency='AED',analysis_start='2026-11-01',analysis_end='2026-11-09',data_source='Synthetic ERP sample'),client=client)
    assert reply['status']=='answered'
    assert reply['evidence'][0]['Dataset']=='Executive ERP'
    assert reply['evidence'][0]['group']
    assert all(request['store'] is False for request in client.requests)
    assert client.requests[0]['tools'][0]['name']=='query_executive'
    assert 'query_metrics' not in [t['name'] for t in client.requests[0]['tools']]


def test_executive_chat_context_history_and_source_isolation(monkeypatch,tmp_path):
    store=WorkspaceStore('sqlite:///'+str(tmp_path/'erp.sqlite3'))
    monkeypatch.setattr(main,'get_store',lambda:store)
    contexts=[]
    def answer(question,sales,plans,context,history):
        contexts.append((context,history.copy()))
        return dict(status='answered',answer='Synthetic ERP answer',limitation='',source_ids=['S1'],evidence=[{'Source ID':'S1','Dataset':'Executive ERP'}])
    monkeypatch.setattr(main,'ask_executive',answer)
    monkeypatch.setattr(main,'ai_request',lambda fn:fn())
    original_save=main.save_workspace
    saves=[]
    def track_save(state):
        saves.append(1)
        return original_save(state)
    monkeypatch.setattr(main,'save_workspace',track_save)
    with TestClient(main.app) as client:
        assert client.get('/api/executive/chat?period=ytd&location=KSA').status_code==200
        assert saves == []  # Loading/filtering must not race to overwrite a workspace.
        response=client.post('/api/executive/chat',json=dict(question='Sales?',period='ytd',location='KSA'))
        assert response.status_code==200
        assert contexts[0][0]['analysis_start']=='2026-01-01'
        assert contexts[0][0]['location']=='KSA'
        assert contexts[0][0]['currency']=='AED'
        assert len(client.get('/api/executive/chat?period=ytd&location=KSA').json()['messages'])==2
        assert client.get('/api/chat').json()['messages']==[]
        assert client.get('/api/executive/chat?period=mtd').json()['messages']==[]
        assert client.post('/api/executive/chat',json=dict(question='Sales?')).status_code==200
        assert contexts[-1][1]==[]
        with TestClient(main.app) as other:
            assert other.get('/api/executive/chat').json()['messages']==[]
        assert client.delete('/api/executive/chat').status_code==200
        assert client.get('/api/executive/chat').json()['messages']==[]
        assert client.post('/api/executive/chat',json=dict(question=' ',period='custom')).status_code==422
    store.engine.dispose()


def test_financial_page_tools_block_operations_and_erp_dimensions():
    from src.financial_agent import FinancialDataTools,FINANCIAL_METRICS,ask_financial
    from test_query_agent import inputs, FakeClient, call, final, arguments, CONTEXT
    tools=FinancialDataTools(*inputs())
    assert set(tools.catalog()['metrics']).issubset(FINANCIAL_METRICS)
    assert 'operations' not in tools.catalog()['datasets']
    for metric in ['Scrap Rate %','Return Rate %','DSO','production_tonnes']:
        with pytest.raises(ValueError): tools.query_metrics(**arguments(metrics=[metric]))
    with pytest.raises(ValueError): tools.inspect_dataset('operations','2026-01','2026-01',['actual'],['scrap_tonnes'])
    with pytest.raises(ValueError): tools.inspect_dataset('balances','2026-01','2026-01',['actual'],['Inventory'])
    result=tools.query_metrics(**arguments(metrics=['Revenue','EBITDA','Cash'],scenarios=['actual']))
    assert len(result['records'])==3
    assert all(row['Value'] is not None for row in result['records'])
    client=FakeClient([call(args=arguments(metrics=['EBITDA'])),final()])
    answer=ask_financial('What is EBITDA?',*inputs(),CONTEXT,client=client)
    assert answer['status']=='answered'
    assert 'Financial Performance page only' in client.requests[0]['instructions']
    assert client.requests[0]['tools'][1]['parameters']['properties']['dataset']['enum']==['finance','balances']


def test_financial_chat_is_separate_and_uses_page_scope(monkeypatch,tmp_path):
    from backend.storage import WorkspaceStore
    from backend import main
    from fastapi.testclient import TestClient
    store=WorkspaceStore('sqlite:///'+str(tmp_path/'financial.sqlite3'))
    monkeypatch.setattr(main,'get_store',lambda:store)
    contexts=[]
    def answer(question,finance,ops,balances,context,history):
        contexts.append(context)
        return dict(status='answered',answer='Financial page result',limitation='',source_ids=['S1'],evidence=[])
    monkeypatch.setattr(main,'ask_financial',answer)
    monkeypatch.setattr(main,'ai_request',lambda function:function())
    with TestClient(main.app) as client:
        assert client.get('/api/financial/chat').json()['messages']==[]
        response=client.post('/api/financial/chat',json=dict(question='EBITDA?',currency='AED',grain='Quarter',period='2026Q4',baseline='both'))
        assert response.status_code==200
        assert contexts[0]['scope']=='Financial Performance page only'
        assert contexts[0]['selected_period']=='2026Q4'
        assert len(client.get('/api/financial/chat').json()['messages'])==2
        assert client.get('/api/chat').json()['messages']==[]
        assert client.get('/api/executive/chat').json()['messages']==[]
        assert client.get('/api/financial/chat?currency=USD').json()['messages']==[]
        client.delete('/api/financial/chat')
        assert client.get('/api/financial/chat').json()['messages']==[]
    store.engine.dispose()


def test_operations_tools_are_scoped_and_calculate_operational_ratios():
    from src.operations_agent import OperationsDataTools,OPERATIONS_METRICS
    from test_query_agent import inputs,arguments
    tools=OperationsDataTools(*inputs())
    assert set(tools.catalog()['metrics']).issubset(OPERATIONS_METRICS)
    assert 'finance' not in tools.catalog()['datasets']
    for metric in ['Revenue','EBITDA','Gross Profit','Net Profit','Gross Margin %']:
        with pytest.raises(ValueError):tools.query_metrics(**arguments(metrics=[metric]))
    with pytest.raises(ValueError):tools.inspect_dataset('finance','2026-01','2026-01',['actual'],['amount'])
    results=tools.query_metrics(**arguments(metrics=['Scrap Rate %','Recycled Input %','Return Rate %','DSO'],scenarios=['actual']))
    assert len(results['records'])==4
    assert all(row['Value'] is not None for row in results['records'])


def test_operations_chat_uses_own_context_and_history(monkeypatch,tmp_path):
    store=WorkspaceStore('sqlite:///'+str(tmp_path/'ops.sqlite3'))
    monkeypatch.setattr(main,'get_store',lambda:store)
    monkeypatch.setattr(main,'ai_request',lambda function:function())
    contexts=[]
    def reply(question,finance,ops,balances,context,history):
        contexts.append(context)
        return dict(answer='Synthetic operations result',status='answered',source_ids=['S1'],evidence=[],limitation='')
    monkeypatch.setattr(main,'ask_operations',reply)
    with TestClient(main.app) as client:
        assert client.get('/api/operations/chat').json()['messages']==[]
        response=client.post('/api/operations/chat',json=dict(question='Scrap rate?',period='2026-11',grain='Month',baseline='both',currency='AED'))
        assert response.status_code==200
        assert contexts[0]['scope']=='Sustainability & Operations page only'
        assert contexts[0]['selected_period']=='2026-11'
        assert len(client.get('/api/operations/chat').json()['messages'])==2
        assert client.get('/api/financial/chat').json()['messages']==[]
        assert client.get('/api/executive/chat').json()['messages']==[]
        client.delete('/api/operations/chat')
        assert client.get('/api/operations/chat').json()['messages']==[]
    store.engine.dispose()
