"""Deterministic financial calculations. Currency is assumed consistent per upload."""
import pandas as pd

ACCOUNTS = {
    'Revenue': 'income', 'Cost of Sales': 'expense', 'Operating Expenses': 'expense',
    'Depreciation': 'expense', 'Interest': 'expense', 'Tax': 'expense', 'Staff Costs': 'expense'
}
FLOW_METRICS = ['Revenue', 'Cost of Sales', 'Operating Expenses', 'Depreciation', 'Interest', 'Tax']
STOCK_COLUMNS = ['Cash', 'Accounts Receivable', 'Inventory', 'Accounts Payable', 'Debt']
SCENARIOS = ['actual', 'budget', 'forecast']
OPS_EXTRA = ['orders_shipped', 'returned_orders', 'returned_order_value', 'waste_cost',
             'material_input_tonnes', 'recycled_input_tonnes', 'waste_recovered_tonnes']
BALANCE_EXTRA = ['Raw Material Stock Tonnes', 'Finished Goods Stock Tonnes',
                 'Customer Credit Limit', 'Overdue Receivables', 'Material Payables',
                 'Overdue Material Payables', 'Headcount']
METRIC_GROUPS = {
    'Financial performance': ['Revenue', 'Gross Profit', 'EBITDA', 'Net Profit',
                              'Gross Margin %', 'EBITDA Margin %', 'Operating Expenses', 'Staff Costs', 'Other Operating Expenses'],
    'Materials & circularity': ['production_tonnes', 'scrap_tonnes', 'Scrap Rate %', 'waste_cost',
                               'Recycled Input %', 'Waste Recovery %'],
    'Customer returns': ['orders_shipped', 'returned_orders', 'Return Rate %', 'returned_order_value'],
    'Stock & customer credit': ['Inventory', 'Raw Material Stock Tonnes', 'Finished Goods Stock Tonnes',
                              'Accounts Receivable', 'Overdue Receivables', 'Customer Credit Limit',
                              'Customer Credit Headroom', 'Credit Utilisation %'],
    'Cash, suppliers & people': ['Cash', 'Material Payables', 'Overdue Material Payables',
                               'Accounts Payable', 'Headcount', 'DSO', 'DIO', 'DPO', 'Cash Conversion Cycle'],
}


def _reject_infinity(df, columns):
    if df[columns].isin([float('inf'), float('-inf')]).any().any():
        raise ValueError('Numeric inputs must be finite')


def normalize_finance(data: pd.DataFrame) -> pd.DataFrame:
    required = {'period', 'account', 'scenario', 'amount'}
    if not required.issubset(data.columns):
        raise ValueError(f"Finance input requires: {', '.join(sorted(required))}")
    df = data.copy()
    df['period'] = pd.to_datetime(df['period'], errors='raise').dt.to_period('M').dt.to_timestamp()
    df['account'] = df['account'].astype(str).str.strip()
    df['scenario'] = df['scenario'].astype(str).str.strip().str.lower()
    if not df['account'].isin(ACCOUNTS).all():
        raise ValueError('Unknown accounts: ' + ', '.join(sorted(set(df.loc[~df.account.isin(ACCOUNTS), 'account']))))
    if not df['scenario'].isin(SCENARIOS).all():
        raise ValueError('Scenario must be actual, budget or forecast')
    df['amount'] = pd.to_numeric(df['amount'], errors='raise')
    _reject_infinity(df, ['amount'])
    if df[['period', 'account', 'scenario', 'amount']].isna().any().any():
        raise ValueError('Finance input contains missing required values')
    # Input convention: revenue and expense categories both entered as positive amounts.
    if (df['amount'] < 0).any():
        raise ValueError('Use positive values for both revenue and expense; corrections must be netted before upload')
    return df


