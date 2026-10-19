"""Display helpers; reporting identifiers and financial calculations stay unchanged."""
import re

import pandas as pd
import plotly.graph_objects as go

NAVY = '#0B1F33'
TEAL = '#00A6A6'
METRIC_LABELS = {
    'production_tonnes': 'Good production', 'scrap_tonnes': 'Material wastage',
    'waste_cost': 'Material wastage cost', 'orders_shipped': 'Orders shipped',
    'returned_orders': 'Returned orders', 'returned_order_value': 'Returned order value',
    'Accounts Receivable': 'Outstanding customer invoices',
    'Material Payables': 'Outstanding material payments',
}
LOWER_BETTER = {'scrap_tonnes', 'Scrap Rate %', 'waste_cost', 'returned_orders',
                'Return Rate %', 'returned_order_value', 'Operating Expenses', 'Staff Costs', 'Other Operating Expenses',
                'Overdue Receivables', 'Overdue Material Payables', 'DSO', 'DIO', 'Cash Conversion Cycle'}


def title_case(text):
    """Capitalize words while retaining financial acronyms such as EBITDA and DSO."""
    return re.sub(r'[A-Za-z]+', lambda match: match[0] if match[0].isupper() else match[0].capitalize(), text)


def period_label(label, grain):
    period = pd.Period(label, freq={'Month': 'M', 'Quarter': 'Q', 'Year': 'Y'}[grain])
    if grain == 'Month':
        return period.start_time.strftime('%B %Y')
    if grain == 'Quarter':
        return f'Q{period.quarter} {period.year} · {period.start_time:%b}–{period.end_time:%b}'
    return f'{period.year} · Jan–Dec'


def format_metric(value, name, currency):
    if pd.isna(value):
        return 'No Data'
    if '%' in name:
        return f'{value:,.1f}%'
    if name in ['DSO', 'DIO', 'DPO', 'Cash Conversion Cycle', 'Days']:
        return f'{value:,.1f} days'
    if name in ['orders_shipped', 'returned_orders']:
        return f'{value:,.0f} orders'
    if name == 'Headcount':
        return f'{value:,.0f} people'
    if name.endswith('_tonnes') or name.endswith('Stock Tonnes'):
        return f'{value:,.1f} tonnes'
    return f'{currency} {value:,.0f}'


def narrative_sections(text):
    """Split Markdown headings, with a readable fallback for unstructured responses."""
    titles = ['Executive summary', 'Performance vs budget and forecast', 'Performance vs budget', 'Performance vs forecast', 'Risks and questions', 'Proposed actions']
    heading = re.compile(
        r'^\s*(?:#{1,6}\s*|\*\*)?(?:\d+[.)]\s*)?('
        + '|'.join(titles) + r')\s*:?(?:\*\*)?\s*:?[ \t]*(.*)$', re.I)
    sections = []
    title, body = 'Overview', []
    for line in text.splitlines():
        match = heading.match(line)
        if match:
            if '\n'.join(body).strip():
                sections.append((title, '\n'.join(body).strip()))
            title, body = match.group(1).capitalize(), [match.group(2)] if match.group(2) else []
        else:
            body.append(line)
    if '\n'.join(body).strip():
        sections.append((title, '\n'.join(body).strip()))
    return sections or [('Overview', 'No commentary was returned.')]


def performance_chart(kpis, metric, grain, selected, currency, baseline='budget'):
    fig = go.Figure()
    labels = sorted(kpis.label.unique())
    # Use one numeric coordinate system for points, ticks and the selection marker.
    # Date-like strings can otherwise auto-select a date axis while the marker
    # is interpreted as a timestamp close to 1970, compressing all recent data.
    positions = list(range(len(labels)))
    periods = [pd.Period(label, freq={'Month': 'M', 'Quarter': 'Q', 'Year': 'Y'}[grain]) for label in labels]
    tick_labels = [
        p.start_time.strftime('%b<br>%Y') if grain == 'Month'
        else f'Q{p.quarter}<br>{p.year}' if grain == 'Quarter'
        else str(p.year)
        for p in periods
    ]
    stride = max(1, (len(labels) + 11) // 12)
    tick_positions = sorted(set(positions[::stride] + positions[-1:]))
    if baseline not in ['budget', 'forecast', 'both']:
        raise ValueError('Choose budget, forecast or both')
    series = [('budget', 'Budget', '#667085', 'dash'), ('forecast', 'Forecast', '#F26B5B', 'dot')]
    series = [item for item in series if baseline == 'both' or item[0] == baseline]
    series.append(('actual', 'Actual', TEAL, 'solid'))
    for scenario, title, color, dash in series:
        data = kpis[kpis.scenario == scenario].set_index('label').reindex(labels)
        fig.add_trace(go.Scatter(
            x=positions, y=data[metric], name=title, mode='lines+markers',
            line=dict(color=color, width=3, dash=dash), marker=dict(size=7),
            customdata=[period_label(label, grain) for label in labels],
            hovertemplate='%{customdata}<br>' + title + ': %{y:,.2f}<extra></extra>',
            connectgaps=False,
        ))
    fig.add_vline(x=labels.index(selected), line_width=1, line_dash='dot', line_color=NAVY)
    fig.update_layout(
        template='plotly_white', height=420, hovermode='x unified',
        font=dict(color=NAVY), margin=dict(l=20, r=25, t=50, b=65),
        legend=dict(orientation='h', y=1.12, x=0),
        yaxis_title=('Percent (%)' if '%' in metric else 'Tonnes' if metric.endswith('_tonnes') or metric.endswith('Stock Tonnes')
                     else 'Orders' if metric in ['orders_shipped', 'returned_orders'] else 'People' if metric == 'Headcount'
                     else 'Days' if metric in ['DSO', 'DIO', 'DPO', 'Cash Conversion Cycle'] else currency),
        xaxis=dict(type='linear', title=grain, tickmode='array', tickvals=tick_positions,
                   ticktext=[tick_labels[i] for i in tick_positions], tickangle=0,
                   range=[-.35, max(len(labels)-1, 0)+.35], automargin=True,
                   showgrid=False, fixedrange=True),
        yaxis=dict(gridcolor='#EDF1F5', zerolinecolor='#D6DFE8', automargin=True,
                   tickformat=',.2~s', nticks=6),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig
