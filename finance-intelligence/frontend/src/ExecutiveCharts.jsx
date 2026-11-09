import React, {useEffect, useState} from 'react';
import MetricInfo from './MetricInfo';
import {ResponsiveContainer, BarChart, Bar, Cell, LabelList, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, Rectangle} from 'recharts';
const palette={teal:'#00A6A6',navy:'#0B1F33',slate:'#667085'};
const labels={net_revenue:'Revenue',gross_profit:'Gross profit',gross_margin:'Gross margin'};
const compact=value=>new Intl.NumberFormat('en',{notation:'compact',maximumFractionDigits:1}).format(value);
const format=(value,metric)=>value==null?'Unavailable':metric==='gross_margin'?`${value.toFixed(1)}%`:`AED ${new Intl.NumberFormat('en',{maximumFractionDigits:0}).format(value)}`;
const delta=value=>value==null?'Unavailable':`${value>=0?'+':''}${value.toFixed(1)}`;
export function PeriodTrend({filters,dimension='location',members=[],metric='net_revenue',title='Progress against prior periods',comparison='all'}) {
  const [data,setData]=useState(null),[error,setError]=useState(''),[retry,setRetry]=useState(0);
  const key=JSON.stringify([filters,dimension,members,metric]);
  useEffect(()=>{
    const controller=new AbortController();setData(null);setError('');
    const params=new URLSearchParams(Object.entries({...filters,dimension,metric}).filter(([,value])=>value));
    members.forEach(value=>params.append('members',value));
    fetch(`/api/executive/trend?${params}`,{signal:controller.signal,cache:'no-store'})
      .then(async response=>{const result=await response.json();if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'Unable to load period comparison');return result;})
      .then(setData).catch(e=>{if(e.name!=='AbortError')setError(e.message);});
    return()=>controller.abort();
  },[key,retry]);
  return <div className="executive-period-trend"><div className="executive-section-heading"><div><h4>{title}</h4><p className="footnote">{metric==='gross_margin'?'Weighted cumulative gross margin':'Cumulative '+labels[metric].toLowerCase()} - same entities, matched reporting cutoffs.</p></div></div>
    {error?<p role="alert">{error} <button type="button" className="text-button" onClick={()=>setRetry(value=>value+1)}>Retry trend</button></p>:!data?<p role="status">Loading period comparison...</p>:<>
      <div className="executive-comparison-cards">{data.periods.filter(period=>period.key==='current'||comparison==='all'||period.key===comparison).map((period,i)=><article key={period.key}><span><i style={{background:({current:palette.teal,last_month:palette.slate,last_year:palette.navy,last_quarter:palette.navy})[period.key]}}/>{period.name}</span><strong>{format(period.value,metric)}</strong><small>{period.start} to {period.end} ({period.days} days)</small>{i>0 && <b>{metric==='gross_margin'?`${delta(period.change)} pp`:`${delta(period.change_pct)}${period.change_pct==null?'':'%'}`} selected vs this period{!period.complete?' - outside source coverage':''}</b>}</article>)}</div>
      <div role="img" aria-label={`${title}: selected period compared with the matching cutoff last month, quarter and year`}>
        <ResponsiveContainer width="100%" height={250}><LineChart data={data.points} margin={{top:14,right:16,left:4,bottom:12}}><CartesianGrid stroke="#E2E8F0" vertical={false}/><XAxis dataKey="day" minTickGap={40} tickFormatter={value=>`Day ${value}`} tick={{fontSize:12}}/><YAxis width={65} tickFormatter={value=>metric==='gross_margin'?`${value.toFixed(0)}%`:compact(value)} tick={{fontSize:12}}/><Tooltip labelFormatter={value=>`Elapsed day ${value}`} formatter={value=>format(value,metric)}/><Legend/>{[['current','Selected period',palette.teal,undefined],['last_month','Last month',palette.slate,'6 4'],['last_year','Last year',palette.navy,'2 4'],['last_quarter','Last quarter',palette.navy,'9 3']].filter(([key])=>key==='current'||comparison==='all'||comparison===key).map(([key,name,color,dash])=><Line key={key} dataKey={key} name={name} stroke={color} strokeWidth={key==='current'?3:2} strokeDasharray={dash} dot={data.points.length===1?{r:5}:false} connectNulls={false} isAnimationActive={false}/>)}</LineChart></ResponsiveContainer>
      </div><p className="footnote">Changes show selected period minus the comparison period. Lines use elapsed days and stop at each cutoff; reporting periods can differ in length. Gross margin changes are percentage points.</p>
    </>}
  </div>;
}
function BarTooltip({active,payload,label,dimension}) {
  if(!active||!payload?.length)return null;
  const row=payload[0].payload;
  return <div className="executive-chart-tooltip"><strong>{row[dimension]||label}</strong>{Object.entries(labels).map(([key,name])=><p key={key}>{name}: <b>{format(row[key],key)}</b></p>)}</div>;
}
export function RankingVisual({title,rows,dimension,metric='net_revenue',filters,tone='teal',orientation='horizontal',comparison='all'}) {
  const [selected,setSelected]=useState('');
  const members=rows.map(row=>row[dimension]);
  const focus=members.includes(selected)?selected:'';
  const color=palette[tone];
  const vertical=orientation==='vertical';
  return <section className="panel executive-ranking-visual"><div className="executive-section-heading"><div><h3><MetricInfo metric={dimension==='sku'?'SKU':metric}>{title}</MetricInfo></h3><p className="footnote">{labels[metric]} - select a bar to focus the trend below.</p></div>{focus&&<button type="button" className="text-button" onClick={()=>setSelected('')}>Show all displayed entities</button>}</div>
    {!rows.length?<p>No transactions match these filters.</p>:<>
      <div className="executive-bar-scroll"><div className="executive-bar-canvas" role="img" aria-label={`${title}, ranked by ${labels[metric]}`} style={{height:vertical?380:Math.max(180,rows.length*38+55), minWidth:vertical?Math.max(560,rows.length*75):560}}><ResponsiveContainer width="100%" height="100%"><BarChart layout={vertical?'horizontal':'vertical'} data={rows} margin={vertical?{left:8,right:25,top:25,bottom:100}:{left:4,right:75,top:8,bottom:12}} accessibilityLayer><CartesianGrid stroke="#E2E8F0" horizontal={false}/>{vertical?<><XAxis type="category" dataKey={dimension} angle={-40} textAnchor="end" interval={0} height={80} tick={{fontSize:11,fill:palette.navy}}/><YAxis type="number" width={65} tickFormatter={value=>metric==='gross_margin'?`${value}%`:compact(value)} tick={{fontSize:12}}/></>:<><XAxis type="number" tickFormatter={value=>metric==='gross_margin'?`${value}%`:compact(value)} tick={{fontSize:12}}/><YAxis type="category" dataKey={dimension} width={185} tick={{fontSize:13,fill:palette.navy}} tickLine={false} axisLine={false}/></>}<ReferenceLine {...(vertical?{y:0}:{x:0})} stroke="#9AABBC"/><Tooltip content={<BarTooltip dimension={dimension}/>}/><Bar dataKey={metric} name={labels[metric]} radius={[7,7,7,7]} maxBarSize={vertical?42:22} cursor="pointer" onClick={entry=>setSelected(previous=>previous===entry[dimension]?'':entry[dimension])} isAnimationActive={false}>{rows.map(row=><Cell key={row[dimension]} fill={row[metric]<0?palette.navy:color} fillOpacity={!focus||focus===row[dimension]?1:.3}/>)}<LabelList dataKey={metric} position={vertical?'top':'right'} formatter={value=>metric==='gross_margin'?`${value.toFixed(1)}%`:compact(value)} style={{fontSize:12,fill:palette.navy}}/></Bar></BarChart></ResponsiveContainer></div></div>
      <label className="executive-trend-focus">Trend focus<select aria-label={`Trend focus for ${title}`} value={focus} onChange={event=>setSelected(event.target.value)}><option value="">All {rows.length} displayed entities</option>{members.map(value=><option key={value}>{value}</option>)}</select></label>
      <details className="executive-chart-data"><summary>View exact figures</summary><div className="table-scroll"><table><caption className="sr-only">{title}</caption><thead><tr><th>{dimension}</th><th>Revenue</th><th>Gross profit</th><th>Gross margin</th></tr></thead><tbody>{rows.map(row=><tr key={row[dimension]}><th>{row[dimension]}</th><td>{format(row.net_revenue,'net_revenue')}</td><td>{format(row.gross_profit,'gross_profit')}</td><td>{format(row.gross_margin,'gross_margin')}</td></tr>)}</tbody></table></div></details>
      <PeriodTrend comparison={comparison} filters={filters} dimension={dimension} members={focus?[focus]:members} metric={metric} title={focus?`${focus} - period progress`:'Displayed entities - period progress'}/>
    </>}
  </section>;
}
export function PlanBars({actual,budget,forecast}) {
  const [chartWidth,setChartWidth]=useState(0);
  const series=[['actual','Actual',palette.teal],['budget','Budget',palette.slate],['forecast','Forecast',palette.navy]];
  const slotWidth=chartWidth?Math.max(1,(chartWidth-118)/3):76.8;
  const barWidth=slotWidth*0.8;
  // Keep the three column centres while narrowing each bar by 20%.
  function shape(index,name,color,value) {
    return props=>{
      if(value==null || !Number.isFinite(props.y) || !Number.isFinite(props.height))return null;
      const x=78+index*(slotWidth+12)+(slotWidth-barWidth)/2,y=props.y,height=props.height;
      return <g><Rectangle x={x} y={y} width={barWidth} height={height} radius={[8,8,0,0]} fill={color}/><text x={x+barWidth/2} y={y-10} textAnchor="middle" fontSize={12} fill={palette.navy}>{compact(value)}</text><text x={x+barWidth/2} y={y+height+22} textAnchor="middle" fontSize={12} fill={palette.navy}>{name}</text></g>;
    };
  }
  return <div role="img" aria-label="Selected-period revenue compared with budget and forecast"><ResponsiveContainer width="100%" height={310} onResize={width=>setChartWidth(width)}><BarChart data={[{period:'Selected period',actual,budget,forecast}]} barGap={12} barCategoryGap="10%" margin={{left:5,right:16,top:26,bottom:22}}><CartesianGrid vertical={false} stroke="#E2E8F0"/><XAxis dataKey="period" tick={false} axisLine={false} tickLine={false} height={24}/><YAxis type="number" width={65} tickFormatter={compact}/><Tooltip labelFormatter={()=>'Selected period'} formatter={value=>format(value,'net_revenue')}/>{series.map(([key,name,color],index)=><Bar key={key} dataKey={key} name={name} fill={color} shape={shape(index,name,color,{actual,budget,forecast}[key])} isAnimationActive={false}/>)}</BarChart></ResponsiveContainer></div>;
}
export function MonthlyBars({history}) {
  return <div className="executive-month-bars" role="img" aria-label="Monthly revenue and gross profit"><ResponsiveContainer width="100%" height={300}><BarChart data={history} barGap={3} margin={{top:10,right:15,left:5,bottom:16}}><CartesianGrid vertical={false} stroke="#E2E8F0"/><XAxis dataKey="month" minTickGap={35} tick={{fontSize:12}}/><YAxis width={65} tickFormatter={compact} tick={{fontSize:12}}/><Tooltip formatter={value=>format(value,'net_revenue')}/><Legend/><Bar dataKey="net_revenue" name="Revenue" fill={palette.teal} radius={[5,5,0,0]} isAnimationActive={false}/><Bar dataKey="gross_profit" name="Gross profit" fill={palette.navy} radius={[5,5,0,0]} isAnimationActive={false}/></BarChart></ResponsiveContainer></div>;
}
