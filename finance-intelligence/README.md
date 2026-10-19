# Packaging Finance Intelligence — Starter MVP

A GitHub-ready, local-first financial management dashboard for a packaging manufacturer. It uses **deterministic** financial calculations and optional **OpenAI** management commentary.

## Features
- CSV/Excel imports for P&L accounts, production data and month-end balance-sheet figures.
- Month, quarter, year grouping; flows sum, period-end balances take last month, ratios recalculate from underlying amounts.
- Revenue, gross profit, EBITDA, EBIT, net profit, margins, output, scrap, DSO/DIO/DPO, cash-conversion cycle.
- Actual vs budget dashboards, downloadable Excel board data pack, optional AI narrative.
- Synthetic sample data for all 12 months of 2026. **Not real company data.**

## Windows / VS Code quick start
1. Download and extract the zip, and open its folder in VS Code.
2. Open a terminal (PowerShell):
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python -m pytest -q
   streamlit run app.py
   ```
3. To use AI, set `OPENAI_API_KEY` as an environment variable (or use an ignored `.streamlit/secrets.toml` and adapt `src/ai.py` to read it). For PowerShell in the current terminal:
   ```powershell
   $env:OPENAI_API_KEY="your_api_key_here"
   $env:OPENAI_MODEL="gpt-4.1-mini"
   streamlit run app.py
   ```
4. Without an API key, dashboards still run; only AI commentary is unavailable.

**API access:** A ChatGPT subscription/token allowance is not the same as API billing. Use an API key and available model from your OpenAI API account. Model selection is configurable via `OPENAI_MODEL`. Usage incurs API charges.

## Upload schemas
Upload all three data sets together using CSV or Excel `.xlsx`. See `data/` for exact column names and sample values.

### finance.csv
`period,scenario,account,amount` where `scenario` is `actual` or `budget`; `account` must be one of: `Revenue`, `Cost of Sales`, `Operating Expenses`, `Depreciation`, `Interest`, `Tax`. **Revenue and expenses both use positive amounts**. Negative entries are blocked in the starter. Multiple entries by account/month are aggregated. `period` is parsed as date; calendar months are used.

### operations.csv
`period,scenario,production_tonnes,scrap_tonnes,energy_cost`. Monthly flows; avoid mixed units. Distinguish good tonnes from scrap tonnes; scrap rate = scrap/(good + scrap).

### balances.csv
`period,scenario,Cash,Accounts Receivable,Inventory,Accounts Payable,Debt`. Exactly one **month-end closing** row per period/scenario. Balance fields are signed where appropriate but check accounting sign conventions. Quarter/year values use latest month available (even if period is incomplete).

For accurate P&L, actual and budget must each contain the expected account categories for every reporting period. Missing financial account combinations currently behave as zero and therefore must be reviewed by Finance. This starter assumes the same currency, corporate entity and fiscal calendar for every record, no eliminations, and no VAT handling. It is not an accounting system.

## Important data-quality notes
- The MVP is a prototype with browser-session uploads, not a transactional datastore; uploaded files are **not persisted** across sessions.
- Period coverage, cut-off completeness, reconciliation to the GL, fiscal-calendar rules, chart-of-accounts mapping, consolidated FX translation, restatements, approved budgets, access control and data lineage must be implemented before board use.
- DSO/DIO/DPO use ending balances and revenue/COGS for the selected period. Finance may prefer average balances and alternate conventions; validate formulas with the company controller.
- Uploaded input files are handled locally in the Streamlit process. The AI button sends **selected computed KPI values** to the configured OpenAI API. This is still company financial information: **do not use live confidential data until the organisation approves the provider, jurisdiction, retention controls, contract and deployment**. `store=False` is set on the Responses API request, but is not a substitute for a full security and data residency assessment.
- No authentication or row-level security is included. Deploy behind suitable controls; do not expose this prototype publicly.

## Suggested production roadmap
1. Define chart-of-accounts mappings, formal metric definitions, fiscal calendar, entities and currency; add reconciliations and a sign-off workflow.
2. Add sales/invoice lines, SKU/customer/material dimensions, operations by plant/line, pricing and contribution analysis.
3. Introduce a relational warehouse (PostgreSQL/Azure SQL), role-based access, audited upload versions, change history, budget/forecast versions, secure file storage, automated tests and CI.
4. Build structured AI JSON outputs with citations to metric IDs, approved drill-through queries, a controlled board narrative and human approval.
5. Add cash flow statements, balance sheet statement mapping, 13-week cash forecast, scenario planning, forecasts, CAPEX and consolidated/group reporting.

## GitHub workflow
```bash
git init
git add .
git commit -m "Initial packaging finance MVP"
git branch -M main
git remote add origin https://github.com/YOUR_ACCOUNT/packaging-finance-intelligence.git
git push -u origin main
```
Create a **private** repository first. Do not commit credentials or proprietary financial uploads.
