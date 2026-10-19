"""Deterministic financial calculations. Currency is assumed consistent per upload."""
import pandas as pd

ACCOUNTS = {
    'Revenue': 'income', 'Cost of Sales': 'expense', 'Operating Expenses': 'expense',
    'Depreciation': 'expense', 'Interest': 'expense', 'Tax': 'expense'
}
FLOW_METRICS = ['Revenue', 'Cost of Sales', 'Operating Expenses', 'Depreciation', 'Interest', 'Tax']
STOCK_COLUMNS = ['Cash', 'Accounts Receivable', 'Inventory', 'Accounts Payable', 'Debt']


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
    if not df['scenario'].isin(['actual', 'budget']).all():
        raise ValueError('Scenario must be actual or budget')
    df['amount'] = pd.to_numeric(df['amount'], errors='raise')
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
    if df[list(required)].isna().any().any() or not df['scenario'].isin(['actual', 'budget']).all():
        raise ValueError('Operations input contains missing/invalid values')
    if (df[['production_tonnes', 'scrap_tonnes', 'energy_cost']] < 0).any().any():
        raise ValueError('Operations values must be nonnegative')
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
    if df[list(required)].isna().any().any() or not df['scenario'].isin(['actual', 'budget']).all():
        raise ValueError('Balance sheet input contains missing/invalid values')
    if df.duplicated(['period', 'scenario']).any():
        raise ValueError('Balance sheet has duplicate period/scenario records')
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
    f = f.groupby(['label', 'scenario', 'account'], as_index=False)['amount'].sum()
    p = f.pivot_table(index=['label','scenario'], columns='account', values='amount', aggfunc='sum', fill_value=0).reset_index()
    for metric in FLOW_METRICS:
        if metric not in p:
            p[metric] = 0.0
    p['Gross Profit'] = p['Revenue'] - p['Cost of Sales']
    p['EBITDA'] = p['Gross Profit'] - p['Operating Expenses']
    p['EBIT'] = p['EBITDA'] - p['Depreciation']
    p['Net Profit'] = p['EBIT'] - p['Interest'] - p['Tax']
    o = o.groupby(['label','scenario'], as_index=False)[['production_tonnes','scrap_tonnes','energy_cost']].sum()
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
    return p.sort_values(['label','scenario']).reset_index(drop=True)


def compare_scenarios(kpis: pd.DataFrame, label: str):
    rows = kpis[kpis['label'] == label].set_index('scenario')
    metrics = ['Revenue', 'Gross Profit', 'EBITDA', 'Net Profit', 'Gross Margin %',
               'EBITDA Margin %', 'production_tonnes', 'Scrap Rate %', 'Cash',
               'DSO', 'DIO', 'DPO', 'Cash Conversion Cycle']
    result = []
    for metric in metrics:
        actual = rows.loc['actual', metric] if 'actual' in rows.index else float('nan')
        budget = rows.loc['budget', metric] if 'budget' in rows.index else float('nan')
        if isinstance(actual, pd.Series): actual = actual.iloc[0]
        if isinstance(budget, pd.Series): budget = budget.iloc[0]
        variance = actual - budget
        result.append({'Metric': metric, 'Actual': actual, 'Budget': budget,
                       'Variance': variance, 'Variance %': (variance/budget*100 if pd.notna(budget) and budget != 0 else float('nan'))})
    return pd.DataFrame(result)
