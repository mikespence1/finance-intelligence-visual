"""Allowlisted Executive ERP aggregations for the existing read-only data agent."""
import re
import pandas as pd
from src.query_agent import DataTools, ask_data

DEFINITIONS = '''Executive ERP: synthetic sample unless context says Dynamics extract. AED accounting currency, no FX conversion. Net revenue excludes VAT and includes signed credit notes. COGS includes signed posted costs. Gross profit = net revenue - COGS, before overhead. Gross margin = summed gross profit / summed net revenue * 100. Budget/forecast are supplied daily SKU/location plans, not customer allocations. Variance = revenue - plan; variance % = variance / abs(plan) * 100. Comparisons use explicit inclusive date boundaries. Missing coverage or a zero denominator yields unavailable, not zero. Rankings include only entities with activity; margin rankings require positive net revenue. No verified business causes, customer overhead allocations or net profit are present.'''

class ExecutiveDataTools:
    record = DataTools.record
    def __init__(self, sales, plans):
        self.sales, self.plans, self.evidence = sales, plans, []

    def catalog(self):
        return {'dataset': 'Executive ERP invoice lines and daily plans', 'currency': 'AED',
                'actual_start': str(self.sales.posting_date.min().date()), 'actual_end': str(self.sales.posting_date.max().date()),
                'plan_start': str(self.plans.date.min().date()), 'plan_end': str(self.plans.date.max().date()),
                'dimensions': {key: sorted(self.sales[key].unique()) for key in ['customer','sku','category','location']},
                'metrics': ['net_revenue','cogs','gross_profit','gross_margin','budget','forecast'],
                'unsupported': ['customer budgets/forecasts','net profit','overhead allocations','verified causes','supplier identity']}

    @staticmethod
    def bounds(start, end):
        if not all(isinstance(value,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',value) for value in [start,end]):
            raise ValueError('Use inclusive YYYY-MM-DD dates')
        try: start, end = pd.Timestamp(start), pd.Timestamp(end)
        except ValueError: raise ValueError('Invalid date') from None
        if start > end: raise ValueError('Start date must not follow end date')
        return start,end

    def aggregate(self, start, end, group_by, category, location, customer, sku):
        sales=self.sales; plans=self.plans
        for key,value in [('category',category),('location',location),('customer',customer),('sku',sku)]:
            if value:
                if value not in set(sales[key]): raise ValueError(f'Unknown {key}; choose a catalog value')
                sales=sales[sales[key]==value]
                if key!='customer': plans=plans[plans[key]==value]
        actual_covered = start >= self.sales.posting_date.min() and end <= self.sales.posting_date.max()
        plan_covered = start >= self.plans.date.min() and end <= self.plans.date.max()
        sales=sales[sales.posting_date.between(start,end)].copy(); plans=plans[plans.date.between(start,end)].copy()
        def group(frame,date_column):
            if group_by=='total': frame['group']='Total'
            elif group_by in ['day','month']:
                frame['group']=frame[date_column].dt.strftime('%Y-%m-%d' if group_by=='day' else '%Y-%m')
            else: frame['group']=frame[group_by]
            return frame
        sales=group(sales,'posting_date')
        result=sales.groupby('group')[['net_revenue','cogs','gross_profit']].sum()
        # Plans have no customer allocation; never repeat the whole plan for every customer.
        if group_by!='customer' and not customer:
            plans=group(plans,'date')
            result=result.join(plans.groupby('group')[['budget','forecast']].sum(),how='outer')
        else:
            result['budget']=float('nan'); result['forecast']=float('nan')
        if group_by=='total' and result.empty: result=result.reindex(['Total'])
        for column in ['net_revenue','cogs','gross_profit']:
            result[column]=result[column].fillna(0) if actual_covered else float('nan')
        for column in ['budget','forecast']:
            if not plan_covered or customer or group_by=='customer': result[column]=float('nan')
            else: result[column]=result[column].fillna(0)
        result['gross_margin']=result.gross_profit.div(result.net_revenue.replace(0,float('nan'))).mul(100) if actual_covered else float('nan')
        for target in ['budget','forecast']:
            result[target+'_variance']=result.net_revenue-result[target]
            result[target+'_variance_pct']=result[target+'_variance'].div(result[target].abs().replace(0,float('nan'))).mul(100)
        return result,actual_covered,plan_covered

    def query_executive(self,start_date,end_date,group_by,category,location,customer,sku,sort_by,direction,limit,compare_start_date,compare_end_date):
        if group_by not in ['total','day','month','customer','sku','category','location']: raise ValueError('Unsupported grouping')
        if sort_by not in ['group','net_revenue','gross_profit','gross_margin','budget','forecast']: raise ValueError('Unsupported sorting')
        if direction not in ['asc','desc'] or not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=100: raise ValueError('Choose asc/desc and limit 1-100')
        start,end=self.bounds(start_date,end_date)
        result,actual_covered,plan_covered=self.aggregate(start,end,group_by,category,location,customer,sku)
        if bool(compare_start_date)!=bool(compare_end_date): raise ValueError('Supply both comparison dates')
        if compare_start_date:
            a,b=self.bounds(compare_start_date,compare_end_date)
            prior,_,_=self.aggregate(a,b,group_by,category,location,customer,sku)
            if group_by in ['day','month']: raise ValueError('Use total or entity grouping for comparison periods; query time trends separately')
            for metric in ['net_revenue','gross_profit','gross_margin']:
                result['comparison_'+metric]=prior[metric].reindex(result.index)
                result[metric+'_change']=result[metric]-result['comparison_'+metric]
                if metric!='gross_margin': result[metric+'_change_pct']=result[metric+'_change'].div(result['comparison_'+metric].abs().replace(0,float('nan'))).mul(100)
        if sort_by=='gross_margin': result=result[result.net_revenue>0]
        result=result.reset_index().sort_values([sort_by]+(['group'] if sort_by!='group' else []),ascending=[direction=='asc']+([True] if sort_by!='group' else []),na_position='last').head(limit)
        if len(self.evidence)+len(result)>500: raise ValueError('Retrieval limit reached; narrow the question')
        records=[]
        for row in result.astype(object).where(pd.notna(result),None).to_dict('records'):
            records.append(self.record({'Dataset':'Executive ERP', 'Start':start_date,'End':end_date,'Group by':group_by,
                'Category filter':category or 'All','Location filter':location or 'All','Customer filter':customer or 'All','SKU filter':sku or 'All',
                'Comparison start':compare_start_date,'Comparison end':compare_end_date,
                'Actual coverage complete':actual_covered,'Plan coverage complete':plan_covered,'Currency':'AED',**row}))
        return {'records':records,'note': 'Read-only Python calculations. Gross margin changes are percentage points. Customer plans unavailable. Coverage checks date boundaries, not reconciliation; verify extract completeness. Missing amounts and zero-denominator ratios are null.'}

    def execute(self,name,arguments):
        if name!='query_executive': raise ValueError('Unsupported tool')
        return self.query_executive(**arguments)


def executive_function_tools():
    props={key:{'type':'string','description':description} for key,description in {
        'start_date':'Inclusive YYYY-MM-DD; default supplied analysis_start', 'end_date':'Inclusive YYYY-MM-DD; default supplied analysis_end',
        'category':'Exact catalog category or empty for all; default context category', 'location':'Exact catalog location or empty for all; default context location',
        'customer':'Exact catalog customer name or empty for all','sku':'Exact catalog SKU name or empty for all',
        'compare_start_date':'Inclusive comparison YYYY-MM-DD, or empty when not comparing','compare_end_date':'Inclusive comparison YYYY-MM-DD, or empty when not comparing'}.items()}
    props.update(group_by={'type':'string','enum':['total','day','month','customer','sku','category','location']},sort_by={'type':'string','enum':['group','net_revenue','gross_profit','gross_margin','budget','forecast']},direction={'type':'string','enum':['asc','desc']},limit={'type':'integer','minimum':1,'maximum':100})
    return [{'type':'function','name':'query_executive','description':'Calculate Executive ERP totals, trends, top/bottom entities, weighted gross margins, budget/forecast variances and comparison-period changes. Use total for daily/MTD/YTD comparisons; customer or SKU for rankings. Budget and forecast are unavailable by customer. No raw code execution.','strict':True,'parameters':{'type':'object','properties':props,'required':list(props),'additionalProperties':False}}]


def ask_executive(question,sales,plans,context,history=(),client=None):
    context={**context, 'scope':'Executive Dashboard metrics only: revenue, COGS, gross profit, gross margin, customer/SKU/category/location rankings, trends, budget and forecast. Refuse unrelated and Financial Performance-only measures such as EBITDA, net profit, cash, headcount and operations.'}
    return ask_data(question,None,None,None,context,history,client,
        data_tools=ExecutiveDataTools(sales,plans),tool_specs=executive_function_tools(),definitions_text=DEFINITIONS)
