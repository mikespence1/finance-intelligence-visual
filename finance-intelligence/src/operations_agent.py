"""Read-only tools limited to the Sustainability & Operations page."""
from src.query_agent import DataTools, ask_data, function_tools
from src.finance import METRIC_GROUPS
OPERATIONS_METRICS=set().union(*(set(values) for key,values in METRIC_GROUPS.items() if key!='Financial performance'))
DEFINITIONS='''Sustainability & Operations page only. Good production excludes scrap. Scrap rate = scrap / (good production + scrap). Recycled input = recycled material input / total material input. Waste recovery = recovered scrap / scrap. Return rate = returned orders / shipped orders in the same period; returns may relate to earlier shipments. Ratios recompute from totals. Wastage cost and returned value are analytical disclosures, not extra profit deductions. Stock quantities/values, customer credit, cash, supplier payables and headcount use latest closing month. DSO = Days Sales Outstanding (receivables/revenue * days); DIO = Days Inventory Outstanding (inventory/cost of sales * days); DPO = Days Payable Outstanding (payables/cost of sales * days). Cash Conversion Cycle = DSO + DIO - DPO. These ratios use financial inputs internally but P&L revenue/profit results cannot be retrieved by this page tool. Aggregate credit headroom does not prove individual customer compliance. Missing values/zero denominators remain unavailable. No customer/SKU ERP identities, net profit, EBITDA or general financial-performance results are exposed. No verified business causes or sustainability certifications can be inferred.'''

class OperationsDataTools(DataTools):
    def __init__(self,finance,operations,balances,currency='AED'):
        super().__init__(finance,operations,balances,currency)
        self.metrics=[metric for metric in self.metrics if metric in OPERATIONS_METRICS]
        self.monthly=self.monthly[['label','scenario']+self.metrics]
        self.frames['balances']=self.frames['balances'][[column for column in self.frames['balances'] if column in OPERATIONS_METRICS or column in ['period','scenario']]]
    def catalog(self):
        catalog=super().catalog();catalog['datasets'].pop('finance',None)
        catalog['scope']='Sustainability & Operations page metrics only'
        catalog['unsupported_dimensions'] += ['Executive ERP identities','revenue and P&L profit metrics','EBITDA','Net Profit']
        return catalog
    def inspect_dataset(self,dataset,*args,**kwargs):
        if dataset not in ['operations','balances']: raise ValueError('Only Sustainability & Operations operations/balances data is available')
        return super().inspect_dataset(dataset,*args,**kwargs)


def ask_operations(question,finance,operations,balances,context,history=(),client=None):
    specs=function_tools()
    specs[0]['parameters']['properties']['metrics']['items']={'type':'string','enum':sorted(OPERATIONS_METRICS)}
    specs[1]['parameters']['properties']['dataset']['enum']=['operations','balances']
    return ask_data(question,finance,operations,balances,context,history,client,
        data_tools=OperationsDataTools(finance,operations,balances,context['currency']),tool_specs=specs,definitions_text=DEFINITIONS)
