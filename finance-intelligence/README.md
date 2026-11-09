# Sustainable Packaging Intelligence

A React dashboard and FastAPI backend for financial performance, sustainable packaging operations and monthly board reporting. Node.js runs the frontend build tools and development server.

The interface uses DataPillars deep navy `#0B1F33`, electric teal `#00A6A6`, coral `#F26B5B`, slate `#667085`, warm white `#F8FAFC` and white `#FFFFFF`. It includes responsive sidebar navigation, metric cards with budget/forecast variances, three-line trends, operational reporting, board exports and grounded AI questions.

## Start On Windows

Run commands from **this folder**, which contains `package.json`, `requirements.txt`, `backend/` and `frontend/`. The repository has an outer folder with the same name; change into the inner project first if necessary.

Requirements: Python 3.11+ and Node.js 22.12+ (Node.js LTS recommended).

```powershell
# Create the virtual environment if you do not already have one.
py -m venv .venv

.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. One command launches the Node/Vite React server and FastAPI on port 8000. Keep the terminal open and press Ctrl+C to stop. If the Python launcher is unavailable, use `python -m venv .venv`. The Node launcher automatically uses this project's `.venv`; an optional `PYTHON` environment variable can override it.

If Node was just installed, fully reopen your terminal application to refresh PATH.

## Build And Run Without The Development Server

```powershell
npm run build
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. FastAPI serves the compiled React application and API from the same origin. Build before starting the backend so the asset directory is mounted. Interactive API documentation is at `/docs`.

## API Configuration

AI is optional; dashboards, uploads and exports work without a key. The backend reads `OPENAI_API_KEY` from its environment first, then the existing ignored `.streamlit/secrets.toml` file for compatibility:

```toml
OPENAI_API_KEY = "your-key-here"
```

Or set it in the terminal before `npm run dev`:

```powershell
$env:OPENAI_API_KEY = "your-key-here"
$env:OPENAI_MODEL = "gpt-4.1-mini"
npm run dev
```

Keys stay server-side. Do not add them to React source, `VITE_` variables, source datasets or Git. `.env.example` is a reference; `.env` files are not automatically loaded. API billing is separate from ChatGPT subscriptions. AI calls use the configured model, bounded read-only data tools and `store=False`. AI requests can incur usage charges.

## Reporting & Data

Use the sidebar to open **Financial Performance**, **Sustainability & Operations**, **Board Pack**, **AI Report** or **Ask Your Data**. The shared filters select a month/quarter/year, reporting period, currency label and actual-versus-budget/forecast mode. Budget & Forecast is the default and shows both planning comparisons. Changing the currency label does not convert amounts.

The bundled data is synthetic for all 12 months of 2026 and all three scenarios. Januaryâ€“February are quiet; Marchâ€“May and November are average; Juneâ€“October and December are busy. No real customer or company records are included.

**Manage Data** accepts the finance, operations and closing-balance files together in CSV/XLSX format. Files are validated before replacing the current workspace. Each file supports up to 1 MB and 100,000 rows; expanded XLSX contents are limited to 50 MB. Requests and generated responses are limited to 4 MB to fit Vercel's function limits. See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for all columns, definitions and accounting conventions. Older datasets remain supported and missing optional metrics remain unavailable.

Flows sum across months; stocks, headcount and customer credit exposure take the latest closing month; ratios recalculate. Staff costs are included in operating expenses. Return value and wastage cost are analytical measures, not additional deductions from profit. Month-presence coverage is shown for actual and planning scenarios; it is not a reconciliation to the general ledger.

Uploads and chat history are stored in a shared PostgreSQL database when `DATABASE_URL` is configured. Locally, an ignored SQLite database is created automatically in `.local/workspaces.sqlite3`. Both stores use the same versioned workspace model: browser sessions remain isolated, stale concurrent changes are rejected, and restarts do not discard data. Workspaces expire after two hours of inactivity; expired payloads are deleted when storage is accessed. Clearing browser cookies loses access to that workspace. The workspace identifier is stored hashed in the database and the browser cookie is HttpOnly. This is browser-session isolation, not user authentication. Public company use still requires login and company access controls.

Vercel requires PostgreSQL and never falls back to local files or process memory. Secure cookies are automatic on Vercel; `COOKIE_SECURE=1` enables them elsewhere. Vercel deployment/production origins are recognised automatically when system environment variables are enabled; `APP_ORIGIN` can additionally declare a trusted custom frontend origin. See [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md) for the remaining dashboard steps.

## Board Packs & AI

The **Board Pack** page downloads CSV, Excel and an editable 11-slide PowerPoint. CSV follows the selected comparison; Excel and PowerPoint include both budget and forecast. The presentation contains KPI cards, financial/operational tables, four editable trend charts and metric definitions. Examples are in `examples/`.

**AI Report** produces four management commentary cards and a Markdown download. **Ask Your Data** supports questions over the loaded files and all available periods. It executes validated read-only Python queries, returns supporting source references and identifies unsupported questions. Expand the evidence tables to review the figures. `D1` identifies the data dictionary; `S` IDs identify records or calculated differences retrieved for that answer.

