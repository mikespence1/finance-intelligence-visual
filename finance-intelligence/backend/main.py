"""Local FastAPI service; calculation, AI and export logic stays server-side."""
from io import BytesIO
import json
import os
from pathlib import Path
import secrets
from threading import BoundedSemaphore
from typing import Literal
from zipfile import ZipFile, BadZipFile

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.ai import generate_board_commentary
from src.board_pack import board_pack
from src.finance import build_kpis, compare_scenarios, METRIC_GROUPS
from src.presentation import format_metric, period_label, METRIC_LABELS, LOWER_BETTER, narrative_sections, title_case
from src.query_agent import ask_data
from backend.storage import get_store, WorkspaceConflict, WorkspaceTooLarge
from src.workbook import style_workbook

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title='Sustainable Packaging Intelligence', version='2.0.0')
ai_slots = BoundedSemaphore(2)
MAX_FILE = 1024 * 1024
MAX_BODY = 4 * 1024 * 1024


def database():
    try:
        return get_store()
    except Exception:
        raise HTTPException(503, 'Workspace storage is unavailable. Connect a PostgreSQL database and check DATABASE_URL in Vercel settings.') from None


def save_workspace(state):
    try:
        state.store.save(state)
    except WorkspaceConflict:
        raise HTTPException(409, 'Your workspace changed in another request. Refresh and try again.') from None
    except WorkspaceTooLarge:
        raise HTTPException(413, 'The workspace is too large. Upload a smaller reporting dataset or clear chat history.') from None
    except Exception:
        raise HTTPException(503, 'Workspace storage could not be updated. Please try again.') from None


class Selection(BaseModel):
    grain: Literal['Month', 'Quarter', 'Year'] = 'Month'
    baseline: Literal['budget', 'forecast', 'both'] = 'both'
    period: str | None = Field(default=None, max_length=16)
    currency: str = Field(default='AED', pattern=r'^[A-Za-z ]{1,8}$')


class Question(Selection):
    question: str = Field(min_length=1, max_length=4000)


def sample():
    return tuple(pd.read_csv(ROOT / 'data' / f'{name}.csv') for name in ['finance', 'operations', 'balances'])


@app.middleware('http')
async def request_guards(request, call_next):
    origin = request.headers.get('origin')
    allowed = {str(request.base_url).rstrip('/'), 'http://localhost:5173', 'http://127.0.0.1:5173', os.environ.get('APP_ORIGIN', '')}
    for variable in ['VERCEL_URL', 'VERCEL_PROJECT_PRODUCTION_URL']:
        if os.environ.get(variable):
            allowed.add('https://' + os.environ[variable])
    if request.method not in ['GET', 'HEAD', 'OPTIONS'] and origin and origin not in allowed:
        return JSONResponse({'detail': 'Origin not permitted'}, status_code=403)
    length = request.headers.get('content-length', '0')
    if length.isdigit() and int(length) > MAX_BODY:
        return JSONResponse({'detail': 'Request exceeds 4 MB. Each uploaded file must be at most 1 MB.'}, status_code=413)
    response = await call_next(request)
    if response.headers.get('content-length', '0').isdigit() and int(response.headers.get('content-length', '0')) > MAX_BODY:
        return JSONResponse({'detail': 'Reporting output exceeds 4 MB. Use a smaller dataset or reporting window.'}, status_code=413)
    if request.url.path.startswith('/api'):
        response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


def session(request: Request, response: Response):
    store = database()
    sid = request.cookies.get('finance_session')
    try:
        state = store.load(sid) if sid else None
        if sid and state is None:
            raise HTTPException(409, 'Your workspace expired. Load sample data or upload your files again.',
                headers={'Set-Cookie': 'finance_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Strict'})
        if state is None:
            sid = secrets.token_urlsafe(32)
            state = store.create(sid, {'frames': sample(), 'source': 'Synthetic Sample Data',
                                      'version': secrets.token_hex(8), 'history': []})
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, 'Workspace storage is unavailable. Please check the database connection.') from None
    response.set_cookie('finance_session', sid, httponly=True, samesite='strict', max_age=store.ttl,
                        secure=bool(os.environ.get('VERCEL')) or os.environ.get('COOKIE_SECURE') == '1')
    return state


