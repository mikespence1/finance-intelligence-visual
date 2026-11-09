"""Executive reporting over normalized Dynamics extract contracts."""
from pathlib import Path
import calendar
import hashlib
import os
from typing import Literal
from functools import lru_cache
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix='/api/executive')

@lru_cache(maxsize=1)
def source():
    root = Path(os.environ.get('EXECUTIVE_DATA_DIR', Path(__file__).resolve().parents[1] / 'data' / 'executive'))
    sales = pd.read_csv(root/'sales_lines.csv', parse_dates=['posting_date'])
    plans = pd.read_csv(root/'daily_plans.csv', parse_dates=['date'])
    for name,key in [('customers','customer_id'),('skus','sku_id'),('locations','location_id')]:
        dim=pd.read_csv(root/f'{name}.csv')
        if dim[key].duplicated().any(): raise ValueError(f'Duplicate {key}')
        sales=sales.merge(dim,on=key,how='left',validate='many_to_one')
        if name != 'customers': plans=plans.merge(dim,on=key,how='left',validate='many_to_one')
    if sales[['customer','sku','location','category']].isna().any().any() or plans[['sku','location']].isna().any().any(): raise ValueError('Unmapped dimension keys')
    if plans.duplicated(['date','sku_id','location_id']).any(): raise ValueError('Duplicate daily plan grain; select one plan version')
    if sales.posting_date.isna().any() or plans.date.isna().any(): raise ValueError('Missing posting or plan dates')
    if sales.duplicated(['company','invoice_id','line_number']).any(): raise ValueError('Duplicate invoice lines')
    for frame, cols in [(sales,['net_revenue','cogs']), (plans,['budget','forecast'])]:
        for col in cols:
            if frame[col].isna().any() or not frame[col].map(lambda x: isinstance(x,(int,float)) and abs(x)<1e15).all(): raise ValueError(f'Invalid {col}')
    if set(sales.currency) != {'AED'}: raise ValueError('Normalize all extracts to AED before loading')
    sales['gross_profit']=sales.net_revenue-sales.cogs
    digest=hashlib.sha256()
    for name in ['sales_lines','daily_plans','customers','skus','locations']:
        digest.update((root/f'{name}.csv').read_bytes())
    sales.attrs['revision']=digest.hexdigest()
    return sales,plans

def rows(frame): return frame.to_dict('records')
def pct(value,base): return (value-base)/abs(base)*100 if base else None

def grouped(frame,key):
    result=frame.groupby(key,as_index=False)[['net_revenue','cogs','gross_profit']].sum()
    result['gross_margin']=result.gross_profit.div(result.net_revenue.replace(0,float('nan'))).mul(100)
    return result.sort_values('gross_profit',ascending=False).astype(object).where(pd.notna(result),None)

