import React from 'react';
import {ResponsiveContainer,AreaChart,Area,Tooltip} from 'recharts';
export default function MetricSparkline({points,formatValue,label}) {
  const values=points.filter(point=>point.value!=null);
  if(!values.length)return null;
  return <div className="metric-sparkline" role="img" aria-label={`${label} recent trend`}><ResponsiveContainer width="100%" height={48}><AreaChart data={points} margin={{top:3,bottom:3,left:0,right:0}}><Tooltip formatter={value=>formatValue(value)} labelFormatter={(_,payload)=>payload?.[0]?.payload?.label||''} contentStyle={{background:'#fff',color:'#0B1F33',fontSize:12,borderRadius:8}}/><Area type="monotone" dataKey="value" stroke="currentColor" fill="currentColor" fillOpacity={.16} strokeWidth={2.5} dot={values.length===1?{r:4}:false} isAnimationActive={false} connectNulls={false}/></AreaChart></ResponsiveContainer></div>;
}
