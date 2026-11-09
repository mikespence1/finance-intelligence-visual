# Executive Dashboard: Dynamics extract contract

The separate React Executive Dashboard reads five normalized CSV files from `data/executive` by default. The fixture is synthetic, not a live Dynamics connection. It spans December 2023–November 2026 (36 calendar months), with actual postings through 9 November 2026 and daily plans through 30 November. Generated values use a fixed seed. Regenerate with `.venv/Scripts/python.exe scripts/generate_executive_data.py`.

## Replace the sample

Export and normalize your Microsoft Dynamics data to the exact headers in the five supplied CSVs. Set `EXECUTIVE_DATA_DIR` to their containing directory before launching the backend, then restart it. The server caches extracts until restart. This setting is server-wide; use it only for an approved shared dataset. The existing Manage Data upload and AI pages continue to use their original aggregate data. No credentials or live Dynamics integration are included.

Dynamics products and customizations differ. Have your Dynamics administrator map the appropriate invoice headers and lines, customer master, released products, inventory dimensions, posted cost transactions and approved plan versions into this contract. Raw OData entity names are intentionally not assumed. Use posted documents only and reconcile net revenue and COGS to the general ledger. Collapse cost adjustments into each original invoice line before export; do not duplicate the revenue line when joining inventory cost transactions.

## Files and grain

- `sales_lines.csv`: one posted invoice/credit-note line; unique `(company, invoice_id, line_number)`. `posting_date` is the accounting date (ISO YYYY-MM-DD); `sales_order_id` retains order traceability. `customer_id`, `sku_id`, `location_id` join to the master files. `document_type` is invoice or credit_note. `quantity` is signed cases; `unit_price` is AED/case; `discount_amount` is signed AED. `net_revenue = quantity * unit_price - discount_amount`, excluding VAT. `cogs` is signed posted cost, including allocated landed costs and subsequent inventory close adjustments. `tax_amount` is informational and excluded from revenue. Credit notes reverse quantity, discount, revenue, cost and tax. `currency` must be AED, the accounting currency, and `exchange_rate` is source-to-accounting currency (1 in the fixture). Convert transaction currency amounts before loading; the dashboard does no FX conversion.
- `customers.csv`: one `customer_id`, display `customer`, `payment_terms_days`.
- `skus.csv`: one `sku_id`, display `sku`, `category` (plastic/paper), `unit`, indicative `base_price`, `standard_cost`. Dashboard profitability uses actual line COGS, not master standard cost. Use unique display names because tables group by display name.
- `locations.csv`: one `location_id`, display `location`; warehouse/site attribution comes from each posted line.
- `daily_plans.csv`: one date × SKU × location for the selected plan versions, with `budget`, `forecast` in AED, plus `budget_version`, `forecast_version`. No customer allocation is implied. When exporting monthly plans, allocate to days using your approved trading-day weights before loading. The fixture evenly distributes modeled expectations across days; it uses one original annual budget and one frozen forecast snapshot, not historical forecast vintages. Keep only one chosen budget/forecast version per grain; otherwise plans will double count.

## Calculation and coverage

Daily revenue sums net posted revenue on the selected date. MTD runs from month start through that date; YTD runs from 1 January. The prior-year comparison uses the same cutoff last year (29 February maps to 28 February). A separate 2025 comparison always uses 1 January 2025 through the matching month/day in 2025; when viewing 2025 it naturally shows zero change. Baselines outside extract coverage are unavailable. No percentage is reported for a zero denominator.

Gross profit = net revenue - COGS. Gross margin = summed gross profit / summed net revenue × 100, never an average of line margins. It is not operating/net profit. Customer and SKU rankings use MTD; the full customer profitability table includes every customer with MTD activity. Margin rankings exclude nonpositive net revenue; credit notes remain in all totals. SKUs with no activity do not enter rankings. Top/bottom SKU lists can be ranked independently by revenue, gross margin percentage or gross profit. Daily breakdowns use the selected day. Category/location filters apply to actuals and plans consistently.

