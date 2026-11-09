import React, {useState} from 'react';
import MetricInfo from './MetricInfo';
const topics=[
  {key:'materials',title:'Materials & Circularity',description:'Reduce waste and track the circular use of materials.',metrics:['production_tonnes','scrap_tonnes','Scrap Rate %','waste_cost','Recycled Input %','Waste Recovery %'],focus:'Scrap Rate %'},
  {key:'returns',title:'Customer Returns',description:'Monitor shipment quality and the cost of returns.',metrics:['orders_shipped','returned_orders','Return Rate %','returned_order_value'],focus:'Return Rate %'},
  {key:'stock',title:'Stock & Customer Credit',description:'Manage stock, overdue invoices and credit exposure.',metrics:['Inventory','Raw Material Stock Tonnes','Finished Goods Stock Tonnes','Accounts Receivable','Overdue Receivables','Customer Credit Limit','Customer Credit Headroom','Credit Utilisation %'],focus:'Credit Utilisation %'},
  {key:'liquidity',title:'Cash, Suppliers & People',description:'Track liquidity, supplier commitments and working-capital days.',metrics:['Cash','Material Payables','Overdue Material Payables','Accounts Payable','Headcount','DSO','DIO','DPO','Cash Conversion Cycle'],focus:'Cash Conversion Cycle'},
];
export default function OperationsOverview({data,selection,renderCard,renderTrend,formatValue}) {
  const [active,setActive]=useState('materials'),[focus,setFocus]=useState('Scrap Rate %');
  const topic=topics.find(item=>item.key===active);
  function choose(item){setActive(item.key);setFocus(item.focus);}
  return <div className="operations-overview">
    <section className="headline-grid" aria-label="Operational headline metrics">{['Scrap Rate %','Recycled Input %','Waste Recovery %','Return Rate %'].map(renderCard)}</section>
    <div className="section-heading"><div><h2>Explore your operations</h2><p>Four themes, one focused trend at a time. Choose a theme to see its key measures and expand the full detail when needed.</p></div></div>
    <nav className="operations-topic-nav" aria-label="Operational themes">{topics.map(item=><button key={item.key} type="button" aria-pressed={active===item.key} onClick={()=>choose(item)}><strong>{item.title}</strong><span>{item.metrics.length} measures</span></button>)}</nav>
    <section className="panel operations-topic"><div className="panel-heading"><div><h2>{topic.title}</h2><p>{topic.description}</p></div><label>Trend metric<select aria-label="Operational trend metric" value={focus} onChange={event=>setFocus(event.target.value)}>{topic.metrics.map(metric=><option key={metric} value={metric}>{data.labels[metric]||metric}</option>)}</select></label></div>
      <p className="operations-focus-value"><MetricInfo metric={focus}>{data.labels[focus]||focus}</MetricInfo><strong>{formatValue(data.comparison.find(row=>row.Metric===focus)?.Actual,focus,selection.currency)}</strong></p>
      {renderTrend(focus)}
      <div className="operations-stat-strip">{topic.metrics.filter(metric=>metric!==focus).slice(0,3).map(metric=><div className="operations-support-card" key={metric}>{renderCard(metric)}<button type="button" className="support-trend-button" aria-label={`View trend for ${data.labels[metric]||metric}`} onClick={()=>setFocus(metric)}>View trend <span aria-hidden="true">&#8599;</span></button></div>)}</div>
      <details className="operations-details"><summary>All {topic.metrics.length} {topic.title.toLowerCase()} measures and plan comparisons</summary><div className="operations-grid">{topic.metrics.map(renderCard)}</div></details>
    </section><p className="footnote">Wastage cost and return value are disclosures already reflected in financial reporting. Ratios recompute from total inputs; closing balances use the latest month. Hover or focus a metric for its definition.</p>
  </div>;
}