def records(frame):
    return json.loads(frame.to_json(orient='records'))


def selected_data(state, selection):
    try:
        kpis = build_kpis(*state['frames'], selection.grain)
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(422, str(error)) from None
    labels = sorted(kpis[kpis.scenario == 'actual'].label.unique())
    if not labels:
        raise HTTPException(422, 'No actual reporting periods are available')
    period = selection.period or labels[-1]
    if period not in labels:
        raise HTTPException(422, 'Selected period has no actual data; choose an available period')
    return kpis, period, compare_scenarios(kpis, period, selection.baseline)


def coverage(state, period, grain):
    window = pd.Period(period, freq={'Month': 'M', 'Quarter': 'Q', 'Year': 'Y'}[grain])
    months = pd.period_range(window.start_time, window.end_time, freq='M')
    output = []
    for scenario in ['actual', 'budget', 'forecast']:
        for name, frame in zip(['Finance', 'Operations', 'Balances'], state['frames']):
            dates = pd.to_datetime(frame.loc[frame.scenario.astype(str).str.strip().str.lower() == scenario, 'period']).dt.to_period('M')
            output.append({'dataset': name, 'scenario': scenario, 'months': int(dates[dates.isin(months)].nunique()), 'expected': len(months)})
    return output


@app.get('/api/health')
def health():
    try:
        database().check()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, 'Workspace storage is unavailable. Check DATABASE_URL and the database connection.') from None
    return {'status': 'ok'}


@app.get('/api/dashboard')
def dashboard(selection: Selection = Depends(), state=Depends(session)):
    kpis, period, comparison = selected_data(state, selection)
    return {'period': period, 'period_title': period_label(period, selection.grain), 'source': state['source'],
            'version': state['version'], 'selection': selection.model_dump(),
            'periods': [{'value': label, 'title': period_label(label, selection.grain)}
                        for label in sorted(kpis[kpis.scenario == 'actual'].label.unique())],
            'groups': METRIC_GROUPS, 'labels': {m: title_case(METRIC_LABELS.get(m, m)) for m in comparison.Metric},
            'lower_better': sorted(LOWER_BETTER), 'comparison': records(comparison), 'history': records(kpis),
            'coverage': coverage(state, period, selection.grain)}


@app.post('/api/datasets/sample')
def reset_sample(state=Depends(session)):
    state.update(frames=sample(), source='Synthetic Sample Data', history=[], version=secrets.token_hex(8))
    save_workspace(state)
    return {'source': state['source']}


def read_upload(file):
    name = (file.filename or '').lower()
    if not name.endswith(('.csv', '.xlsx')):
        raise HTTPException(422, 'Only CSV and XLSX files are supported')
    content = file.file.read(MAX_FILE + 1)
    file.file.close()
    if not content or len(content) > MAX_FILE:
        raise HTTPException(413, 'Each file must be nonempty and at most 1 MB')
    try:
        if name.endswith('.xlsx'):
            with ZipFile(BytesIO(content)) as archive:
                if sum(info.file_size for info in archive.infolist()) > 50 * 1024 * 1024:
                    raise HTTPException(413, 'Expanded workbook exceeds 50 MB')
            frame = pd.read_excel(BytesIO(content), nrows=100001)
        else:
            frame = pd.read_csv(BytesIO(content), nrows=100001)
    except (ValueError, UnicodeError, BadZipFile, KeyError):
        raise HTTPException(422, 'Unable to read the uploaded file; check its format') from None
    if len(frame) > 100000:
        raise HTTPException(413, 'Each file supports up to 100,000 rows')
    return frame


@app.post('/api/datasets/upload')
def upload(finance: UploadFile = File(...), operations: UploadFile = File(...),
                 balances: UploadFile = File(...), state=Depends(session)):
    frames = tuple(read_upload(file) for file in [finance, operations, balances])
    try:
        kpis = build_kpis(*frames)
        if not (kpis.scenario == 'actual').any():
            raise ValueError('Uploads must include actual results')
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(422, str(error)) from None
    state.update(frames=frames, source='Uploaded Data', history=[], version=secrets.token_hex(8))
    save_workspace(state)
    return {'source': state['source']}