Budget and forecast comparisons sum daily plans to the same MTD cutoff; variance = actual - plan and variance % = variance / abs(plan) × 100. Trends retain months up to the as-of date. MoM compares the available selected month against the previous full month and is explicitly labeled when partial. Coverage begins in December 2023, so 2023 YTD and its prior baseline are partial/unavailable. The fixture has no missing trading days; for real extracts, verify completeness independently. Absence of transactions is treated as zero activity, not evidence that the extract is complete.

All files must contain matching dimension keys and numeric finite amounts. Load validation rejects duplicate invoice lines, duplicate master keys, missing dimensions and non-AED sales. Extend this contract and add entity filters before combining legal entities that reuse customer/product IDs. Use costs and overhead allocations approved by finance before making customer profitability decisions.

## Updated sample scale and analysis controls

The fixture generator scales all financial values (prices, discounts, revenue, cost, tax, budget and forecast) to 50% of the original fixture, retaining transaction quantities and margin ratios. Half-cent precision is retained to preserve exact halving and line arithmetic. Locations are Abu Dhabi, Dubai, Other Emirates and KSA. All values remain in the AED reporting currency, including KSA; these are sales markets rather than separate legal entities.

The dashboard is arranged into Sales Overview, Customer Performance, SKU Performance, and Trends & Comparisons. The analysis period supports selected day, MTD (default), QTD, YTD or custom start through as-of date. It applies to customer/SKU rankings and revenue breakdowns. Headline daily/MTD/YTD metrics and MTD plan comparisons retain their named periods. Trends show history through the as-of date. Category/location apply throughout. Customer ranking controls support revenue, gross profit or gross margin, top/bottom 5/10/20 and customer-name search. These controls supersede the MTD-only descriptions above. The API accepts `period=day|mtd|qtd|ytd|custom` and `start_date=YYYY-MM-DD` for custom analysis.

## Ask Executive Data

The Executive Dashboard now includes an **Ask your Executive data** panel. It defaults questions to that page's analysis date range, category and location; explicit questions can request other periods or filters. **Ask Your Data** also offers a **Data source for questions** selector: choose **Executive Dashboard ERP data** for the same chat with its own period filters, or keep **Financial & operational reports** for the original aggregate datasets.

Executive chat uses the same server-side OpenAI key and AI enablement settings as the existing assistant. It exposes a bounded read-only `query_executive` tool: Python computes totals, gross profit, weighted margins, top/bottom rankings, trends, budget/forecast variances and optional exact-date period comparisons. No generated SQL or Python runs. Answers include source IDs and expandable supporting calculations. Relevant aggregated records (including customer/SKU names when requested), filters and recent messages go to OpenAI. No full extract is uploaded to the model. Live API calls may incur charges.

ERP chat history is stored separately from the financial-report chat. It resets when the ERP extract revision or selected period/category/location changes and remains isolated by the existing browser workspace cookie. Customer-level budgets, net profit/overhead allocations and verified business causes are not supported. Dates outside source coverage produce unavailable totals, not invented zeros. Source completeness still needs reconciliation.

After rebuilding locally, **restart the Python backend** so the new Executive chat endpoints are loaded, then refresh your browser. Tests use mocked model responses; running the tests does not call OpenAI.

## Visual period comparisons

Customer/SKU rankings and revenue breakdowns now use rounded horizontal bar charts in DataPillars teal, navy, coral and slate. Exact values remain under **View exact figures**. Click a bar or choose **Trend focus** to compare a single entity; otherwise the trend follows the fixed set of currently displayed entities across all periods (never a different historical top/bottom list).

Each ranking has cumulative progress lines for the selected period, the same time last month, and the same time last year. Revenue/gross profit accumulate from the start of each window; gross margin recalculates from accumulated gross profit and revenue rather than summing/averaging percentages. Daily selection provides one point per series; choose a longer analysis period for a longer trend. Named period starts (MTD/QTD/YTD) recalculate from the shifted as-of date; custom ranges shift both start/end dates by a calendar month/year. Month-end and leap-day dates clamp to the last valid day. Explicit dates and day counts appear next to totals; lines stop at each period's cutoff. Comparisons outside extract boundaries are unavailable. Missing transaction dates inside coverage are treated as zero activity; completeness still requires reconciliation.