@router.get('')
def dashboard(date: str | None=None, category: str='', location: str='', period: Literal['day','mtd','qtd','ytd','custom']='mtd', start_date: str | None=None):
    try: sales,plans=source()
    except (ValueError,KeyError,FileNotFoundError) as e: raise HTTPException(422,f'Executive extract validation: {e}') from None
    minimum=sales.posting_date.min(); maximum=sales.posting_date.max()
    try: end=pd.Timestamp(date) if date else maximum
    except ValueError: raise HTTPException(422,'Invalid as-of date') from None
    if pd.isna(end) or end < minimum or end > maximum: raise HTTPException(422,'As-of date must be inside actual data coverage')
    options={'categories':sorted(sales.category.unique()),'locations':sorted(sales.location.unique())}
    for key,value in [('category',category),('location',location)]:
        if value:
            sales=sales[sales[key]==value];plans=plans[plans[key]==value]
    month=end.replace(day=1); year=end.replace(month=1,day=1)
    mtd=sales[sales.posting_date.between(month,end)]; daily=sales[sales.posting_date==end]; ytd=sales[sales.posting_date.between(year,end)]
    starts={'day':end,'mtd':month,'qtd':end.replace(month=((end.month-1)//3)*3+1,day=1),'ytd':year}
    if period == 'custom':
        try: start=pd.Timestamp(start_date) if start_date else None
        except ValueError: raise HTTPException(422,'Invalid start date') from None
        if start is None or pd.isna(start) or start < minimum or start > end:
            raise HTTPException(422,'Custom start date must be within coverage and before the as-of date')
    else: start=starts[period]
    analysis=sales[sales.posting_date.between(start,end)]
    prior=end.replace(year=end.year-1,day=min(end.day,calendar.monthrange(end.year-1,end.month)[1]))
    prior_start=prior.replace(month=1,day=1)
    prior_value=float(sales.loc[sales.posting_date.between(prior_start,prior),'net_revenue'].sum()) if minimum <= prior_start else None
    fixed_end=pd.Timestamp(2025,end.month,min(end.day,calendar.monthrange(2025,end.month)[1]))
    fixed=float(sales.loc[sales.posting_date.between('2025-01-01',fixed_end),'net_revenue'].sum()) if minimum <= pd.Timestamp('2025-01-01') and maximum >= fixed_end else None
    plan=plans[plans.date.between(month,end)]
    revenue=float(mtd.net_revenue.sum()); budget=float(plan.budget.sum()) if len(plan) else None;forecast=float(plan.forecast.sum()) if len(plan) else None
    analysis_plan=plans[plans.date.between(start,end)]
    analysis_revenue=float(analysis.net_revenue.sum())
    analysis_profit=float(analysis.gross_profit.sum())
    analysis_budget=float(analysis_plan.budget.sum()) if len(analysis_plan) else None
    analysis_forecast=float(analysis_plan.forecast.sum()) if len(analysis_plan) else None
    comparison_end=end-pd.DateOffset(years=1)
    comparison_start=start-pd.DateOffset(years=1) if period=='custom' else trend_window(comparison_end,period)[0]
    analysis_prior=float(sales.loc[sales.posting_date.between(comparison_start,comparison_end),'net_revenue'].sum()) if comparison_start>=minimum and comparison_end<=maximum else None
    analysis_history=analysis.assign(month=lambda x:x.posting_date.dt.strftime('%Y-%m')).groupby('month',as_index=False)[['net_revenue','gross_profit']].sum()
    analysis_history=analysis_history.merge(analysis_plan.assign(month=lambda x:x.date.dt.strftime('%Y-%m')).groupby('month',as_index=False)[['budget','forecast']].sum(),on='month',how='outer')
    analysis_history['mom_pct']=analysis_history.net_revenue.pct_change(fill_method=None).mul(100)
    analysis_history=analysis_history.astype(object).where(pd.notna(analysis_history),None)
    history=sales[sales.posting_date<=end].assign(month=lambda x:x.posting_date.dt.strftime('%Y-%m')).groupby('month',as_index=False)[['net_revenue','gross_profit']].sum()
    history['mom_pct']=history.net_revenue.pct_change().mul(100)
    planning=plans[plans.date<=end].assign(month=lambda x:x.date.dt.strftime('%Y-%m')).groupby('month',as_index=False)[['budget','forecast']].sum()
    history=history.merge(planning,on='month',how='left').astype(object).where(lambda x:pd.notna(x),None)
    return {'as_of':str(end.date()),'min_date':str(minimum.date()),'max_date':str(maximum.date()),'options':options,'source':'Dynamics extract' if os.environ.get('EXECUTIVE_DATA_DIR') else 'Synthetic ERP sample',
        'daily_revenue':float(daily.net_revenue.sum()),'mtd':revenue,'ytd':float(ytd.net_revenue.sum()),'prior_ytd':prior_value,'yoy_pct':pct(float(ytd.net_revenue.sum()),prior_value) if prior_value is not None else None,'sales_2025':fixed,'vs_2025_pct':pct(float(ytd.net_revenue.sum()),fixed) if fixed is not None else None,
        'budget':budget,'forecast':forecast,'budget_variance':revenue-budget if budget is not None else None,'forecast_variance':revenue-forecast if forecast is not None else None,'budget_pct':pct(revenue,budget) if budget is not None else None,'forecast_pct':pct(revenue,forecast) if forecast is not None else None,
        'analysis_budget':analysis_budget,'analysis_forecast':analysis_forecast,
        'analysis_budget_variance':analysis_revenue-analysis_budget if analysis_budget is not None else None,'analysis_budget_pct':pct(analysis_revenue,analysis_budget) if analysis_budget is not None else None,
        'analysis_forecast_variance':analysis_revenue-analysis_forecast if analysis_forecast is not None else None,'analysis_forecast_pct':pct(analysis_revenue,analysis_forecast) if analysis_forecast is not None else None,
        'analysis_margin':analysis_profit/analysis_revenue*100 if analysis_revenue else None,'analysis_prior_revenue':analysis_prior,'analysis_yoy_pct':pct(analysis_revenue,analysis_prior) if analysis_prior is not None else None,
        'analysis_history':rows(analysis_history),'analysis_start':str(start.date()),'analysis_end':str(end.date()),'analysis_revenue':float(analysis.net_revenue.sum()),'analysis_profit':float(analysis.gross_profit.sum()),'breakdowns':{key:rows(grouped(analysis,key)) for key in ['customer','category','sku','location']},'customers':rows(grouped(analysis,'customer')),'skus':rows(grouped(analysis,'sku')),'daily':{key:rows(grouped(daily,key)) for key in ['customer','category','sku','location']},'history':rows(history)}


def trend_window(end, period, custom_start=None):
    if period == 'day': return end,end
    if period == 'mtd': return end.replace(day=1),end
    if period == 'qtd': return end.replace(month=((end.month-1)//3)*3+1,day=1),end
    if period == 'ytd': return end.replace(month=1,day=1),end
    return custom_start,end


@router.get('/trend')
def cohort_trend(date: str | None=None, category: str='', location: str='',
        period: Literal['day','mtd','qtd','ytd','custom']='mtd', start_date: str | None=None,
        dimension: Literal['customer','sku','category','location']='customer', members: list[str]=Query(default=[]),
        metric: Literal['net_revenue','gross_profit','gross_margin']='net_revenue'):
    if len(members)>100: raise HTTPException(422,'Select at most 100 entities')
    try: sales,_=source()
    except (ValueError,KeyError,FileNotFoundError) as error:
        raise HTTPException(422,f'Executive extract validation: {error}') from None
    minimum=sales.posting_date.min(); maximum=sales.posting_date.max()
    try:
        end=pd.Timestamp(date) if date else maximum
        custom=pd.Timestamp(start_date) if start_date else None
    except ValueError: raise HTTPException(422,'Invalid comparison date') from None
    if pd.isna(end) or end<minimum or end>maximum: raise HTTPException(422,'As-of date must be inside actual data coverage')
    if period=='custom' and (custom is None or pd.isna(custom) or custom<minimum or custom>end):
        raise HTTPException(422,'Custom start date must be within coverage and before the as-of date')
    start,end=trend_window(end,period,custom)
    if members and not set(members).issubset(set(sales[dimension])): raise HTTPException(422,'Unknown comparison entity')
    for key,value in [('category',category),('location',location)]:
        if value: sales=sales[sales[key]==value]
    if members: sales=sales[sales[dimension].isin(members)]
    series={}; summaries=[]
    for key,name,offset in [('current','Selected period',None),('last_month','Same time last month',pd.DateOffset(months=1)),('last_year','Same time last year',pd.DateOffset(years=1)),('last_quarter','Same time last quarter',pd.DateOffset(months=3))]:
        finish=end if offset is None else end-offset
        custom=start if offset is None else start-offset
        begin,finish=trend_window(finish,period,custom)
        complete=begin>=minimum and finish<=maximum
        dates=pd.date_range(begin,finish)
        values=[]
        if complete:
            frame=sales[sales.posting_date.between(begin,finish)]
            cumulative=frame.groupby('posting_date')[['net_revenue','gross_profit']].sum().reindex(dates,fill_value=0).cumsum()
            if metric=='gross_margin':
                values=[None if revenue==0 else float(profit/revenue*100) for revenue,profit in zip(cumulative.net_revenue,cumulative.gross_profit)]
            else: values=[float(value) for value in cumulative[metric]]
        else: values=[None]*len(dates)
        series[key]=values
        summaries.append({'key':key,'name':name,'start':str(begin.date()),'end':str(finish.date()),'days':len(dates),'complete':complete,'value':values[-1] if values else None})
    points=[{'day':i+1,**{key:values[i] if i<len(values) else None for key,values in series.items()}} for i in range(max(map(len,series.values())))]
    current=summaries[0]['value']
    for summary in summaries:
        base=summary['value']; summary['change']=current-base if current is not None and base is not None else None
        summary['change_pct']=pct(current,base) if current is not None and base is not None and metric!='gross_margin' else None
    return {'metric':metric,'dimension':dimension,'member_count':len(members),'points':points,'periods':summaries,
        'note':'Fixed set of displayed entities in all periods; no historical reranking. Cumulative totals; margin recomputes from cumulative revenue and gross profit. Named periods restart at the relevant month/quarter/year boundary; custom ranges shift both dates. Compare by elapsed day. Period lengths can differ; lines stop at their own cutoff. Incomplete extract coverage is unavailable.'}