The editable prompt is [prompts/data_agent.md](prompts/data_agent.md). The agent cannot execute generated Python/SQL, browse or read arbitrary files. Customer identities and SKU details are available through the separate Executive ERP chat source; they remain unavailable in the aggregate finance schemas. Verified causes are unavailable in both. Relevant results, requested source records, metric definitions, context and recent chat messages are sent to OpenAI. Source IDs are validated, but AI prose still needs human review. Chat clears when data or currency changes; Clear Chat removes the current conversation. `store=False` does not replace an organisational data-retention or residency assessment.

## Architecture

| Location | Responsibility |
| --- | --- |
| `frontend/src/main.jsx` | React pages, state, uploads, charts, AI UI and downloads |
| `frontend/src/styles.css` | Responsive DataPillars brand design system |
| `frontend/vite.config.js` | Node.js/Vite development proxy and production build |
| `scripts/dev.mjs` | Starts the frontend and Python backend together |
| `backend/main.py` | FastAPI validation, per-browser datasets, API and exports |
| `backend/storage.py` | Shared PostgreSQL workspace storage and automatic local SQLite fallback |
| `src/finance.py` | Shared deterministic KPI and scenario calculations |
| `src/query_agent.py` | Bounded read-only AI data tools and evidence validation |
| `src/ai.py` | Server-only API configuration and commentary |
| `src/board_pack.py` | Editable PowerPoint generation |
| `app.py` | Retained legacy Streamlit UI; not needed for the React application |

The React app requests the API through the same origin. Vite proxies `/api` during development; FastAPI serves the production bundle. No separate Node API duplicates the Python financial logic.

## Validation & Sample Artifacts

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm run build
npm run test:ui
.\.venv\Scripts\python.exe scripts/generate_sample_data.py
.\.venv\Scripts\python.exe scripts/export_sample_board_pack.py
```

Python tests cover aggregation, comparisons, tool restrictions, API session isolation, validated uploads, AI error handling and all export formats. Browser tests cover React filters/navigation, uploads, PowerPoint downloads, AI report/chat rendering and mobile overflow. API and browser tests simulate AI replies; they never call OpenAI. Browser tests start an isolated service on port 8765 with AI disabled, using installed Microsoft Edge on Windows. Elsewhere install Playwright Chromium or set `PLAYWRIGHT_CHANNEL` to a supported installed browser.

Storage tests exercise real SQLite databases shared across independent store instances, including restart recovery, chat/data isolation, expiry and concurrent-update rejection. They do not connect to Neon or create a cloud account. Vercel deployment must still be verified against the connected PostgreSQL database.

The optional legacy Streamlit UI needs `pip install -r requirements-legacy.txt`; its tests skip when Streamlit is absent. It is retained as a migration reference, while React/FastAPI is the primary application.

### Data Load Templates

Use **Templates** beside **Manage Data** to download a ZIP containing three sample CSV files and instructions. Upload any subset of these files. Each load replaces all workspace datasets, so omitted files are empty. Period and scenario identify each row; finance also requires account and amount headers. Numeric cells may be blank and operations/balance metric columns may be omitted. At least one actual row is required. Missing inputs and dependent metrics display **No Data**, while explicit zeros remain zero. Include all available files together when updating a workspace.

## Executive Dashboard

Open **Executive Dashboard** in the sidebar for daily revenue breakdowns, MTD and YTD sales, the same-period 2025 comparison, customer profitability, customer and SKU rankings, and revenue against budget/forecast. A separate synthetic Dynamics-style invoice-line dataset covers 36 calendar months (December 2023–November 2026), with actuals through 9 November 2026. See [EXECUTIVE_DATA.md](EXECUTIVE_DATA.md) for the schema, source mapping, accounting definitions and instructions to replace all five CSVs using `EXECUTIVE_DATA_DIR`. The Executive page uses its own date/category/location filters and AED reporting; the existing aggregate upload and AI pages do not read these extracts.

Executive ERP questions are now supported from the dashboard chat panel or by selecting **Executive Dashboard ERP data** on **Ask Your Data**. Python tools calculate filtered sales, customer/SKU rankings, margins, plan variances and period comparisons with supporting evidence. The assistant uses the existing server-side API key and AI settings; restart the backend after rebuilding to load its new endpoints. See [EXECUTIVE_DATA.md](EXECUTIVE_DATA.md).

Page-specific navy assistants are now available on Executive Dashboard, Financial Performance, and Sustainability & Operations. Each has a separate tool allowlist and chat history. There is no standalone Ask Your Data menu item. Executive period filters apply to all overview figures and charts, with nearby Day/MTD/QTD/YTD and matching-month/quarter/year comparison shortcuts.

## Troubleshooting AI locally

Local hosting supports all three data assistants. The Python server must have outbound HTTPS access to OpenAI. A server launched inside a restricted agent sandbox can serve the website but fail every AI request. Start/restart Uvicorn from a normal PowerShell terminal (or explicitly approve normal network access when the agent launches it). Rebuilding React does not change the running backend process.

AI errors now distinguish missing/invalid credentials, project permissions, exhausted quota, rate limits, model access, timeouts and connection failures without exposing credentials. `python scripts/diagnose_ai.py` makes a minimal live request using the existing server configuration, prints only a safe result category, and sends no company data. This diagnostic is separate from automated tests and can incur a small API charge.