Changes are selected-period minus comparison-period; gross margin changes use percentage points. Plans remain at SKU/location grain. The plan panel also has rounded actual/budget/forecast bars and an MTD progress chart; monthly history has paired revenue/gross-profit bars with exact monthly values available to expand.

## Page layouts and scoped assistants

Executive and Financial Performance now have persistent navy question panels. The Executive panel exposes only the Executive metrics and ERP dimensions. The Financial panel uses `/api/financial/chat` and a server-enforced tool allowlist for the Financial Performance page; sustainability/returns/ERP identities cannot be retrieved by those tools. Its conversation is separate from the Executive and legacy aggregate chats. Histories still use browser-workspace storage and existing AI configuration. Model tests use mocked API responses.

Sales Overview charts are vertical. Customer and product rankings default to top/bottom 10, and bar/line colours use teal, navy and slate. Exact ranking values remain expandable. Metric labels include short hover/focus explanations and expanded acronyms. The Executive coverage block and shared Sustainable Growth badge have been removed.

Sustainability & Operations uses four operational headline rates (scrap, recycled inputs, recovery and returns), followed by four theme buttons. Each theme has one selected trend, three compact supporting measures and expandable full metric/plan cards. This replaces the long wall of cards and repeated financial headlines while keeping every original operational metric available.

## Unified Executive periods and Operations questions

All Executive Sales Overview headline values, Actual/Budget/Forecast bars, plan variances, monthly histories and breakdowns now use the selected analysis date range. The previous fixed MTD plan chart and separately named daily/YTD cards have been replaced by selected-period sales, gross profit, gross margin and matching-period sales change versus last year. Day/MTD/QTD/YTD shortcuts update the same top-level filter. Compact plan bars leave room beside the chart for period and comparison buttons.

Comparison buttons choose matching cutoffs last month, quarter (three calendar months) or year, or show all comparisons. Selected-day mode compares the corresponding individual dates; MTD/QTD/YTD restart at their relevant calendar boundary, while custom periods shift both dates. Month-end and leap dates clamp to valid calendar dates. The comparison selection applies to all Executive entity/trend visuals. Period changes also filter the monthly history tab; boundary months may be partial.

The standalone Ask Your Data navigation item and sidebar slogan have been removed. Sustainability & Operations now has its own navy question panel, `/api/operations/chat`, independent history and server-side metric allowlist. It supports only that page's operational, stock, credit, supplier, cash/headcount and working-capital measures. It cannot retrieve revenue/profit/EBITDA metrics or raw finance/Executive ERP records. Working-capital ratios may use financial denominators internally without exposing P&L metrics as query results. Existing API-key/AI settings apply. Tests mock model responses and do not incur API charges.

## Compact dashboard redesign

Reporting controls now live vertically in the existing left sidebar above page navigation. Executive filters are rendered into that shared sidebar while retaining the Executive page's own state and query context. Financial/Operations period, scenario and currency controls use the same panel position. On small screens the existing navigation drawer exposes these filters.

All three pages start with four full-width navy/teal metric cards, recent-history sparklines and compact reporting badges, followed by charts and their scoped assistant. Explanations remain on metric hover/focus; detailed financial tables are expandable. Operational themes and supporting cards remain interactive.

Executive defaults to real MTD within its dated invoice-line extract. Finance/Operations default to Month and prefer the current Dubai calendar month when available, falling back to the latest earlier month (or the available source period when all data is later). Their inputs remain monthly aggregates and are labelled **Monthly source totals**. They cannot honestly represent daily MTD cutoffs without daily extracts; no values are prorated or fabricated. Future actuals after the selected financial/operational period are hidden from trend lines, while planning series remain available.
