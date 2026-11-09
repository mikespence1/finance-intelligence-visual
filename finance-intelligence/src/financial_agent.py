"""Financial-page-only tools: no ERP identities or sustainability/operations measures."""
from src.query_agent import DataTools, ask_data, function_tools
from src.finance import METRIC_GROUPS

FINANCIAL_METRICS=set(METRIC_GROUPS['Financial performance']) | {'Cash','Accounts Receivable','Material Payables','Headcount'}
DEFINITIONS='''Financial Performance page only. Revenue and expenses are positive. Gross profit = revenue - cost of sales. EBITDA = earnings before interest, tax, depreciation and amortisation; in this model revenue - cost of sales - operating expenses. Net profit deducts depreciation, interest and tax. Staff costs are included in operating expenses. Other operating expenses = operating expenses - staff costs. Margins recalculate from totals. Cash, receivables, material payables and headcount take the latest closing month. Actual-minus-plan is the variance. Rate changes are percentage points. Missing values and zero denominator ratios are unavailable. This source contains aggregate financial data only, with no customer/SKU identities, circularity, waste, returns or operational measures. The separate Executive ERP dataset must never be mixed into these figures.'''

class FinancialDataTools(DataTools):
    def __init__(self,finance,operations,balances,currency='AED'):
        super().__init__(finance,operations,balances,currency)
        self.metrics=[metric for metric in self.metrics if metric in FINANCIAL_METRICS]
        self.monthly=self.monthly[['label','scenario']+self.metrics]
        self.frames['operations']=self.frames['operations'][['period','scenario']]
        self.frames['balances']=self.frames['balances'][[column for column in self.frames['balances'] if column in FINANCIAL_METRICS or column in ['period','scenario']]]
    def catalog(self):
        catalog=super().catalog()
        catalog['datasets'].pop('operations',None)
        catalog['scope']='Financial Performance page metrics only'
        catalog['unsupported_dimensions'] += ['sustainability','waste','returns','operations','Executive ERP customer/SKU data']
        return catalog
    def inspect_dataset(self,dataset,*args,**kwargs):
        if dataset not in ['finance','balances']: raise ValueError('Only Financial Performance finance/balances data is available')
        return super().inspect_dataset(dataset,*args,**kwargs)


def ask_financial(question,finance,operations,balances,context,history=(),client=None):
    specs=function_tools()
    specs[0]['parameters']['properties']['metrics']['items']={'type':'string','enum':sorted(FINANCIAL_METRICS)}
    specs[1]['parameters']['properties']['dataset']['enum']=['finance','balances']
    return ask_data(question,finance,operations,balances,context,history,client,
        data_tools=FinancialDataTools(finance,operations,balances,context['currency']),tool_specs=specs,definitions_text=DEFINITIONS)