def normalize_ops(data: pd.DataFrame) -> pd.DataFrame:
    required = {'period', 'scenario', 'production_tonnes', 'scrap_tonnes', 'energy_cost'}
    if not required.issubset(data.columns):
        raise ValueError('Operations input requires: ' + ', '.join(sorted(required)))
    df = data.copy()
    df['period'] = pd.to_datetime(df['period'], errors='raise').dt.to_period('M').dt.to_timestamp()
    df['scenario'] = df['scenario'].astype(str).str.strip().str.lower()
    for c in ['production_tonnes', 'scrap_tonnes', 'energy_cost']:
        df[c] = pd.to_numeric(df[c], errors='raise')
    for c in OPS_EXTRA:
        df[c] = pd.to_numeric(df[c], errors='raise') if c in df else float('nan')
    _reject_infinity(df, ['production_tonnes', 'scrap_tonnes', 'energy_cost'] + OPS_EXTRA)
    if df[list(required)].isna().any().any() or not df['scenario'].isin(SCENARIOS).all():
        raise ValueError('Operations input contains missing/invalid values')
    if (df[['production_tonnes', 'scrap_tonnes', 'energy_cost']] < 0).any().any():
        raise ValueError('Operations values must be nonnegative')
    if (df[OPS_EXTRA] < 0).any().any():
        raise ValueError('Additional operations values must be nonnegative')
    for c in ['orders_shipped', 'returned_orders']:
        if (df[c].dropna() % 1 != 0).any():
            raise ValueError('Order counts must be whole numbers')
    for subset, total in [('recycled_input_tonnes', 'material_input_tonnes'),
                          ('waste_recovered_tonnes', 'scrap_tonnes')]:
        if (df[subset] > df[total]).any():
            raise ValueError(f'{subset} cannot exceed {total}')
    return df


def normalize_balances(data: pd.DataFrame) -> pd.DataFrame:
    required = {'period', 'scenario', *STOCK_COLUMNS}
    if not required.issubset(data.columns):
        raise ValueError('Balance sheet input requires: ' + ', '.join(sorted(required)))
    df = data.copy()
    df['period'] = pd.to_datetime(df['period'], errors='raise').dt.to_period('M').dt.to_timestamp()
    df['scenario'] = df['scenario'].astype(str).str.strip().str.lower()
    for c in STOCK_COLUMNS:
        df[c] = pd.to_numeric(df[c], errors='raise')
    for c in BALANCE_EXTRA:
        df[c] = pd.to_numeric(df[c], errors='raise') if c in df else float('nan')
    _reject_infinity(df, STOCK_COLUMNS + BALANCE_EXTRA)
    if df[list(required)].isna().any().any() or not df['scenario'].isin(SCENARIOS).all():
        raise ValueError('Balance sheet input contains missing/invalid values')
    if df.duplicated(['period', 'scenario']).any():
        raise ValueError('Balance sheet has duplicate period/scenario records')
    if (df[BALANCE_EXTRA] < 0).any().any():
        raise ValueError('Additional closing balances must be nonnegative')
    if (df.Headcount.dropna() % 1 != 0).any():
        raise ValueError('Headcount must be a whole number')
    for subset, total in [('Overdue Receivables', 'Accounts Receivable'),
                          ('Overdue Material Payables', 'Material Payables'),
                          ('Material Payables', 'Accounts Payable')]:
        if (df[subset] > df[total]).any():
            raise ValueError(f'{subset} cannot exceed {total}')
    return df


def _period_label(d, grain):
    if grain == 'Month':
        return d.dt.strftime('%Y-%m')
    if grain == 'Quarter':
        return d.dt.to_period('Q').astype(str)
    return d.dt.strftime('%Y')


def _days_from_label(label, grain):
    p = pd.Period(label, freq={'Month': 'M', 'Quarter': 'Q', 'Year': 'Y'}[grain])
    return (p.end_time.normalize() - p.start_time.normalize()).days + 1