def ai_request(function):
    if os.environ.get('AI_DISABLED', '1' if os.environ.get('VERCEL') else '0') == '1':
        raise HTTPException(503, 'AI is disabled in this environment.')
    if not ai_slots.acquire(blocking=False):
        raise HTTPException(429, 'The analyst is busy. Please try again shortly.')
    try:
        return function()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, 'AI is unavailable. Check the server API key, model access and connection.') from None
    finally:
        ai_slots.release()


@app.post('/api/commentary')
def commentary(selection: Selection, state=Depends(session)):
    _, period, comparison = selected_data(state, selection)
    text = ai_request(lambda: generate_board_commentary(comparison, period_label(period, selection.grain),
        selection.grain, currency=selection.currency, baseline=selection.baseline))
    return {'text': text, 'sections': [{'title': title_case(title), 'body': body} for title, body in narrative_sections(text)]}


@app.get('/api/chat')
def chat_history(currency: str = Query(default='AED', pattern=r'^[A-Za-z ]{1,8}$'), state=Depends(session)):
    if state.get('history_currency') != currency:
        state.update(history=[], history_currency=currency)
        save_workspace(state)
    return {'messages': state['history']}


@app.delete('/api/chat')
def clear_chat(state=Depends(session)):
    state['history'] = []
    save_workspace(state)
    return {'messages': []}


@app.post('/api/chat')
def chat(question: Question, state=Depends(session)):
    _, period, _ = selected_data(state, question)
    if not question.question.strip():
        raise HTTPException(422, 'Enter a question')
    version = state['version']
    if state.get('history_currency') != question.currency:
        state.update(history=[], history_currency=question.currency)
    result = ai_request(lambda: ask_data(question.question, *state['frames'],
        {'currency': question.currency, 'selected_period': period, 'grain': question.grain,
         'baseline': question.baseline, 'data_source': state['source']}, history=state['history']))
    if state['version'] != version or state.get('history_currency') != question.currency:
        raise HTTPException(409, 'Data changed during the question. Please ask again.')
    state['history'] = (state['history'] + [{'role': 'user', 'content': question.question},
                         {'role': 'assistant', 'content': result['answer'], 'reply': result}])[-20:]
    save_workspace(state)
    return result


@app.get('/api/definitions')
def definitions():
    return {'text': (ROOT / 'DATA_DICTIONARY.md').read_text(encoding='utf-8')}


@app.get('/api/exports/{kind}')
def export(kind: Literal['csv', 'xlsx', 'pptx'], response: Response, selection: Selection = Depends(), state=Depends(session)):
    kpis, period, comparison = selected_data(state, selection)
    title = period_label(period, selection.grain)
    filename = f'sustainable_packaging_board_{period}.{kind}'
    if kind == 'csv':
        frame = comparison.copy()
        frame.insert(0, 'Reporting Period', title)
        frame.insert(1, 'Currency', selection.currency)
        content, mime = frame.to_csv(index=False).encode('utf-8-sig'), 'text/csv'
    elif kind == 'xlsx':
        output = BytesIO()
        frame = compare_scenarios(kpis, period, 'both')
        frame.insert(0, 'Reporting Period', title)
        frame.insert(1, 'Currency', selection.currency)
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            frame.to_excel(writer, sheet_name='Board KPIs', index=False)
            kpis.to_excel(writer, sheet_name='KPI History', index=False)
            style_workbook(writer.book)
        content, mime = output.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else:
        notes = '; '.join(f"{row['dataset']}: {row['months']}/{row['expected']} months" for row in coverage(state, period, selection.grain) if row['scenario'] == 'actual')
        content = board_pack(kpis, period, selection.grain, selection.currency, state['source'], notes)
        mime = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    if response.headers.get('set-cookie'):
        headers['Set-Cookie'] = response.headers['set-cookie']
    return Response(content, media_type=mime, headers=headers)


# After npm run build, FastAPI serves the React application from the same origin.
DIST = ROOT / 'frontend' / 'dist'
if DIST.is_dir():
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')


@app.get('/')
def index():
    if (DIST / 'index.html').is_file():
        return FileResponse(DIST / 'index.html')
    return JSONResponse({'detail': 'Build the React frontend with npm run build, or use the Vite development server.'}, status_code=503)
