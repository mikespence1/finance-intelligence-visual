"""Legacy Streamlit UI. The primary React/FastAPI application starts with npm run dev."""
import hashlib
import io
from itertools import count
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.finance import METRIC_GROUPS, build_kpis, compare_scenarios
from src.board_pack import board_pack
from src.ai import generate_board_commentary
from src.query_agent import ask_data, dataset_fingerprint
from src.presentation import LOWER_BETTER, METRIC_LABELS, format_metric, narrative_sections, performance_chart, period_label, title_case

st.set_page_config(page_title='Finance Intelligence', page_icon='📊', layout='wide')
st.markdown('''<style>
.block-container {padding-top: 6rem; max-width: 1480px;}
@media (max-width: 640px) {.block-container {padding-top: 5rem;}}
h1, h2, h3 {color: #142D4E; letter-spacing: -.025em;}
[class*="st-key-raised-card-"] {
    background: linear-gradient(145deg, #FFFFFF 0%, #EDF3F8 100%);
    border: 1px solid #DAE4EF; border-radius: 16px;
    box-shadow: 0 8px 20px rgba(20,45,78,.10), 0 2px 4px rgba(20,45,78,.05), inset 0 1px 0 #FFFFFF;
    padding: 1rem;
}
[data-testid="stMetricValue"] {color: #142D4E; font-weight: 700;}
[data-testid="stMetricLabel"] {color: #52677F;}
[data-testid="stSidebar"] {border-right: 1px solid #DFE7F0;}
[data-testid="stSidebar"] .st-key-reporting_page [role="radiogroup"] {gap: .5rem;}
[data-testid="stSidebar"] .st-key-reporting_page [data-testid="stRadio"] label,
[data-testid="stSidebar"] .st-key-reporting_page [role="radiogroup"] label {
    background: #EAF0F6; border-radius: 10px; padding: .65rem .8rem;
    border: 1px solid #D7E2EC; font-weight: 600;
}
[data-testid="stSidebar"] .st-key-reporting_page label:has(input:checked) {
    background: #D7EEEC; border-color: #008A87; box-shadow: 0 2px 6px rgba(20,45,78,.1);
}
.eyebrow {color: #008A87; font-size: .8rem; font-weight: 700;
    letter-spacing: .12em; line-height: 1.6; padding: .35rem 0; margin-bottom: .4rem;}
[data-baseweb="tab-list"] {gap: 1.2rem;}
</style>''', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">FINANCE INTELLIGENCE / MANAGEMENT REPORTING</div>', unsafe_allow_html=True)
st.title('Sustainable Packaging Intelligence')
st.caption('Materials & circularity · Customer returns · People & costs · Financial resilience')


card_ids = count()


def card():
    return st.container(border=True, key=f'raised-card-{next(card_ids)}')


def heading(text):
    st.subheader(title_case(text))


def load_default(name):
    return pd.read_csv(Path(__file__).parent / 'data' / f'{name}.csv')


def read_upload(upload):
    return pd.read_excel(upload) if upload.name.lower().endswith('.xlsx') else pd.read_csv(upload)


with st.sidebar:
    st.markdown('### Reporting Workspace')
    st.markdown('### Reporting & Analysis')
    page = st.radio('Reporting & Analysis', ['Financial Performance', 'Sustainability & Operations',
                    'Board Pack', 'AI Report', 'Ask Your Data'], key='reporting_page', label_visibility='collapsed')
    st.divider()
    source = st.radio('Data source', ['Sample dataset', 'Upload finance files'])
    if source == 'Sample dataset':
        st.caption('Synthetic sample data · January–December 2026')
    else:
        finance_file = st.file_uploader('Finance (CSV or XLSX)', type=['csv', 'xlsx'])
        ops_file = st.file_uploader('Operations (CSV or XLSX)', type=['csv', 'xlsx'])
        balance_file = st.file_uploader('Closing balances (CSV or XLSX)', type=['csv', 'xlsx'])
        if not all([finance_file, ops_file, balance_file]):
            st.info('Provide all three files to display uploaded financial results.')
            st.stop()
    grain = st.selectbox('Group results by', ['Month', 'Quarter', 'Year'])
    baseline = st.selectbox('Compare Actuals Against', ['budget', 'forecast', 'both'], index=2,
                            format_func=lambda value: 'Budget & Forecast' if value == 'both' else value.title())
    baseline_title = 'Budget & Forecast' if baseline == 'both' else baseline.title()
    baselines = ['budget', 'forecast'] if baseline == 'both' else [baseline]
    currency = st.text_input('Reporting currency', 'AED', max_chars=8)
    st.divider()
    st.caption('Prototype · Calendar fiscal year. Review uploaded data before using results for decisions.')
    with st.expander('Data Privacy'):
        st.write('Uploads remain in this browser session. AI reports and Ask Your Data send relevant calculated KPIs or requested source records to OpenAI. Use approved data only.')

try:
    if source == 'Sample dataset':
        finance, ops, balances = (load_default(n) for n in ['finance', 'operations', 'balances'])
    else:
        finance, ops, balances = (read_upload(f) for f in [finance_file, ops_file, balance_file])
    kpis = build_kpis(finance, ops, balances, grain)
except (ValueError, KeyError, TypeError) as error:
    st.error(f'Data validation failed: {error}')
    st.stop()

labels = sorted(kpis.label.unique())
if not labels:
    st.warning('No reporting periods found.')
    st.stop()
selected = st.selectbox('Select reporting period', labels, index=len(labels)-1,
                        format_func=lambda label: period_label(label, grain))
period = kpis[(kpis.label == selected) & (kpis.scenario == 'actual')]
if period.empty:
    st.warning('No actuals found for the selected period.')
    st.stop()
r = period.iloc[0]
comparison = compare_scenarios(kpis, selected, baseline)
display_period = period_label(selected, grain)
window = pd.Period(selected, freq={'Month': 'M', 'Quarter': 'Q', 'Year': 'Y'}[grain])
heading(display_period)
st.caption(f'Actual results against {baseline_title} · {window.start_time:%d %b %Y} – {window.end_time:%d %b %Y} · Currency: {currency}')
for comparator in baselines:
    if not ((kpis.label == selected) & (kpis.scenario == comparator)).any():
        st.warning(f'No {comparator} data for this period. Comparisons are unavailable, not zero.')

coverage = []
for dataset, name in [(finance, 'Finance'), (ops, 'Operations'), (balances, 'Closing balances')]:
    actual_dates = pd.to_datetime(dataset.loc[dataset.scenario.astype(str).str.strip().str.lower() == 'actual', 'period'])
    months = actual_dates.dt.to_period('M')
    count = months[(months >= window.start_time.to_period('M')) &
                   (months <= window.end_time.to_period('M'))].nunique()
    coverage.append((name, count))
expected = {'Month': 1, 'Quarter': 3, 'Year': 12}[grain]
st.caption('Actual data coverage: ' + ' · '.join(f'{name}: {count}/{expected} months' for name, count in coverage))
if any(count < expected for _, count in coverage):
    st.warning('Partial reporting period: some actual months are missing. Totals reflect available data; working capital ratios use the full calendar period.')


def metric_card(column, name, title=None, lower_better=False):
    row = comparison.loc[comparison.Metric == name].iloc[0]
    delta = None
    if baseline != 'both' and pd.notna(row.Actual) and pd.notna(row[baseline_title]):
        if '%' in name:
            delta = f'{row.Variance:+,.1f} pp vs {baseline}'
        elif pd.notna(row['Variance %']):
            delta = f'{row["Variance %"]:+,.1f}% vs {baseline}'
    with column:
        with card():
            st.metric(title_case(title or METRIC_LABELS.get(name, name)), format_metric(row.Actual, name, currency), delta=delta,
                      delta_color='inverse' if lower_better or name in LOWER_BETTER else 'normal')
            for comparator in baselines:
                target = comparator.title()
                variance = row['Variance vs ' + target] if baseline == 'both' else row.Variance
                relative = row['Variance % vs ' + target] if baseline == 'both' else row['Variance %']
                change = ('Unavailable' if pd.isna(variance) else f'{variance:+,.1f} pp' if '%' in name
                          else f'{relative:+,.1f}%' if pd.notna(relative) else format_metric(variance, name, currency))
                st.caption(f'{target}: {format_metric(row[target], name, currency)} · Δ {change}')


for col, name in zip(st.columns(4), ['Revenue', 'Gross Profit', 'EBITDA', 'EBITDA Margin %']):
    metric_card(col, name)

heading(page)
if page == 'Financial Performance':
    with card():
        heading('Performance Against Plan')
        st.caption('Solid Teal = Actual · Dashed Grey = Budget · Dotted Amber = Forecast · Vertical Marker = Selected Period')
        metric = st.selectbox('Financial metric', METRIC_GROUPS['Financial performance'])
        st.plotly_chart(performance_chart(kpis, metric, grain, selected, currency, baseline), use_container_width=True)
        row = comparison.loc[comparison.Metric == metric].iloc[0]
        cols = st.columns(1 + len(baselines))
        cols[0].metric('Actual · ' + display_period, format_metric(row.Actual, metric, currency))
        delta_cols = st.columns(len(baselines))
        for index, comparator in enumerate(baselines):
            target = comparator.title()
            cols[1+index].metric(target, format_metric(row[target], metric, currency))
            variance = row['Variance vs ' + target] if baseline == 'both' else row.Variance
            difference = 'Unavailable' if pd.isna(variance) else (f'{variance:+,.1f} pp' if '%' in metric else f'{currency} {variance:+,.0f}')
            delta_cols[index].metric('Variance To ' + target, difference)
    heading('People & Operating Expenses')
    for col, name in zip(st.columns(4), ['Staff Costs', 'Headcount', 'Operating Expenses', 'Other Operating Expenses']):
        metric_card(col, name)
    st.caption('Staff costs are included in operating expenses. Headcount is the latest closing employee count, not a period total.')
    with st.expander('Explore all financial and operational metrics'):
        table = comparison.copy()
        for field in [c for c in table.columns if c != 'Metric' and not c.startswith('Variance %')]:
            table[field] = table.apply(lambda item: (
                f'{item[field]:+,.1f} pp' if field.startswith('Variance') and '%' in item.Metric and pd.notna(item[field])
                else format_metric(item[field], item.Metric, currency)), axis=1)
        for field in [c for c in table.columns if c.startswith('Variance %')]:
            table[field] = table[field].map(lambda v: 'Unavailable' if pd.isna(v) else f'{v:+,.1f}%')
        table['Metric'] = table.Metric.replace(METRIC_LABELS)
        st.dataframe(table, hide_index=True, use_container_width=True)

if page == 'Sustainability & Operations':
    heading('Sustainable Materials & Manufacturing')
    for col, name, title, inverse in zip(
        st.columns(4), ['production_tonnes', 'Scrap Rate %', 'DSO', 'Cash Conversion Cycle'],
        ['Production output', 'Scrap rate', 'Receivables days', 'Cash conversion cycle'],
        [False, True, True, True],
    ):
        metric_card(col, name, title, inverse)
    for group_title in ['Materials & circularity', 'Customer returns', 'Stock & customer credit', 'Cash, suppliers & people']:
        heading(group_title)
        metrics = METRIC_GROUPS[group_title]
        for start in range(0, len(metrics), 3):
            for col, name in zip(st.columns(3), metrics[start:start+3]):
                metric_card(col, name)
    st.caption('Material waste cost and returned order value are analytical measures. They are not deducted again from reported profit. Stock quantities and credit exposures are closing balances.')
    st.caption('Customer credit headroom is approved limits less unpaid invoices. Aggregate headroom can hide individual customer breaches. Returns are recorded in-period and may relate to earlier shipments.')
    operation_metric = st.selectbox('Operational trend', [m for group in list(METRIC_GROUPS.values())[1:] for m in group],
                                    format_func=lambda name: METRIC_LABELS.get(name, name))
    st.plotly_chart(performance_chart(kpis, operation_metric, grain, selected, currency, baseline), use_container_width=True)
    with card():
        heading('Margins & Material Efficiency')
        actuals = kpis[kpis.scenario == 'actual'].copy()
        actuals['Reporting period'] = actuals.label.map(lambda label: period_label(label, grain))
        fig = px.line(actuals, x='Reporting period', y=['Scrap Rate %', 'EBITDA Margin %'],
                      markers=True, color_discrete_sequence=['#142D4E', '#008A87'],
                      labels={'value': 'Percent (%)', 'variable': 'Metric'})
        fig.update_layout(template='plotly_white', legend=dict(orientation='h', y=1.15),
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
        st.caption('Working capital ratios use closing balances and period sales/COGS. Consider seasonality when comparing months, quarters and years.')

if page == 'Board Pack':
    with card():
        heading(f'Board Reporting · {display_period}')
        st.write('Download the selected period comparison or the full KPI history for your management pack.')
        st.dataframe(comparison.rename(columns={'Metric': 'Metric (currency amounts in ' + currency + ')'}),
                     hide_index=True, use_container_width=True)
        export = comparison.copy()
        export.insert(0, 'Reporting period', display_period)
        export.insert(1, 'Currency', currency)
        both = compare_scenarios(kpis, selected, 'budget').merge(
            compare_scenarios(kpis, selected, 'forecast').drop(columns='Actual'), on='Metric', suffixes=(' vs budget', ' vs forecast'))
        both.insert(0, 'Reporting period', display_period)
        both.insert(1, 'Currency', currency)
        st.download_button('Download period KPIs · CSV', export.to_csv(index=False).encode('utf-8'),
                           file_name=f'board_kpis_{selected}.csv', mime='text/csv')
        history = kpis.copy()
        history.insert(0, 'Reporting period', history.label.map(lambda label: period_label(label, grain)))
        with pd.ExcelWriter((output := io.BytesIO()), engine='openpyxl') as writer:
            both.to_excel(writer, sheet_name='Board KPIs', index=False)
            history.to_excel(writer, sheet_name='KPI History', index=False)
        st.download_button('Download management report · Excel', output.getvalue(),
                           file_name=f'finance_management_{selected}.xlsx',
                           mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        st.download_button('Download board presentation · PowerPoint',
            board_pack(kpis, selected, grain, currency, source,
                       'Actual coverage: ' + '; '.join(f'{name}: {count}/{expected} months' for name, count in coverage)),
            file_name=f'sustainable_packaging_board_{selected}.pptx',
            mime='application/vnd.openxmlformats-officedocument.presentationml.presentation')

if page == 'AI Report':
    heading('Your AI Board Briefing')
    st.caption(f'{display_period} · Insights drawn from the selected period’s calculated KPIs')
    st.info('Generate sends the selected KPI comparison to OpenAI, rather than raw transaction files. Review commentary before sharing.')
    fingerprint = hashlib.sha256(comparison.to_json().encode()).hexdigest()
    report_key = (grain, selected, currency, baseline, fingerprint)
    if st.button('Generate board commentary', type='primary'):
        try:
            with st.spinner('Preparing your board briefing…'):
                commentary = generate_board_commentary(comparison, display_period, grain, currency=currency, baseline=baseline)
            st.session_state['board_report'] = (report_key, commentary)
        except Exception as error:
            st.error(f'AI generation unavailable: {error}')
    report = st.session_state.get('board_report')
    if report and report[0] == report_key:
        commentary = report[1]
        sections = narrative_sections(commentary)
        for start in range(0, len(sections), 2):
            for column, (title, body) in zip(st.columns(2), sections[start:start+2]):
                with column:
                    with card():
                        st.caption(f'BOARD BRIEFING · {display_period}')
                        heading(title)
                        st.markdown(body)
        st.download_button('Download commentary · Markdown', commentary, file_name=f'commentary_{selected}.md')
    else:
        with card():
            st.markdown('#### Ready When You Are')
            st.write('Generate a briefing to explore your executive summary, budget performance, risks and proposed actions in report cards.')

if page == 'Ask Your Data':
    heading('Ask Your Data')
    st.caption('Explore Financials, Materials, Returns, People And Cash')
    st.info('Questions use the loaded datasets across all available periods. Relevant results and requested source records are sent to OpenAI. Review answers against the supporting data.')
    st.caption(f'Default context: {display_period} · {baseline_title} comparison · {currency} · {source}')
    with st.expander('Example Questions & Coverage'):
        st.markdown('- How did EBITDA compare with budget in Q1 2026?\n- How did material wastage change between Q1 and Q2?\n- What were overdue material payments in December 2026?\n- How did headcount and staff costs change during 2026?')
        st.write('Customer-level details, return reasons, unprovided periods and external questions are not covered. Definitions and available aggregate figures can be explained.')
    chat_context = dataset_fingerprint(finance, ops, balances, currency, source)
    if st.session_state.get('data_chat_context') != chat_context:
        st.session_state['data_chat_context'] = chat_context
        st.session_state['data_chat'] = []
    if st.button('Clear Conversation', key='clear_data_chat'):
        st.session_state['data_chat'] = []

    def render_reply(reply):
        st.markdown(reply['answer'])
        if reply.get('limitation'):
            st.caption(reply['limitation'])
        if reply.get('source_ids'):
            st.caption('Sources: ' + ', '.join(reply['source_ids']))
        if reply.get('evidence'):
            with st.expander('Supporting Data & Calculations'):
                st.dataframe(pd.DataFrame(reply['evidence']), hide_index=True, use_container_width=True)
        if 'D1' in reply.get('source_ids', []):
            with st.expander('Metric Definitions · D1'):
                st.markdown((Path(__file__).parent / 'DATA_DICTIONARY.md').read_text(encoding='utf-8'))

    for message in st.session_state['data_chat']:
        with st.chat_message(message['role']):
            if message['role'] == 'assistant':
                render_reply(message['reply'])
            else:
                st.markdown(message['content'])
    question = st.chat_input('Ask About Your Company Performance…', max_chars=4000, key='data_question')
    if question:
        chat = st.session_state['data_chat']
        history = [{'role': m['role'], 'content': m['content']} for m in chat]
        chat.append({'role': 'user', 'content': question})
        with st.chat_message('user'):
            st.markdown(question)
        with st.chat_message('assistant'):
            try:
                with st.spinner('Checking Your Data…'):
                    reply = ask_data(question, finance, ops, balances,
                        {'currency': currency, 'selected_period': selected, 'grain': grain,
                         'baseline': baseline, 'data_source': source}, history=history)
                render_reply(reply)
                chat.append({'role': 'assistant', 'content': reply['answer'], 'reply': reply})
            except Exception:
                st.error('The Data Assistant Could Not Complete This Request. Check Your API Configuration And Connection, Then Try Again.')
                chat.pop()  # Keep failed requests out of follow-up context; input remains retryable.
        st.session_state['data_chat'] = chat[-20:]

st.caption('Calendar fiscal year · Single entity and currency · No consolidation or FX translation · Prototype for review')
