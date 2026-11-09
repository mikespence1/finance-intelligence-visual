import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { AreaChart as ChartIcon, ArrowDownToLine, ArrowRight, ArrowUpRight, Check, ChevronRight, CircleHelp, FileChartColumn, Leaf, LoaderCircle, MessageSquareText, PanelLeftClose, PanelLeftOpen, RefreshCw, Send, ShieldCheck, Sparkles, Sprout, Upload, Users, Wallet, X } from 'lucide-react';
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import Markdown from 'react-markdown';
import './styles.css';
import ExecutiveDashboard from './ExecutiveDashboard';
import FinancialChat from './FinancialChat';
import OperationsOverview from './OperationsOverview';
import MetricInfo from './MetricInfo';

const PAGES = [
  ['Executive Dashboard', ChartIcon, 'Executive'],
  ['Financial Performance', ChartIcon, 'Performance'],
  ['Sustainability & Operations', Sprout, 'Operations'],
  ['Board Pack', FileChartColumn, 'Board Pack'],
  ['AI Report', Sparkles, 'AI Report'],
];
const initial = { grain: 'Month', baseline: 'both', period: '', currency: 'AED' };
const comparisons = baseline => baseline === 'both' ? ['budget', 'forecast'] : [baseline];
const title = text => text.replace(/\b[a-z]+/g, word => word[0].toUpperCase() + word.slice(1));
function params(selection) { return new URLSearchParams(Object.entries(selection).filter(([, value]) => value !== '')); }
async function api(url, options = {}) {
  const response = await fetch(`/api${url}`, { credentials: 'same-origin', ...options });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === 'string' ? error.detail : 'Please check your inputs and try again.');
  }
  return response.json();
}
const post = body => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
function unit(metric, currency) {
  if (metric.includes('%')) return '%';
  if (metric.endsWith('_tonnes') || metric.endsWith('Stock Tonnes')) return 'tonnes';
  if (['DSO', 'DIO', 'DPO', 'Cash Conversion Cycle', 'Days'].includes(metric)) return 'days';
  if (['returned_orders', 'orders_shipped'].includes(metric)) return 'orders';
  if (metric === 'Headcount') return 'people';
  return currency;
}
function number(value, metric, currency, compact = false) {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'No Data';
  const suffix = unit(metric, currency);
  const formatted = new Intl.NumberFormat('en', { maximumFractionDigits: ['%', 'days', 'tonnes'].includes(suffix) ? 1 : compact ? 1 : 0,
    notation: compact && Math.abs(value) >= 1000000 ? 'compact' : 'standard' }).format(value);
  return suffix === currency ? `${currency} ${formatted}` : `${formatted}${suffix === '%' ? '%' : ` ${suffix}`}`;
}
function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob), link = document.createElement('a');
  link.href = url; link.download = filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function variance(row, target, selection) {
  const both = selection.baseline === 'both';
  const delta = row[both ? `Variance vs ${title(target)}` : 'Variance'];
  const relative = row[both ? `Variance % vs ${title(target)}` : 'Variance %'];
  return { delta, text: delta == null ? 'No Data' : row.Metric.includes('%') ? `${delta >= 0 ? '+' : ''}${delta.toFixed(1)} pp`
    : relative != null ? `${relative >= 0 ? '+' : ''}${relative.toFixed(1)}%`
    : `${delta >= 0 ? '+' : ''}${number(delta, row.Metric, selection.currency)}` };
}

function MetricCard({ metric, data, selection, headline = false }) {
  const row = data.comparison.find(item => item.Metric === metric);
  if (!row) return null;
  const inversed = data.lower_better.includes(metric);
  return <article className={`metric-card ${headline ? 'headline' : ''}`}>
    <div className="metric-title"><MetricInfo metric={metric}>{data.labels[metric] || metric}</MetricInfo>{headline && <ArrowUpRight size={16} aria-hidden="true"/>}</div>
    <div className="metric-value" title={number(row.Actual, metric, selection.currency)}>{unit(metric, selection.currency) === selection.currency && row.Actual != null ? <><small>{selection.currency}</small><span>{number(row.Actual, metric, selection.currency, true).slice(selection.currency.length+1)}</span></> : number(row.Actual, metric, selection.currency, true)}</div>
    <div className="metric-comparisons">{comparisons(selection.baseline).map(target => {
      const change = variance(row, target, selection), favorable = change.delta == null ? null : inversed ? change.delta <= 0 : change.delta >= 0;
      return <div key={target}><span><i className={target}/>{title(target)} <b>{number(row[title(target)], metric, selection.currency, true)}</b></span>
        <span className={`delta ${favorable === null ? '' : favorable ? 'positive' : 'negative'}`}>{change.text}</span></div>;
    })}</div>
  </article>;
}

