# Packaging Finance Intelligence — Starter MVP

A local-first management dashboard for a sustainable packaging manufacturer, covering financial performance, materials and circularity, returned orders, stock, customer credit exposure, supplier payments and people costs. It uses deterministic calculations and optional OpenAI commentary.

See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for the current upload schema, metric definitions and accounting conventions. The included dataset covers January–December 2026 with actual, budget and forecast scenarios. The Board pack tab now exports CSV, Excel and an editable PowerPoint presentation. Example monthly outputs are in `examples/`.

## Features
- CSV/Excel imports for P&L accounts, production data and month-end balance-sheet figures.
- Month, quarter, year grouping; flows sum, period-end balances take last month, ratios recalculate from underlying amounts.
- Revenue, gross profit, EBITDA, EBIT, net profit, margins, output, scrap, DSO/DIO/DPO, cash-conversion cycle.
- Actual vs budget/forecast dashboards, downloadable Excel and PowerPoint board packs, optional AI narrative cards.
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

## Dashboard presentation
- Navy, teal and white theme configured in `.streamlit/config.toml`.
- Month names, quarter date ranges and calendar years appear in selectors, charts and downloads. The selected reporting window shows actual monthly coverage; partial periods are flagged.
- Headline and operational metric cards include budget comparisons. Margin differences use percentage points.
- The performance chart uses a solid actual line and dashed budget line, with the selected period marked. Missing values remain gaps.
- AI commentary appears in report cards and stays available during the session. Switching the reporting context hides the previous report until regenerated.

## Ask Your Data

The **Ask Your Data** tab provides a read-only question assistant over the currently loaded finance, operations and closing-balance files. It can query available months, quarters and years, compare actuals against budget/forecast, inspect supported source records and explain metric definitions. Questions default to the dashboard selection unless another period is specified.

Setup from the project directory (the folder containing `app.py`):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Configure `OPENAI_API_KEY` in your ignored `.streamlit/secrets.toml` or the terminal environment. The assistant shares the existing API configuration and `OPENAI_MODEL` environment setting. No separate GPT creation, agent service, vector database or file upload to OpenAI is needed. The editable instruction prompt is [prompts/data_agent.md](prompts/data_agent.md).

Try “How did EBITDA compare with budget in Q1 2026?” or “How did material wastage change between Q1 and Q2?” Expand **Supporting Data & Calculations** to inspect the cited figures. `D1` refers to the supplied data dictionary; `S` references identify records or Python-calculated differences retrieved for that answer.

The model selects validated tools; Python performs aggregation and comparisons. The agent has no arbitrary code, SQL, filesystem or web tool. Requests and retrieval size are bounded. Unsupported questions return a standard not-covered response; unclear questions can request clarification. The application validates source IDs but does not independently verify every sentence of AI prose, so answers require review. Customer identities, product detail and verified causes are not present in the aggregate schemas. New custom columns need explicit schema/tool support.

Relevant retrieved source records, results, schema/metric definitions, dashboard context and the last few chat messages are sent to OpenAI when a question is submitted. API calls use `store=False`; this is not a complete data retention or residency policy. Chat is held in the browser session, bounded to recent messages, and cleared when datasets, data source or currency change. **Clear Conversation** removes the displayed history. Never include credentials in a question or source file.

Automated tests use a simulated API client and do not send data to OpenAI. Run `python -m pytest -q` to check calculations, tool restrictions, citations, unsupported-result handling and chat UI behaviour.

## Upload schemas

See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) and the CSV files in data/ for all required and optional columns, units, actual/budget/forecast scenarios, and aggregation rules. Older datasets remain supported; missing extended metrics display as unavailable.

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
