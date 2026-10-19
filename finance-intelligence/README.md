# Sustainable Packaging Intelligence

A React dashboard and FastAPI backend for financial performance, sustainable packaging operations and monthly board reporting. Node.js runs the frontend build tools and development server.

The interface uses forest green `#123F36`, secondary green `#2A6B5C`, gold `#C49A45` and cream `#E8DCC4`. It includes responsive sidebar navigation, metric cards with budget/forecast variances, three-line trends, operational reporting, board exports and grounded AI questions.

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

The bundled data is synthetic for all 12 months of 2026 and all three scenarios. January–February are quiet; March–May and November are average; June–October and December are busy. No real customer or company records are included.

**Manage Data** accepts the finance, operations and closing-balance files together in CSV/XLSX format. Files are validated before replacing the current workspace. Each file supports up to 1 MB and 100,000 rows; expanded XLSX contents are limited to 50 MB. Requests and generated responses are limited to 4 MB to fit Vercel's function limits. See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for all columns, definitions and accounting conventions. Older datasets remain supported and missing optional metrics remain unavailable.

Flows sum across months; stocks, headcount and customer credit exposure take the latest closing month; ratios recalculate. Staff costs are included in operating expenses. Return value and wastage cost are analytical measures, not additional deductions from profit. Month-presence coverage is shown for actual and planning scenarios; it is not a reconciliation to the general ledger.

Uploads and chat history are stored in a shared PostgreSQL database when `DATABASE_URL` is configured. Locally, an ignored SQLite database is created automatically in `.local/workspaces.sqlite3`. Both stores use the same versioned workspace model: browser sessions remain isolated, stale concurrent changes are rejected, and restarts do not discard data. Workspaces expire after two hours of inactivity; expired payloads are deleted when storage is accessed. Clearing browser cookies loses access to that workspace. The workspace identifier is stored hashed in the database and the browser cookie is HttpOnly. This is browser-session isolation, not user authentication. Public company use still requires login and company access controls.

Vercel requires PostgreSQL and never falls back to local files or process memory. Secure cookies are automatic on Vercel; `COOKIE_SECURE=1` enables them elsewhere. Vercel deployment/production origins are recognised automatically when system environment variables are enabled; `APP_ORIGIN` can additionally declare a trusted custom frontend origin. See [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md) for the remaining dashboard steps.

## Board Packs & AI

The **Board Pack** page downloads CSV, Excel and an editable 11-slide PowerPoint. CSV follows the selected comparison; Excel and PowerPoint include both budget and forecast. The presentation contains KPI cards, financial/operational tables, four editable trend charts and metric definitions. Examples are in `examples/`.

**AI Report** produces four management commentary cards and a Markdown download. **Ask Your Data** supports questions over the loaded files and all available periods. It executes validated read-only Python queries, returns supporting source references and identifies unsupported questions. Expand the evidence tables to review the figures. `D1` identifies the data dictionary; `S` IDs identify records or calculated differences retrieved for that answer.

The editable prompt is [prompts/data_agent.md](prompts/data_agent.md). The agent cannot execute generated Python/SQL, browse or read arbitrary files. Customer identities, SKU details and verified causes are not present in the supported aggregate schemas. Relevant results, requested source records, metric definitions, context and recent chat messages are sent to OpenAI. Source IDs are validated, but AI prose still needs human review. Chat clears when data or currency changes; Clear Chat removes the current conversation. `store=False` does not replace an organisational data-retention or residency assessment.

## Architecture

| Location | Responsibility |
| --- | --- |
| `frontend/src/main.jsx` | React pages, state, uploads, charts, AI UI and downloads |
| `frontend/src/styles.css` | Responsive green/gold/cream design system |
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