def build_kpis(finance: pd.DataFrame, operations: pd.DataFrame, balances: pd.DataFrame, grain='Month') -> pd.DataFrame:
    """Flow metrics sum; balance metrics take last available closing month."""
    if grain not in ['Month', 'Quarter', 'Year']:
        raise ValueError('Unsupported grain')
    f = normalize_finance(finance)
    o = normalize_ops(operations)
    b = normalize_balances(balances)
    for df in (f, o, b):
        df['label'] = _period_label(df['period'], grain)
    staff = f[f.account == 'Staff Costs'].groupby(['label', 'scenario'])['amount'].sum()
    month_counts = f.groupby(['label', 'scenario']).period.nunique()
    staff_counts = f[f.account == 'Staff Costs'].groupby(['label', 'scenario']).period.nunique()
    staff = staff.where(staff_counts.reindex(staff.index) == month_counts.reindex(staff.index))
    f = f.groupby(['label', 'scenario', 'account'], as_index=False)['amount'].sum()
    p = f.pivot_table(index=['label','scenario'], columns='account', values='amount', aggfunc='sum', fill_value=0).reset_index()
    for metric in FLOW_METRICS:
        if metric not in p:
            p[metric] = 0.0
    p['Staff Costs'] = [staff.get((row.label, row.scenario), float('nan')) for row in p.itertuples()]
    if (p['Staff Costs'] > p['Operating Expenses']).any():
        raise ValueError('Staff Costs must be included within Operating Expenses, not added on top')
    p['Gross Profit'] = p['Revenue'] - p['Cost of Sales']
    p['EBITDA'] = p['Gross Profit'] - p['Operating Expenses']
    p['Other Operating Expenses'] = p['Operating Expenses'] - p['Staff Costs']
    p['EBIT'] = p['EBITDA'] - p['Depreciation']
    p['Net Profit'] = p['EBIT'] - p['Interest'] - p['Tax']
    o = o.groupby(['label','scenario'], as_index=False)[['production_tonnes','scrap_tonnes','energy_cost'] + OPS_EXTRA].agg(lambda values: values.sum() if values.notna().all() else float('nan'))
    # Last closing balance of each reporting window, by scenario.
    b = b.sort_values('period').groupby(['label', 'scenario'], as_index=False).tail(1).drop(columns='period')
    p = p.merge(o, on=['label','scenario'], how='left').merge(b, on=['label','scenario'], how='left')
    p['Gross Margin %'] = (100 * p['Gross Profit'] / p['Revenue'].replace(0, float('nan')))
    p['EBITDA Margin %'] = (100 * p['EBITDA'] / p['Revenue'].replace(0, float('nan')))
    p['Net Margin %'] = (100 * p['Net Profit'] / p['Revenue'].replace(0, float('nan')))
    p['Scrap Rate %'] = 100 * p['scrap_tonnes'] / (p['production_tonnes'] + p['scrap_tonnes']).replace(0, float('nan'))
    p['Revenue / Tonne'] = p['Revenue'] / p['production_tonnes'].replace(0, float('nan'))
    p['COGS / Tonne'] = p['Cost of Sales'] / p['production_tonnes'].replace(0, float('nan'))
    p['Days'] = p['label'].apply(lambda x: _days_from_label(x, grain))
    p['DSO'] = p['Accounts Receivable'] / p['Revenue'].replace(0, float('nan')) * p['Days']
    p['DIO'] = p['Inventory'] / p['Cost of Sales'].replace(0, float('nan')) * p['Days']
    p['DPO'] = p['Accounts Payable'] / p['Cost of Sales'].replace(0, float('nan')) * p['Days']
    p['Cash Conversion Cycle'] = p['DSO'] + p['DIO'] - p['DPO']
    p['Return Rate %'] = 100 * p.returned_orders / p.orders_shipped.replace(0, float('nan'))
    p['Recycled Input %'] = 100 * p.recycled_input_tonnes / p.material_input_tonnes.replace(0, float('nan'))
    p['Waste Recovery %'] = 100 * p.waste_recovered_tonnes / p.scrap_tonnes.replace(0, float('nan'))
    p['Customer Credit Headroom'] = p['Customer Credit Limit'] - p['Accounts Receivable']
    p['Credit Utilisation %'] = 100 * p['Accounts Receivable'] / p['Customer Credit Limit'].replace(0, float('nan'))
    return p.sort_values(['label','scenario']).reset_index(drop=True)


def compare_scenarios(kpis: pd.DataFrame, label: str, baseline='budget'):
    if baseline == 'both':
        budget = compare_scenarios(kpis, label, 'budget').rename(columns={
            'Variance': 'Variance vs Budget', 'Variance %': 'Variance % vs Budget'})
        forecast = compare_scenarios(kpis, label, 'forecast').drop(columns='Actual').rename(columns={
            'Variance': 'Variance vs Forecast', 'Variance %': 'Variance % vs Forecast'})
        return budget.merge(forecast, on='Metric')
    if baseline not in ['budget', 'forecast']:
        raise ValueError('Comparison must be budget or forecast')
    rows = kpis[kpis['label'] == label].set_index('scenario')
    metrics = [metric for group in METRIC_GROUPS.values() for metric in group]
    result = []
    for metric in metrics:
        actual = rows.loc['actual', metric] if 'actual' in rows.index else float('nan')
        budget = rows.loc[baseline, metric] if baseline in rows.index else float('nan')
        if isinstance(actual, pd.Series): actual = actual.iloc[0]
        if isinstance(budget, pd.Series): budget = budget.iloc[0]
        variance = actual - budget
        result.append({'Metric': metric, 'Actual': actual, baseline.title(): budget,
                       'Variance': variance, 'Variance %': (variance/budget*100 if pd.notna(budget) and budget != 0 else float('nan'))})
    return pd.DataFrame(result)
