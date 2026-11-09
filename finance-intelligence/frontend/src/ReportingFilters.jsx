import React from 'react';
export default function ReportingFilters({data,selection,busy,loading,onChange}) {
  return <section className="sidebar-reporting-filters" aria-label="Reporting filters">
    <h2>Reporting filters</h2>
    <label>Reporting View<select aria-label="Reporting View" value={selection.grain} disabled={busy} onChange={event=>onChange('grain',event.target.value)}>{['Month','Quarter','Year'].map(grain=><option key={grain}>{grain}</option>)}</select></label>
    <label>Reporting Period<select aria-label="Reporting Period" value={data?.period||''} disabled={busy||loading} onChange={event=>onChange('period',event.target.value)}>{data?.periods.map(period=><option key={period.value} value={period.value}>{period.title}</option>)}</select></label>
    <label>Compare Actuals Against<select aria-label="Compare Actuals Against" value={selection.baseline} disabled={busy} onChange={event=>onChange('baseline',event.target.value)}><option value="both">Budget & Forecast</option><option value="budget">Budget</option><option value="forecast">Forecast</option></select></label>
    <label>Currency<select aria-label="Currency" value={selection.currency} disabled={busy} onChange={event=>onChange('currency',event.target.value)}>{['AED','USD','GBP','EUR','SAR'].map(currency=><option key={currency}>{currency}</option>)}</select></label>
    <small>Monthly source totals. Currency label only; no FX conversion.</small>
  </section>;
}