function Trend({ data, metric, selection }) {
  const labels = [...new Set(data.history.map(row => row.label))].sort();
  const points = labels.map((label, index) => ({ index, label, ...Object.fromEntries(['actual', 'budget', 'forecast'].map(scenario =>
    [scenario, data.history.find(row => row.label === label && row.scenario === scenario)?.[metric] ?? null])) }));
  const short = index => {
    const label = labels[Math.round(index)];
    if (!label) return '';
    if (selection.grain === 'Month') return new Date(`${label}-01T12:00:00`).toLocaleDateString('en', { month: 'short', year: '2-digit' });
    return label.replace(/(\d{4})Q(\d)/, 'Q$2 $1');
  };
  const ticks = points.filter((_, i) => i % Math.max(1, Math.ceil(points.length / 12)) === 0 || i === points.length - 1).map(p => p.index);
  return <div className="trend-wrap" role="img" aria-label={`${data.labels[metric] || metric} actual versus ${selection.baseline === 'both' ? 'budget and forecast' : selection.baseline} trend`}>
    <ResponsiveContainer width="100%" height={330}>
      <LineChart data={points} margin={{ top: 15, right: 20, bottom: 15, left: 10 }}>
        <CartesianGrid stroke="#E2E8F0" vertical={false}/>
        <XAxis dataKey="index" type="number" domain={points.length === 1 ? [-.25, .25] : [0, points.length - 1]} ticks={ticks} tickFormatter={short} tick={{ fontSize: 15, fill: '#667085' }} tickLine={false} axisLine={false} dy={10}/>
        <YAxis width={82} tickFormatter={v => new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(v)} tick={{ fontSize: 15, fill: '#667085' }} tickLine={false} axisLine={false}/>
        <Tooltip labelFormatter={i => data.periods.find(p => p.value === labels[i])?.title || labels[i]} formatter={value => number(value, metric, selection.currency)} contentStyle={{ fontSize: 16, borderRadius: 12, border: '1px solid #E2E8F0', boxShadow: '0 8px 25px #0b1f3315' }}/>
        <Legend iconType="plainline" wrapperStyle={{ fontSize: 16, paddingTop: 18 }}/>
        <ReferenceLine x={labels.indexOf(data.period)} stroke="#0B1F33" strokeDasharray="3 6"/>
        {comparisons(selection.baseline).map(s => <Line key={s} dataKey={s} name={title(s)} stroke={s === 'budget' ? '#667085' : '#0B1F33'} strokeDasharray={s === 'budget' ? '7 5' : '2 5'} strokeWidth={2.5} dot={{ r: 3 }} connectNulls={false} isAnimationActive={false}/>)}
        <Line dataKey="actual" name="Actual" stroke="#00A6A6" strokeWidth={3.5} dot={{ r: 3.5, fill: '#00A6A6', strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 6 }} connectNulls={false} isAnimationActive={false}/>
      </LineChart>
    </ResponsiveContainer>
  </div>;
}

function ComparisonTable({ data, selection, rows = data.comparison }) {
  return <div className="table-scroll"><table><thead><tr><th>Performance Metric</th><th>Actual</th>{comparisons(selection.baseline).map(s => <React.Fragment key={s}><th>{title(s)}</th><th>Variance</th></React.Fragment>)}</tr></thead>
    <tbody>{rows.map(row => <tr key={row.Metric}><th><MetricInfo metric={row.Metric}>{data.labels[row.Metric] || row.Metric}</MetricInfo></th><td className="actual-cell">{number(row.Actual, row.Metric, selection.currency)}</td>{comparisons(selection.baseline).map(s => <React.Fragment key={s}><td>{number(row[title(s)], row.Metric, selection.currency)}</td><td>{variance(row, s, selection).text}</td></React.Fragment>)}</tr>)}</tbody></table></div>;
}

