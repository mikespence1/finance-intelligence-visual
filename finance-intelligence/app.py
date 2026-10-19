"""Streamlit demo. Uploaded data stays in session memory; not a production ledger."""
import io
import os
import pandas as pd
import plotly.express as px
import streamlit as st
from src.finance import build_kpis, compare_scenarios
from src.ai import generate_board_commentary

st.set_page_config(page_title='Packaging Finance Intelligence', page_icon='📊', layout='wide')
st.title('Packaging Finance Intelligence')
st.caption('Financial reporting • Manufacturing KPIs • Board insights | MVP / demonstration')


def load_default(name):
    return pd.read_csv(f'data/{name}.csv')


def read_upload(upload, name):
    if upload is None:
        return load_default(name)
    if upload.name.lower().endswith('.xlsx'):
        return pd.read_excel(upload)
    return pd.read_csv(upload)

with st.sidebar:
    st.header('Data & reporting')
    st.warning('Demo only. Uploads and AI summaries are not approved for confidential company data without security controls.')
    source = st.radio('Data source', ['Sample dataset', 'Upload finance files'])
    if source == 'Upload finance files':
        finance_file = st.file_uploader('Finance (CSV or XLSX)', type=['csv','xlsx'])
        ops_file = st.file_uploader('Operations (CSV or XLSX)', type=['csv','xlsx'])
        balance_file = st.file_uploader('Closing balances (CSV or XLSX)', type=['csv','xlsx'])
        if not all([finance_file, ops_file, balance_file]):
            st.info('Provide all three files to display uploaded financial results.')
            st.stop()
    grain = st.selectbox('Reporting period', ['Month', 'Quarter', 'Year'])
    currency = st.text_input('Reporting currency label', 'AED', max_chars=8)

try:
    if source == 'Sample dataset':
        finance, ops, balances = (load_default(n) for n in ['finance','operations','balances'])
    else:
        finance = read_upload(finance_file, 'finance')
        ops = read_upload(ops_file, 'operations')
        balances = read_upload(balance_file, 'balances')
    kpis = build_kpis(finance, ops, balances, grain)
except (ValueError, KeyError, TypeError) as error:
    st.error(f'Data validation failed: {error}')
    st.stop()

labels = sorted(kpis.label.unique())
if not labels:
    st.warning('No reporting periods found.')
    st.stop()
selected = st.selectbox('Select reporting period', labels, index=len(labels)-1)
period = kpis[(kpis.label == selected) & (kpis.scenario == 'actual')]
if period.empty:
    st.warning('No actuals found for the selected period.')
    st.stop()
r = period.iloc[0]
comparison = compare_scenarios(kpis, selected)

cols = st.columns(4)
for col, name, suffix in zip(cols, ['Revenue','Gross Profit','EBITDA','EBITDA Margin %'], [currency,currency,currency,'%']):
    val = r[name]
    display = f'{val:,.1f}%' if suffix == '%' else f'{suffix} {val:,.0f}'
    col.metric(name, display)

tab1, tab2, tab3, tab4 = st.tabs(['Performance','Manufacturing & working capital','Board pack','AI financial analyst'])
with tab1:
    st.subheader('Financial performance')
    chart = kpis[kpis.scenario.isin(['actual','budget'])]
    metric = st.selectbox('Metric', ['Revenue','Gross Profit','EBITDA','Net Profit','Gross Margin %','EBITDA Margin %'])
    fig = px.bar(chart, x='label', y=metric, color='scenario', barmode='group',
                 labels={'label': grain, 'scenario':'Scenario'})
    st.plotly_chart(fig, use_container_width=True)
    st.subheader('Actual vs budget')
    st.dataframe(comparison, hide_index=True, use_container_width=True)
with tab2:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Output (tonnes)', f"{r['production_tonnes']:,.0f}")
    c2.metric('Scrap rate', f"{r['Scrap Rate %']:.2f}%")
    c3.metric('DSO (days)', f"{r['DSO']:.1f}")
    c4.metric('Cash conversion (days)', f"{r['Cash Conversion Cycle']:.1f}")
    st.plotly_chart(px.line(kpis[kpis.scenario == 'actual'], x='label', y=['Scrap Rate %','EBITDA Margin %'], markers=True), use_container_width=True)
    st.caption('Working capital ratios use closing AR/AP/inventory and period sales/COGS. Interpret annual/quarterly ratios in light of seasonality.')
with tab3:
    st.subheader(f'Board reporting — {selected}')
    st.write('Financial and operational KPIs (actual vs budget). Numbers are computed from the uploaded files.')
    st.dataframe(comparison, hide_index=True, use_container_width=True)
    csv = comparison.to_csv(index=False).encode('utf-8')
    st.download_button('Download period KPI report (CSV)', csv, file_name=f'board_kpis_{selected}.csv', mime='text/csv')
    with pd.ExcelWriter((output := io.BytesIO()), engine='openpyxl') as writer:
        comparison.to_excel(writer, sheet_name='Board KPIs', index=False)
        kpis.to_excel(writer, sheet_name='KPI History', index=False)
    st.download_button('Download management report (Excel)', output.getvalue(),
                       file_name=f'finance_management_{selected}.xlsx',
                       mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
with tab4:
    st.subheader('AI board narrative')
    st.info('AI is optional. Clicking Generate sends the selected period’s calculated KPI table to your configured OpenAI API endpoint. It does not upload raw transaction files.')
    if st.button('Generate board commentary', type='primary'):
        try:
            with st.spinner('Generating commentary'):
                commentary = generate_board_commentary(comparison, selected, grain)
            st.markdown(commentary)
            st.download_button('Download commentary', commentary, file_name=f'commentary_{selected}.md')
        except Exception as error:
            st.error(f'AI generation unavailable: {error}')
st.caption('Demo assumptions: single entity/currency, calendar fiscal year, positive debit-style expense inputs, no consolidation or currency translation.')
