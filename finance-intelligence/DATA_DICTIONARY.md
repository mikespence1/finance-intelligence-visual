# Sustainable packaging reporting data

All three CSV/XLSX inputs use `period` (calendar month, e.g. `2026-01-01`) and `scenario` (`actual`, `budget`, `forecast`). Values share one reporting currency and entity. Forecast is one planning snapshot supplied by Finance; it is not an automatically generated prediction. Replace that snapshot when revising the forecast.

## Finance

Columns: `period,scenario,account,amount`. Revenue and expenses use positive amounts. Allowed accounts: Revenue, Cost of Sales, Operating Expenses, Staff Costs, Depreciation, Interest, Tax.

**Staff Costs is a disclosure within Operating Expenses.** Include staff costs in Operating Expenses and also provide the Staff Costs row to expose the breakdown. Staff Costs must not exceed Operating Expenses. Payroll allocated to manufacturing must be mapped consistently before import; this prototype's Staff Costs disclosure covers operating expenses only. EBITDA = Revenue − Cost of Sales − Operating Expenses. Other operating expenses = Operating Expenses − Staff Costs if supplied. Missing core finance accounts retain the starter's zero treatment and require reconciliation before reporting. Missing Staff Costs is unavailable.

## Operations

One or more rows per month/scenario. All measures are period flows and sum across months; optional missing values remain unavailable. Every numeric value must be finite and nonnegative.

| Column | Meaning |
| --- | --- |
| production_tonnes | Good finished packaging output; excludes scrap |
| scrap_tonnes | Material wastage generated, including recoverable scrap |
| energy_cost | Energy expense disclosure; already included in finance costs |
| orders_shipped | Orders dispatched during the period; whole number |
| returned_orders | Orders returned during the period; whole number |
| returned_order_value | Value of returns recorded during the period |
| waste_cost | Cost assigned to wasted material; already included in finance costs |
| material_input_tonnes | Total material consumed by production |
| recycled_input_tonnes | Recycled material consumed; cannot exceed material input |
| waste_recovered_tonnes | Scrap recovered for reuse/recycling; cannot exceed scrap |

The original five columns through energy_cost remain required. Additional columns are optional for older datasets. For multiple rows, any missing optional value makes the aggregated value unavailable rather than silently treating it as zero.

Wastage rate = scrap / (good output + scrap). Recycled input % = recycled inputs / material inputs. Waste recovery % = recovered scrap / scrap. Return rate = returned orders / orders shipped in the same reporting period, not a shipment-cohort return measure; returns can relate to earlier shipments. Quarter/year ratios recalculate from total numerators and denominators. Zero denominators yield unavailable, not zero.

Return value and waste cost are analytical disclosures. They do not reduce profit again. Revenue must already reflect any booked return credits, and finance costs must already reflect waste.

## Closing balances

Exactly one row per month/scenario. The latest available month is used for quarter/year closing balances and headcount; they are never summed across months.

Required: `Cash,Accounts Receivable,Inventory,Accounts Payable,Debt` (currency amounts).

| Additional column | Unit / definition |
| --- | --- |
| Raw Material Stock Tonnes | Closing raw-material quantity, tonnes |
| Finished Goods Stock Tonnes | Closing finished packaging quantity, tonnes |
| Customer Credit Limit | Total approved customer credit limits, currency |
| Overdue Receivables | Overdue portion of Accounts Receivable |
| Material Payables | Materials-related portion of Accounts Payable |
| Overdue Material Payables | Overdue portion of Material Payables |
| Headcount | Closing employee count; whole number |

Additional columns must be finite and nonnegative; overdue amounts cannot exceed their parent balances. Material Payables cannot exceed Accounts Payable. Inventory is the total stock value; the two stock quantity fields provide separate physical measures without an implied valuation conversion.

Outstanding customer credit = Accounts Receivable. Headroom = Customer Credit Limit − Accounts Receivable; negative headroom indicates aggregate excess exposure. Credit utilisation = Accounts Receivable / Customer Credit Limit. Aggregate headroom does not prove every customer is within their individual limit. Customer-level ageing, credit insurance and collection schedules are not included.

## Comparisons and coverage

Actual minus budget/forecast is the variance. Rate differences use percentage points, while variance % is the relative change from the comparator. Missing comparator data stays unavailable. Expense/waste/returns reductions are displayed as favourable; other metrics may require management interpretation. Coverage counts show months present, not GL completeness or a reconciliation. Partial periods are flagged; working-capital day ratios still use the full calendar window.

## Board outputs

The Board pack tab exports the selected month, quarter or year as CSV, Excel and an editable 11-slide PowerPoint. Excel and PowerPoint include both budget and forecast comparisons. Slides include headline cards, financials, circularity, returns, stock/credit, supplier/people/cash, four editable trend charts and reporting definitions. PowerPoint uses the local python-pptx dependency and needs no API key or PowerPoint installation to generate.

Run `python scripts/generate_sample_data.py` to regenerate the 12-month, three-scenario synthetic dataset. Run `python scripts/export_sample_board_pack.py` to reproduce the December example PowerPoint and Excel files in `examples/`. All supplied numbers are synthetic, not measured sustainability outcomes or real company data.