function App() {
  const [page, setPage] = useState('Financial Performance'), [selection, setSelection] = useState(initial);
  const [data, setData] = useState(null), [error, setError] = useState(''), [loading, setLoading] = useState(true), [reload, setReload] = useState(0);
  const [metric, setMetric] = useState('Revenue'), [operationsMetric, setOperationsMetric] = useState('scrap_tonnes');
  const [uploadOpen, setUploadOpen] = useState(false), [busy, setBusy] = useState(false), [navOpen, setNavOpen] = useState(false);
  const [report, setReport] = useState(null);
  const effective = { ...selection, period: data?.period || selection.period };
  const reportKey = JSON.stringify([data?.version, effective]);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError('');
    api(`/dashboard?${params(selection)}`, { signal: controller.signal }).then(setData)
      .catch(e => { if (e.name !== 'AbortError') setError(e.message); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [selection, reload]);
  function change(key, value) { setSelection(previous => ({ ...previous, [key]: value, ...(key === 'grain' ? { period: '' } : {}) })); }
  async function exportFile(kind) {
    setBusy(true); setError('');
    try {
      const response = await fetch(`/api/exports/${kind}?${params(effective)}`);
      if (!response.ok) throw new Error('The board pack could not be generated. Please try again.');
      downloadBlob(await response.blob(), `sustainable_packaging_board_${effective.period}.${kind}`);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function switchSample() {
    setBusy(true); setError('');
    try { await api('/datasets/sample', { method: 'POST' }); setSelection(s => ({ ...s, period: '' })); setReload(n => n + 1); setUploadOpen(false); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function upload(event) {
    event.preventDefault(); setBusy(true); setError('');
    try { const form = new FormData(event.currentTarget);
    for (const [name, file] of [...form.entries()]) if (file instanceof File && !file.name) form.delete(name);
      for (const file of form.values()) {
        if (file instanceof File && file.size > 1024 * 1024) throw new Error('Each source file must be at most 1 MB. Please upload a smaller dataset.');
      }
      await api('/datasets/upload', { method: 'POST', body: form });
      setSelection(s => ({ ...s, period: '' })); setReload(n => n + 1); setUploadOpen(false);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function generateReport() {
    setBusy(true); setError(''); const key = reportKey;
    try { const result = await api('/commentary', post(effective)); setReport({ key, ...result }); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  const rows = data?.comparison || [];
  const selectedRow = rows.find(row => row.Metric === metric);
  const coverage = data?.coverage.filter(row => row.scenario === 'actual') || [];
  const missing = data?.coverage.filter(row => comparisons(selection.baseline).includes(row.scenario) && row.months < row.expected) || [];
  return <div className="app-shell">
    {navOpen && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setNavOpen(false)}/>}
    <aside className={`sidebar ${navOpen ? 'open' : ''}`}>
      <a className="brand" href="#" onClick={e => { e.preventDefault(); setPage('Financial Performance'); }}><span className="brand-mark"><Leaf size={25}/></span><span>Packaging<span className="brand-light">Intelligence</span></span></a>
      <div className="workspace-label">REPORTING WORKSPACE</div><div className="workspace"><span className="workspace-monogram">SP</span><div>Sustainable Packaging<small>Management Workspace</small></div><ShieldCheck size={16}/></div>
      <p className="nav-label">Reporting & Analysis</p>
      <nav aria-label="Reporting & Analysis">{PAGES.map(([name, Icon]) => <button key={name} className={page === name ? 'active' : ''} aria-current={page === name ? 'page' : undefined} onClick={() => { setPage(name); setNavOpen(false); }}><Icon size={19}/><span>{name}</span><ChevronRight size={15}/></button>)}</nav>

      <div className="sidebar-footer"><span className="status-dot"/>Local Workspace<span>v2.0</span></div>
    </aside>
    <div className="workspace-main">
      <header className="topbar"><div className="breadcrumb"><button className="icon-button mobile-toggle" aria-label="Open navigation" onClick={() => setNavOpen(true)}><PanelLeftOpen size={22}/></button><span>Workspace</span><ChevronRight size={14}/><strong>{page}</strong></div><div className="top-actions"><span className="source-pill"><span className="status-dot"/>{page === 'Executive Dashboard' ? 'Executive ERP extracts' : data?.source || 'Connecting'}</span><a className="button secondary template-download" href="/api/datasets/templates" download="data_load_templates.zip"><ArrowDownToLine size={16}/>Templates</a><button className="button secondary" onClick={() => setUploadOpen(true)} disabled={busy || loading}><Upload size={16}/>Manage Data</button><span className="avatar" title="Management Workspace">SP</span></div></header>
      <main>
        <div className="page-heading"><div><p className="eyebrow">FINANCE INTELLIGENCE / MANAGEMENT REPORTING</p><h1>{page}</h1><p className="page-description">{page === 'Executive Dashboard' ? 'Sales, customer profitability and product performance from ERP source data.' : page === 'Financial Performance' ? 'The numbers that matter. A clearer view of what comes next.' : page === 'Sustainability & Operations' ? 'Track your materials, customer experience and operational resilience.' : page === 'Board Pack' ? 'From performance data to a board-ready conversation.' : page === 'AI Report' ? 'Turn calculated results into a focused management briefing.' : 'A conversation with your company performance data.'}</p></div></div>
        {page !== 'Executive Dashboard' && <section className="filter-bar" aria-label="Reporting filters">
          <label>Reporting View<select aria-label="Reporting View" value={selection.grain} disabled={busy} onChange={e => change('grain', e.target.value)}>{['Month', 'Quarter', 'Year'].map(g => <option key={g}>{g}</option>)}</select></label>
          <label>Reporting Period<select aria-label="Reporting Period" value={data?.period || ''} disabled={busy || loading} onChange={e => change('period', e.target.value)}>{data?.periods.map(p => <option key={p.value} value={p.value}>{p.title}</option>)}</select></label>
          <label>Compare Actuals Against<select aria-label="Compare Actuals Against" value={selection.baseline} disabled={busy} onChange={e => change('baseline', e.target.value)}><option value="both">Budget & Forecast</option><option value="budget">Budget</option><option value="forecast">Forecast</option></select></label>
          <label>Currency<select aria-label="Currency" value={selection.currency} disabled={busy} onChange={e => change('currency', e.target.value)}>{['AED', 'USD', 'GBP', 'EUR', 'SAR'].map(c => <option key={c}>{c}</option>)}</select></label>
          <div className="filter-note"><span className="status-dot"/>Calculated From Source Data<small>Currency label only  -  No FX conversion</small></div>
        </section>}
        {page === 'Executive Dashboard' && <ExecutiveDashboard/>}
        {page !== 'Executive Dashboard' && error && <div className="alert error" role="alert"><CircleHelp size={18}/><span>{error}</span><button className="icon-button" aria-label="Dismiss error" onClick={() => setError('')}><X size={18}/></button></div>}
        {page === 'Executive Dashboard' ? null : loading ? <div className="loading-state" role="status"><LoaderCircle className="spin" size={30}/>Preparing Your Reporting Workspace...</div> : !data ? <div className="empty-state"><h2>Let's Reconnect Your Workspace</h2><button className="button primary" onClick={() => setReload(n => n + 1)}><RefreshCw size={16}/>Try Again</button></div> : <>
          <div className="period-line" hidden={page === 'Executive Dashboard'}><span><b>{data.period_title}</b><span className="divider">/</span>Actual Results Against {selection.baseline === 'both' ? 'Budget & Forecast' : title(selection.baseline)}</span>{!['Financial Performance', 'Sustainability & Operations'].includes(page) && <span>{coverage.map(c => `${c.dataset}: ${c.months}/${c.expected}`).join('  -  ')} Months</span>}</div>
          {page !== 'Executive Dashboard' && (coverage.some(c => c.months < c.expected) || missing.length > 0) && <div className="alert"><CircleHelp size={18}/><span>Partial Data Coverage. Missing values stay unavailable. Flows reflect available months; day ratios use the full calendar period.</span></div>}
          {!['Financial Performance','Sustainability & Operations'].includes(page) && <section className="headline-grid">{['Revenue', 'Gross Profit', 'EBITDA', 'EBITDA Margin %'].map(m => <MetricCard key={m} metric={m} data={data} selection={selection} headline/>)}</section>}
          {page === 'Financial Performance' && <div className="dashboard-with-assistant"><div className="dashboard-metrics"><section className="headline-grid">{['Revenue', 'Gross Profit', 'EBITDA', 'EBITDA Margin %'].map(m => <MetricCard key={m} metric={m} data={data} selection={selection} headline/>)}</section>
            <div className="analysis-grid financial-analysis-grid"><section className="panel chart-panel"><div className="panel-heading"><div><p className="eyebrow">THE BIGGER PICTURE</p><h2>Performance Against Plan</h2></div><label className="sr-only" htmlFor="financial-metric">Financial Metric</label><select id="financial-metric" value={metric} onChange={e => setMetric(e.target.value)}>{data.groups['Financial performance'].map(m => <option key={m}>{m}</option>)}</select></div><div className="chart-unit">{unit(metric, selection.currency)}  -  {selection.grain}ly Performance</div><Trend data={data} metric={metric} selection={selection}/><div className="chart-summary"><span>Selected Period <b>{data.period_title}</b></span><span>Actual <b>{number(selectedRow?.Actual, metric, selection.currency, true)}</b></span>{comparisons(selection.baseline).map(s => <span key={s}>{title(s)} <b>{number(selectedRow?.[title(s)], metric, selection.currency, true)}</b></span>)}</div></section>
            <section className="focus-panel cash-panel-classic"><span className="gold-icon"><Wallet size={24}/></span><p className="eyebrow">FINANCIAL RESILIENCE</p><h2>A Closer Look At Cash</h2><p>Closing balances for your selected reporting period.</p>{['Cash', 'Accounts Receivable', 'Material Payables'].map(m => <div className="focus-metric" key={m}><span><MetricInfo metric={m}>{data.labels[m]||m}</MetricInfo></span><strong>{number(rows.find(r => r.Metric === m)?.Actual, m, selection.currency, true)}</strong></div>)}<button onClick={() => setPage('Sustainability & Operations')}>Explore Operations <ArrowRight size={17}/></button></section></div>
            <div className="section-heading"><div><h2>People & Operating Expenses</h2><p>Staff costs sit within operating expenses. Headcount is a closing balance.</p></div><Users size={22}/></div><div className="headline-grid">{['Staff Costs', 'Headcount', 'Operating Expenses', 'Other Operating Expenses'].map(m => <MetricCard key={m} metric={m} data={data} selection={selection}/>)}</div>
            <section className="panel"><div className="panel-heading"><div><h2>Financial Detail</h2><p>A consistent view of actuals and your planning targets.</p></div><button className="text-button" onClick={() => exportFile('csv')} disabled={busy}><ArrowDownToLine size={16}/>Export CSV</button></div><ComparisonTable data={data} selection={selection} rows={rows.filter(r => data.groups['Financial performance'].includes(r.Metric))}/></section>
          </div><aside className="data-assistant-panel" aria-label="Financial Data side panel"><FinancialChat selection={effective} version={data.version}/></aside></div>}
          {page === 'Sustainability & Operations' && <div className="dashboard-with-assistant"><div className="dashboard-metrics"><OperationsOverview data={data} selection={selection}
            renderCard={m=><MetricCard key={m} metric={m} data={data} selection={selection} headline/>}
            renderTrend={m=><Trend data={data} metric={m} selection={selection}/>}
            formatValue={number}/></div><aside className="data-assistant-panel" aria-label="Operations Data side panel"><FinancialChat scope="operations" selection={effective} version={data.version}/></aside></div>}
          {page === 'Board Pack' && <>
            <section className="board-hero"><div><p className="eyebrow">READY FOR THE BOARDROOM</p><h2>Your Performance.<br/>A Clearer Conversation.</h2><p>{data.period_title}  -  Financial results, sustainable operations, customer credit and people in one pack.</p><span><ShieldCheck size={17}/>Generated From The Same Validated KPI Calculations</span></div><FileChartColumn size={120} strokeWidth={.9}/></section>
            <div className="export-grid">{[['pptx', 'Board Presentation', '11 editable slides with key metrics, planning comparisons and trend charts.'], ['xlsx', 'Management Workbook', 'Both planning comparisons and the complete reporting KPI history.'], ['csv', 'Period KPI Data', 'Selected comparison, reporting period and currency. Ready to analyse.']].map(([kind, name, description]) => <article className="panel export-card" key={kind}><span className="file-type">{kind.toUpperCase()}</span><h2>{name}</h2><p>{description}</p><button className="button primary" disabled={busy} onClick={() => exportFile(kind)}><ArrowDownToLine size={17}/>Download {kind.toUpperCase()}</button></article>)}</div>
            <section className="panel"><div className="panel-heading"><div><h2>Board KPI Preview</h2><p>Margin and rate differences are percentage points. Other variances are relative percentages.</p></div></div><ComparisonTable data={data} selection={selection}/></section>
          </>}
          {page === 'AI Report' && <>
            <section className="ai-banner"><span className="gold-icon"><Sparkles size={26}/></span><div><p className="eyebrow">YOUR MANAGEMENT BRIEFING</p><h2>From Numbers To Perspective</h2><p>Generate a grounded briefing for {data.period_title}. The selected KPI comparison is sent to OpenAI; review the narrative before sharing.</p></div><button className="button primary" disabled={busy} onClick={generateReport}>{busy ? <LoaderCircle className="spin" size={17}/> : <Sparkles size={17}/>}Generate Briefing</button></section>
            {report?.key === reportKey ? <><div className="report-grid">{report.sections.map((section, i) => <article className="panel narrative-card" key={i}><span className="section-number">0{i+1}</span><p className="eyebrow">{data.period_title}</p><h2>{section.title}</h2><Markdown>{section.body}</Markdown></article>)}</div><button className="button secondary" onClick={() => downloadBlob(new Blob([report.text], { type: 'text/markdown' }), `commentary_${data.period}.md`)}><ArrowDownToLine size={17}/>Download Commentary</button></> : <div className="empty-state"><Sparkles size={35}/><h2>Your Next Board Briefing Starts Here</h2><p>Executive summary  -  Performance vs plan  -  Risks & questions  -  Proposed actions</p></div>}
          </>}
          <footer className="page-footer"><span><Leaf size={14}/>Sustainable Packaging Intelligence</span><span>Calendar Fiscal Year  -  Single Entity  -  {selection.currency}  -  {data.source}</span></footer>
        </>}
      </main>
    </div>
    {uploadOpen && <div className="modal-backdrop" onClick={e => { if (e.target === e.currentTarget && !busy) setUploadOpen(false); }}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="upload-title"><div className="panel-heading"><div><p className="eyebrow">YOUR REPORTING WORKSPACE</p><h2 id="upload-title">Manage Source Data</h2></div><button className="icon-button" aria-label="Close data dialog" disabled={busy} onClick={() => setUploadOpen(false)}><X/></button></div><p>Upload any one or more files. Each load replaces the current datasets. Omitted files and blank numeric fields display No Data; enter 0 only for a reported zero. Include at least one actual row. Download Templates above for sample CSV files and instructions.</p><form onSubmit={upload}>{[['finance', 'Financial Accounts'], ['operations', 'Operations & Materials'], ['balances', 'Closing Balances & Headcount']].map(([name, label]) => <label className="file-input" key={name}>{label}<input type="file" name={name} accept=".csv,.xlsx" disabled={busy}/></label>)}<p className="footnote">CSV or XLSX  -  Maximum 1 MB and 100,000 rows per file. Your files and chat are saved privately for this browser workspace and expire after two hours of inactivity.</p><button className="button primary" disabled={busy}>{busy ? <LoaderCircle className="spin" size={17}/> : <Upload size={17}/>}Validate & Load Files</button></form><div className="modal-divider">OR EXPLORE THE APPLICATION</div><button className="button secondary" disabled={busy} onClick={switchSample}><Sprout size={17}/>Load Seasonal Sample Data</button>{error && <p role="alert" className="negative">{error}</p>}</section></div>}
  </div>;
}

function Evidence({ rows }) {
  const columns = [...new Set(rows.flatMap(row => Object.keys(row)))];
  return <div className="table-scroll evidence"><table><thead><tr>{columns.map(c => <th key={c}>{c}</th>)}</tr></thead><tbody>{rows.map((r, i) => <tr key={i}>{columns.map(c => <td key={c}>{r[c] == null ? 'No Data' : String(r[c])}</td>)}</tr>)}</tbody></table></div>;
}
function Definitions() {
  const [text, setText] = useState('');
  return <details onToggle={e => { if (e.currentTarget.open && !text) api('/definitions').then(r => setText(r.text)).catch(() => setText('Definitions could not be loaded.')); }}><summary>Metric Definitions  -  D1</summary><Markdown>{text}</Markdown></details>;
}

createRoot(document.getElementById('root')).render(<App/>);
