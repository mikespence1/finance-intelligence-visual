"""Reproducible synthetic sustainable packaging data; no customer/company records."""
from pathlib import Path
import math
import pandas as pd

# Demand relative to an average month: quiet Jan/Feb; peak Jun–Oct and Dec.
SEASONAL_DEMAND = {1: .62, 2: .70, 3: 1.00, 4: 1.04, 5: 1.02,
                   6: 1.35, 7: 1.42, 8: 1.46, 9: 1.40, 10: 1.34,
                   11: 1.03, 12: 1.60}


def generate(destination):
    finance, operations, balances = [], [], []
    for month in range(1, 13):
        for scenario in ['actual', 'budget', 'forecast']:
            period = f'2026-{month:02d}-01'
            factor = {'budget': 1, 'forecast': 1.025, 'actual': 1 + .04 * math.sin(month)}[scenario]
            season = SEASONAL_DEMAND[month]
            busy = month in [6, 7, 8, 9, 10, 12]
            quiet = month in [1, 2]
            revenue = 5_500_000 * season * factor
            production = 1000 * season * factor
            waste_rate = {'actual': .046 - month * .0007, 'budget': .035, 'forecast': .039}[scenario]
            scrap = production * waste_rate / (1 - waste_rate)
            cogs = revenue * {'actual': .64, 'budget': .62, 'forecast': .635}[scenario]
            headcount = 86 + (10 if busy else -4 if quiet else 0) + (2 if scenario == 'actual' else 0)
            staff = headcount * 7800 * (1.08 if busy else 1)
            opex = staff + 180_000 + 50_000 * season * factor
            shipped = round(1200 * season * factor)
            returns = round(shipped * {'actual': .026, 'budget': .018, 'forecast': .022}[scenario])
            for account, amount in [('Revenue', revenue), ('Cost of Sales', cogs),
                                    ('Operating Expenses', opex), ('Staff Costs', staff),
                                    ('Depreciation', 125000), ('Interest', 28000),
                                    ('Tax', max(0, revenue - cogs - opex - 153000) * .09)]:
                finance.append(dict(period=period, scenario=scenario, account=account, amount=round(amount, 2)))
            operations.append(dict(
                period=period, scenario=scenario, production_tonnes=round(production, 2),
                scrap_tonnes=round(scrap, 2), energy_cost=round(60000 + 130000 * season * factor, 2),
                orders_shipped=shipped, returned_orders=returns,
                returned_order_value=round(returns * revenue / shipped, 2), waste_cost=round(scrap * 2300, 2),
                material_input_tonnes=round(production + scrap, 2),
                recycled_input_tonnes=round((production + scrap) * (.62 + month * .008), 2),
                waste_recovered_tonnes=round(scrap * .82, 2)))
            receivables = revenue * .92
            payables = cogs * .65
            balances.append(dict(period=period, scenario=scenario, **{
                'Cash': round(2200000 + month * 95000 * factor, 2),
                'Accounts Receivable': round(receivables, 2), 'Inventory': round(cogs * .8, 2),
                'Accounts Payable': round(payables, 2), 'Debt': 2400000,
                'Raw Material Stock Tonnes': round(production * .48, 2),
                'Finished Goods Stock Tonnes': round(production * .19, 2),
                'Customer Credit Limit': 6200000, 'Overdue Receivables': round(receivables * .14, 2),
                'Material Payables': round(payables * .88, 2),
                'Overdue Material Payables': round(payables * .88 * .12, 2), 'Headcount': headcount}))
    destination.mkdir(parents=True, exist_ok=True)
    for name, records in [('finance', finance), ('operations', operations), ('balances', balances)]:
        pd.DataFrame(records).to_csv(destination / f'{name}.csv', index=False)


if __name__ == '__main__':
    generate(Path(__file__).resolve().parents[1] / 'data')
