"""Deterministic, invoice-line ERP fixture. Run from the project root."""
from pathlib import Path
import random
import pandas as pd


def generate():
    rng = random.Random(20261109)
    root = Path(__file__).resolve().parents[1] / 'data' / 'executive'
    root.mkdir(exist_ok=True)
    customers = pd.DataFrame([{'customer_id': f'C{i:03}', 'customer': f'{["Gulf", "Oasis", "Emirates", "Palm", "Desert"][i%5]} { ["Foods", "Retail", "Hospitality", "Trading", "Industries", "Markets"][i%6]} {i:02}', 'payment_terms_days': [30,45,60][i%3]} for i in range(1,49)])
    skus = pd.DataFrame([{'sku_id': f'SKU{i:03}', 'sku': f'{"Recycled container" if i%2 else "Kraft carton"} {i:02}', 'category': 'plastic' if i%2 else 'paper', 'unit': 'case', 'base_price': 35+i*3, 'standard_cost': round((35+i*3)*(.55+(i%9)*.045),2)} for i in range(1,41)])
    locations = pd.DataFrame([{'location_id': f'L{i}', 'location': name} for i,name in enumerate(['Dubai','Abu Dhabi','Other Emirates','KSA'],1)])
    customer_records=customers.to_dict('records'); sku_records=skus.to_dict('records'); location_records=locations.to_dict('records')
    sales=[]; plans=[]; seq=0
    for date in pd.date_range('2023-12-01','2026-11-30'):
        season = 1 + .17 * (date.month in [6,7,8,9,10,12]) - .15 * (date.month in [1,2])
        growth = 1 + (date.year-2024)*.065
        for sku in sku_records:
            for loc in location_records:
                expected = (7+int(sku['sku_id'][-3:])%7)*sku['base_price']*season*growth
                plans.append([str(date.date()),sku['sku_id'],loc['location_id'],round(expected,2),round(expected*(.95+.025*(date.month%4)),2),'FY'+str(date.year)+' original','2026-11 snapshot'])
        if date > pd.Timestamp('2026-11-09'): continue
        for _ in range(rng.randint(28,48)):
            seq+=1; sku=rng.choice(sku_records); cust=rng.choice(customer_records); loc=rng.choice(location_records)
            qty=rng.randint(15,85)*(-1 if rng.random()<.025 else 1)
            price=round(sku['base_price']*growth*rng.uniform(.94,1.08),2); discount=round(abs(qty*price)*rng.choice([0,.02,.05,.08]),2)*(1 if qty>0 else -1)
            revenue=round(qty*price-discount,2); cogs=round(qty*sku['standard_cost']*rng.uniform(.95,1.06),2)
            sales.append([str(date.date()),'SP01',f'INV{seq//3:07}',seq%3+1,f'SO{seq//3:07}',cust['customer_id'],sku['sku_id'],loc['location_id'],'credit_note' if qty<0 else 'invoice',qty,price,discount,revenue,cogs,round(revenue*.05,2),'AED',1.0])
    # Scale financial amounts only; retain transaction volume and margin ratios.
    sales_frame = pd.DataFrame(sales, columns=['posting_date','company','invoice_id','line_number','sales_order_id','customer_id','sku_id','location_id','document_type','quantity','unit_price','discount_amount','net_revenue','cogs','tax_amount','currency','exchange_rate'])
    plan_frame = pd.DataFrame(plans, columns=['date','sku_id','location_id','budget','forecast','budget_version','forecast_version'])
    for column in ['unit_price','discount_amount','net_revenue','cogs','tax_amount']:
        sales_frame[column] = sales_frame[column] / 2
    plan_frame[['budget','forecast']] = plan_frame[['budget','forecast']] / 2
    skus[['base_price','standard_cost']] = skus[['base_price','standard_cost']] / 2
    customers.to_csv(root/'customers.csv',index=False); skus.to_csv(root/'skus.csv',index=False); locations.to_csv(root/'locations.csv',index=False)
    sales_frame.to_csv(root/'sales_lines.csv',index=False)
    plan_frame.to_csv(root/'daily_plans.csv',index=False)
    print(f'Generated {len(sales):,} sales lines and {len(plans):,} daily plan rows in {root}')

if __name__ == '__main__': generate()
