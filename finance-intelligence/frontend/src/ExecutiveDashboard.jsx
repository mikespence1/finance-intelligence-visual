import React, {useEffect, useState} from 'react';
import ExecutiveChat from './ExecutiveChat';
import MetricInfo from './MetricInfo';
import {RankingVisual, PeriodTrend, PlanBars, MonthlyBars} from './ExecutiveCharts';
import {ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend} from 'recharts';
const money = value => value == null ? 'Unavailable' : `AED ${new Intl.NumberFormat('en', {maximumFractionDigits: 0}).format(value)}`;
const percent = value => value == null ? 'Unavailable' : `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
const metrics = {net_revenue: 'Revenue', gross_profit: 'Gross profit', gross_margin: 'Gross margin %'};
function ranked(rows, key, descending = true) {
  return rows.filter(row => row[key] != null && (key !== 'gross_margin' || row.net_revenue > 0))
    .slice().sort((a, b) => (descending ? -1 : 1) * (a[key] - b[key]) || String(a.customer || a.sku).localeCompare(String(b.customer || b.sku)));
}
function RankSelect({label, value, onChange}) {
  return <label>{label}<select aria-label={label} value={value} onChange={e => onChange(e.target.value)}>{Object.entries(metrics).map(([key, name]) => <option key={key} value={key}>{name}</option>)}</select></label>;
}
export default function ExecutiveDashboard() {
  const [filters, setFilters] = useState({date: '', category: '', location: '', period: 'mtd', start_date: ''});
  const [data, setData] = useState(null), [error, setError] = useState(''), [loading, setLoading] = useState(true), [reload, setReload] = useState(0);
  const [comparison,setComparison] = useState('all');
  const [section, setSection] = useState('overview'), [breakdown, setBreakdown] = useState('customer');
  const [customerRank, setCustomerRank] = useState('gross_profit'), [skuRank, setSkuRank] = useState('net_revenue');
  const [count, setCount] = useState(10), [search, setSearch] = useState('');
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError('');
    let timedOut = false;
    const timer = setTimeout(() => {timedOut = true; controller.abort();}, 60000);
    fetch(`/api/executive?${new URLSearchParams(Object.entries(filters).filter(([, value]) => value))}`, {signal: controller.signal, cache: 'no-store'})
      .then(async response => {
        const result = await response.json().catch(() => null);
        if (!response.ok) {
          const detail = typeof result?.detail === 'string' ? result.detail : null;
          throw Error(detail || `Executive data request failed (HTTP ${response.status}). Please retry. If this continues, check the server deployment logs.`);
        }
        if (!result?.breakdowns || !Array.isArray(result.customers) || !Array.isArray(result.skus) || !Array.isArray(result.history) || !result.options) {
          throw Error('The Executive API returned an incompatible response. Redeploy the frontend and backend from the same latest commit, then refresh this page.');
        }
        return result;
      })
      .then(setData).catch(e => {
        if (timedOut) setError('Executive data took longer than 60 seconds to load. Please retry.');
        else if (e.name !== 'AbortError') setError(e.message || 'Unable to connect to the Executive API. Please retry.');
      })
      .finally(() => {clearTimeout(timer); if (!controller.signal.aborted || timedOut) setLoading(false);});
    return () => {clearTimeout(timer); controller.abort();};
  }, [filters, reload]);
  const change = (key, value) => setFilters(previous => ({...previous, [key]: value, ...(key === 'period' && value === 'custom' && !previous.start_date ? {start_date: (previous.date || data.as_of).slice(0, 7) + '-01'} : {})}));
  if (!data) return <section className="panel" aria-busy={loading}>
    <h2>{error ? 'Executive Dashboard could not load' : 'Loading executive data...'}</h2>
    <p role={error ? 'alert' : 'status'}>{error || 'Preparing sales and planning data. The first request may take a little longer.'}</p>
    {error && <button className="button primary" type="button" onClick={() => setReload(value => value + 1)}>Retry Executive Dashboard</button>}
  </section>;
  const customers = data.customers.filter(row => row.customer.toLowerCase().includes(search.toLowerCase()));
  const salesLabel=({day:'Daily sales',mtd:'Month-to-date sales',qtd:'Quarter-to-date sales',ytd:'Year-to-date sales',custom:'Selected-period sales'})[filters.period];
  const periodLabel = `${data.analysis_start} to ${data.analysis_end}`;
  return <div className="executive-dashboard" aria-busy={loading}>
    <section className="panel executive-controls" aria-label="Executive filters">
      <div className="executive-section-heading"><div><h2>Your reporting view</h2><p>Select a date and market. The analysis period filters all sales metrics, plans, rankings and charts below.</p></div><span className="source-pill">{data.source} - AED</span></div>
      <div className="executive-filter-grid">
        <label>As-of date<input type="date" min={data.min_date} max={data.max_date} value={filters.date || data.as_of} onChange={e => change('date', e.target.value)}/></label>
        <label>Analysis period<select aria-label="Analysis period" value={filters.period} onChange={e => change('period', e.target.value)}>{[['day','Selected day'],['mtd','Month to date'],['qtd','Quarter to date'],['ytd','Year to date'],['custom','Custom date range']].map(([key, name]) => <option key={key} value={key}>{name}</option>)}</select></label>
        {filters.period === 'custom' && <label>From date<input type="date" min={data.min_date} max={filters.date || data.as_of} value={filters.start_date} onChange={e => change('start_date', e.target.value)}/></label>}
        {['category','location'].map(key => <label key={key}>{key === 'category' ? 'Material category' : 'Location'}<select aria-label={key === 'category' ? 'Material category' : 'Location'} value={filters[key]} onChange={e => change(key, e.target.value)}><option value="">All {key === 'category' ? 'categories' : 'locations'}</option>{data.options[key === 'category' ? 'categories' : 'locations'].map(value => <option key={value}>{value}</option>)}</select></label>)}
      </div>
      <p className="footnote" role="status">{loading ? 'Updating results...' : `Analysis: ${periodLabel}.`} All visuals use this date range, category and location.</p>
    </section>
    {error && <p className="alert error" role="alert">{error} Showing the last successfully loaded results.</p>}
    <nav className="executive-sections" aria-label="Executive dashboard sections">{[['overview','Sales overview'],['customers','Customer performance'],['skus','Product performance'],['trends','Trends & comparisons']].map(([key, name]) => <button type="button" key={key} aria-pressed={section === key} onClick={() => setSection(key)}>{name}</button>)}</nav>
    <div className="executive-section-heading"><div><h2>{section === 'overview' ? 'Sales overview' : section === 'customers' ? 'Customer performance' : section === 'skus' ? 'Product performance' : 'Trends & comparisons'}</h2><p>{section === 'overview' ? `As of ${data.as_of}` : `Analysis period: ${periodLabel}`}</p></div></div>
    <div className="dashboard-with-assistant"><div className="dashboard-metrics">
    {section === 'overview' && <>
      <div className="headline-grid">{[[salesLabel,money(data.analysis_revenue),periodLabel],['Gross profit',money(data.analysis_profit),'Revenue less cost of goods sold'],['Gross margin',data.analysis_margin==null?'Unavailable':`${data.analysis_margin.toFixed(1)}%`,'Gross profit divided by selected-period revenue'],['Sales change vs last year',percent(data.analysis_yoy_pct),`Matching period last year: ${money(data.analysis_prior_revenue)}`]].map(([label, value, note]) => <article className="metric-card" key={label}><div className="metric-title"><MetricInfo metric={label}>{label}</MetricInfo></div><div className="metric-value">{value}</div><p className="footnote">{note}</p></article>)}</div>
      <section className="panel executive-plan-panel"><h3>Revenue against plan - selected period</h3><p>{periodLabel} - actual sales: <strong>{money(data.analysis_revenue)}</strong>. Plans cover the same dates.</p>
        <div className="plan-chart-and-controls"><div className="compact-plan-chart"><PlanBars actual={data.analysis_revenue} budget={data.analysis_budget} forecast={data.analysis_forecast}/></div>
          <nav className="period-shortcuts" aria-label="Sales period and comparison shortcuts"><strong>Analysis period</strong><div>{[['day','Day'],['mtd','MTD'],['qtd','QTD'],['ytd','YTD']].map(([key,label])=><button key={key} type="button" aria-pressed={filters.period===key} onClick={()=>change('period',key)}><MetricInfo metric={key==='day'?'Daily revenue':label}>{label}</MetricInfo></button>)}</div>
            <strong>Compare matching cutoff</strong><div>{[['last_month','Last month'],['last_quarter','Last quarter'],['last_year','Last year'],['all','All comparisons']].map(([key,label])=><button key={key} type="button" aria-pressed={comparison===key} onClick={()=>setComparison(key)}>{label}</button>)}</div></nav>
        </div><div className="executive-plan-grid">{[['Budget',data.analysis_budget,data.analysis_budget_variance,data.analysis_budget_pct],['Forecast',data.analysis_forecast,data.analysis_forecast_variance,data.analysis_forecast_pct]].map(([name,amount,variance,relative])=><article key={name}><h4>{name}</h4><strong>{money(amount)}</strong><p>{money(variance)} variance ({percent(relative)})</p></article>)}</div>
        <PeriodTrend comparison={comparison} filters={filters} title="Selected sales period - progress"/>
      </section>
      <section className="panel"><div className="executive-section-heading"><div><h3>Revenue breakdown</h3><p>{periodLabel} - change the analysis period above to explore daily or longer-term sales.</p></div><label>Group by<select value={breakdown} onChange={e => setBreakdown(e.target.value)}>{['customer','category','sku','location'].map(value => <option key={value}>{value}</option>)}</select></label></div><RankingVisual comparison={comparison} orientation={['customer','sku'].includes(breakdown)?'horizontal':'vertical'} filters={filters} title={`Revenue by ${breakdown}`} dimension={breakdown} rows={ranked(data.breakdowns[breakdown], 'net_revenue').slice(0,10)}/></section>
    </>}
    {section === 'customers' && <>
      <section className="panel"><div className="executive-filter-grid"><RankSelect label="Rank customers by" value={customerRank} onChange={setCustomerRank}/><label>Customers in each list<select aria-label="Customers in each list" value={count} onChange={e => setCount(Number(e.target.value))}>{[5,10,20].map(value => <option key={value} value={value}>{value}</option>)}</select></label><label>Find a customer<input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Customer name"/></label></div><p className="footnote">Filter by day, month, quarter, year or custom range, material category and location above. Rankings use {metrics[customerRank].toLowerCase()}; margin rankings require positive net revenue.</p></section>
      <div className="executive-ranking-grid"><RankingVisual orientation="horizontal" comparison={comparison} filters={filters} title={`Top ${count} customers by ${metrics[customerRank].toLowerCase()}`} dimension="customer" metric={customerRank} rows={ranked(customers, customerRank).slice(0,count)}/><RankingVisual orientation="horizontal" comparison={comparison} filters={filters} title={`Bottom ${count} customers by ${metrics[customerRank].toLowerCase()}`} dimension="customer" metric={customerRank} tone="navy" rows={ranked(customers, customerRank, false).slice(0,count)}/></div>
      <details className="panel"><summary>All matching customers ({customers.length})</summary><RankingVisual orientation="horizontal" comparison={comparison} filters={filters} title="Customer profitability" dimension="customer" metric={customerRank} rows={ranked(customers, customerRank)}/></details>
    </>}
    {section === 'skus' && <>
      <section className="panel"><RankSelect label="Rank SKUs by" value={skuRank} onChange={setSkuRank}/><p className="footnote">Uses the analysis period, category and location above. Margin rankings require positive net revenue.</p></section>
      <div className="executive-ranking-grid"><RankingVisual orientation="horizontal" comparison={comparison} filters={filters} title={`Top 10 SKUs by ${metrics[skuRank].toLowerCase()}`} dimension="sku" metric={skuRank} rows={ranked(data.skus, skuRank).slice(0,10)}/><RankingVisual orientation="horizontal" comparison={comparison} filters={filters} title={`Bottom 10 SKUs by ${metrics[skuRank].toLowerCase()}`} dimension="sku" metric={skuRank} tone="navy" rows={ranked(data.skus, skuRank, false).slice(0,10)}/></div>
    </>}
    {section === 'trends' && <>
      <section className="panel"><h3>Revenue trend - selected period</h3><p>Monthly totals inside the selected analysis range, category and location. Boundary months show only the selected days.</p><ResponsiveContainer width="100%" height={340}><LineChart data={(data.analysis_history||data.history)}><CartesianGrid stroke="#E2E8F0" vertical={false}/><XAxis dataKey="month" minTickGap={36}/><YAxis width={75} tickFormatter={value => `${(value/1000000).toFixed(1)}m`}/><Tooltip formatter={money}/><Legend/>{[['net_revenue','Revenue','#007F80'],['budget','Budget','#667085'],['forecast','Forecast','#0B1F33']].map(([key, label, color], i) => <Line key={key} dataKey={key} name={label} stroke={color} strokeDasharray={i ? `${i*4} 4` : undefined} dot={(data.analysis_history||data.history).length===1?{r:4}:false} strokeWidth={2}/>)}</LineChart></ResponsiveContainer></section>
      <section className="panel"><h3>Month-on-month comparison</h3><p className="footnote">Monthly values respect the selected range; boundary months can be partial. MoM compares adjacent months within that range.</p><MonthlyBars history={(data.analysis_history||data.history)}/><PeriodTrend comparison={comparison} filters={filters} title="Selected sales period - progress"/><details className="executive-chart-data"><summary>View monthly figures</summary><div className="table-scroll executive-history"><table><thead><tr><th>Month</th><th>Revenue</th><th>Gross profit</th><th>MoM change</th></tr></thead><tbody>{(data.analysis_history||data.history).slice().reverse().map(row => <tr key={row.month}><th>{row.month}{row.month === data.as_of.slice(0,7) ? ' (through selected day)' : ''}</th><td>{money(row.net_revenue)}</td><td>{money(row.gross_profit)}</td><td>{percent(row.mom_pct)}</td></tr>)}</tbody></table></div></details></section>
    </>}
    </div><aside className="data-assistant-panel" aria-label="Executive Data side panel"><ExecutiveChat key={JSON.stringify(filters)} filters={filters}/></aside></div>
  </div>;
}
