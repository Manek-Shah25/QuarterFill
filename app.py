"""Streamlit UI; all financial selection and calculations live in quarterfill/."""
import json
import os
from datetime import date
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from quarterfill.concepts import METRICS, BY_NAME, DERIVED, search
from quarterfill.export import workbook, fill_model
from quarterfill.research import Research
from quarterfill.sec import SECClient, SECError
from quarterfill.store import save_audits
from io import BytesIO
from zipfile import ZipFile

st.set_page_config(page_title='QuarterFill | SEC Financial Research', page_icon='◧', layout='wide')
st.markdown('''<style>.block-container{padding-top:2rem;max-width:1500px}h1{letter-spacing:-.05em}
div[data-testid="stMetric"]{background:#e9eef5;padding:18px;border-radius:8px}</style>''', unsafe_allow_html=True)
st.title('QuarterFill')
st.caption('Quarterly financials. Original disclosures. A calculation trail for every cell.')
page = st.sidebar.radio('Research workspace', ['Quarterly Lookup', 'Three-Statement Builder',
    'Missing Data Investigator', 'SEC Filing Explorer', 'Excel Export Center', 'Methodology and Data Health'])


def configuration(name):
    try:
        return st.secrets.get(name, os.getenv(name, ''))
    except FileNotFoundError:
        return os.getenv(name, '')


@st.cache_resource
def client_resource(ua, mirror):
    return SECClient(ua, snapshot_url=mirror)


client = client_resource(configuration('SEC_USER_AGENT'), configuration('QUARTERFILL_SNAPSHOT_URL'))


def audit_panel(cell):
    st.subheader(f'{cell.metric} · FY{cell.year} {cell.quarter}')
    a, b, c = st.columns(3)
    a.metric('Value (original units)', str(cell.value) if cell.value is not None else 'Unavailable')
    b.metric('Classification', cell.status)
    c.metric('Source matching', 'Document matched' if cell.verified else 'Review required')
    st.write(f'**Period:** {cell.start or "Point in time"} → {cell.end or "Unresolved"} · **Units:** {cell.unit or "Unresolved"}')
    if cell.formula:
        st.code(cell.formula, language=None)
    for reason in cell.reasoning:
        st.write(reason)
    for warning in cell.warnings:
        st.warning(warning)
    for f in cell.inputs:
        with st.expander(f'{f.concept} · {f.form} · filed {f.filed} · {f.value} {f.unit}'):
            st.write(f'Accession: {f.accession} | context: {f.context} | fact ID: {f.id}')
            st.write(f'Period: {f.start} to {f.end}; dimensions: {f.dimensions or "consolidated"}')
            if f.url:
                st.link_button('Original SEC disclosure', f.url)
            st.text(f.section or 'Document excerpt unavailable; source matching incomplete.')
    st.download_button('Download this audit (JSON)', json.dumps(cell.audit(), indent=2),
                       f'{cell.id}.json', 'application/json', key='audit_' + cell.id)
    with st.expander('Copy formula and sources'):
        st.code(cell.formula + '\n' + '\n'.join(f.url for f in cell.inputs), language=None)
    with st.expander('Investigation log'):
        st.json(cell.investigation)


def display(cells):
    st.session_state['cells'] = cells
    rows = [{'Fiscal year': c.year, 'Metric': c.metric, 'Quarter': c.quarter,
             'Value': float(c.value) if c.value is not None else None, 'Status': c.status,
             'Source matched': c.verified, 'Unit': c.unit, 'Audit ID': c.id} for c in cells]
    frame = pd.DataFrame(rows)
    st.caption('Values are shown in original reporting units. Annual columns are meaningful for additive flows only. Select a cell audit below.')
    pivot = frame.pivot(index=['Metric', 'Fiscal year'], columns='Quarter', values='Value')
    st.dataframe(pivot, width='stretch')
    st.caption('Select a row below to inspect its value and calculation. Reported and calculated classifications are shown beside every observation.')
    event = st.dataframe(frame, width='stretch', hide_index=True, on_select='rerun', selection_mode='single-row')
    labels = {c.id: f'{c.metric} · FY{c.year} {c.quarter} · {c.status}' for c in cells}
    selected_row = event.selection.rows[0] if event.selection.rows else 0
    selected = st.selectbox('Cell audit', list(labels), index=selected_row, format_func=labels.get)
    audit_panel(next(c for c in cells if c.id == selected))
    chart = frame[(frame.Quarter != 'FY') & frame.Value.notna()].copy()
    if not chart.empty:
        chart['Period'] = chart['Fiscal year'].astype(str) + ' ' + chart['Quarter']
        st.plotly_chart(px.line(chart, x='Period', y='Value', color='Metric', markers=True), width='stretch')
    col1, col2, col3 = st.columns(3)
    col1.download_button('Financial workbook', workbook(cells), 'QuarterFill.xlsx',
                         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    col2.download_button('Quarterly CSV', frame.to_csv(index=False), 'QuarterFill.csv', 'text/csv')
    col3.download_button('All cell audits', json.dumps([c.audit() for c in cells], indent=2), 'QuarterFill-audits.json')
    if st.button('Prepare portable provenance archive (DuckDB + Parquet)'):
        directory=Path('data/cache/provenance')
        save_audits(cells,directory)
        archive=BytesIO()
        with ZipFile(archive,'w') as zipped:
            for path in directory.iterdir():
                zipped.write(path,path.name)
        st.download_button('Download provenance archive',archive.getvalue(),'QuarterFill-provenance.zip')


if page == 'Methodology and Data Health':
    st.subheader('Evidence before interpolation')
    st.markdown(Path('docs/accounting_methodology.md').read_text(encoding='utf-8'))
    st.markdown(Path('docs/validation.md').read_text(encoding='utf-8'))
    st.subheader('Request and source availability')
    st.dataframe(pd.DataFrame(client.events), width='stretch')
    with st.expander('Offline SEC Financial Statement / Notes Data Set import'):
        dataset=st.file_uploader('Official SEC data set ZIP (raw disclosure review)',type=['zip'])
        if dataset:
            from quarterfill.offline import import_fsn
            try:
                rows,tables=import_fsn(dataset.getvalue())
                st.write(f'{len(rows)} numeric disclosure rows; tables: {", ".join(tables)}')
                st.dataframe(rows.head(500),width='stretch')
                st.caption('Raw import only: missing start dates and dimensional scope must be reviewed before quarterly reconstruction.')
            except (ValueError,KeyError) as exc:
                st.error(str(exc))
    st.info('Document matched means the exact fact context was found in a retrieved filing. It does not certify accounting comparability or completeness.')
elif page == 'Excel Export Center':
    cells = st.session_state.get('cells', [])
    st.subheader('Financial modeling workbook')
    if cells:
        st.download_button('Export current research', workbook(cells), 'QuarterFill.xlsx')
        uploaded = st.file_uploader('Existing model (.xlsx, maximum 25 MB)', type=['xlsx'])
        st.caption('Provide an explicit mapping. Only empty cells receiving document-matched values are eligible. Formulas and nonempty values are always preserved.')
        mapping = st.text_area('Mapping JSON: {"audit ID": ["sheet", "B4"]}', '{}')
        if uploaded and st.button('Fill eligible empty cells'):
            try:
                result, changes = fill_model(uploaded.getvalue(), json.loads(mapping), cells)
                st.dataframe(pd.DataFrame(changes, columns=['Sheet', 'Cell', 'Result']))
                st.download_button('Download updated model', result, 'QuarterFill-filled.xlsx')
            except (ValueError, KeyError, TypeError) as exc:
                st.error(f'Invalid workbook mapping: {exc}')
    else:
        st.info('Run a lookup or statement reconstruction first.')
else:
    with st.form('research_form'):
        left, right = st.columns([2, 3])
        company_query = left.text_input('Company ticker or name', 'AAPL')
        query = right.text_input('Financial line item search', 'Stock compensation')
        candidates = search(query)
        metric_name = st.selectbox('Accounting definition (confirm the intended metric)',
                                   [m.name for m in candidates] + list(DERIVED))
        years = st.slider('Fiscal years (named by annual period-end calendar year)', 2009, date.today().year,
                          (date.today().year - 5, date.today().year - 1))
        history = st.checkbox('Load historical filing index (required for older periods)', True)
        run = st.form_submit_button('Find Quarterly Values', type='primary')
    if run:
        try:
            with st.spinner('Resolving company and retrieving authentic SEC disclosures…'):
                companies = client.companies()
                matches = [c for c in companies if c['ticker'].lower() == company_query.lower() or
                           company_query.lower() in c['title'].lower()]
                if len(matches) != 1:
                    st.warning('Enter an exact ticker. Matching companies: ' + ', '.join(c['ticker'] for c in matches[:20]))
                    st.stop()
                payload, submissions = client.company(matches[0]['cik_str'])
                research = Research(client, payload, submissions, history)
                for year in range(years[0], years[1] + 1):
                    research.investigate(year)
                st.session_state['research'] = research
                st.session_state['request'] = (metric_name, years)
        except SECError as exc:
            st.error(f'SEC data access incomplete: {exc}')
            st.info('No substitute financial results have been generated. The operator can configure the authentic snapshot workflow described in DEPLOYMENT.md.')
    research = st.session_state.get('research')
    if research:
        name, selected_years = st.session_state['request']
        st.subheader(research.company['entityName'])
        if any('snapshot' in event.get('status','') for event in client.events):
            st.info('Authentic SEC snapshots are in use for some requests. These are saved disclosures, not a live feed. Retrieval times and request failures are listed in Methodology and Data Health.')
        if page == 'SEC Filing Explorer':
            term = st.text_input('Search filing concepts and source excerpts', name)
            facts = [f for f in research.facts if term.lower() in (f.concept + ' ' + f.section).lower()]
            st.dataframe(pd.DataFrame([{'Concept': f.concept, 'Value': str(f.value), 'Unit': f.unit,
                'Start': f.start, 'End': f.end, 'Dimensions': str(f.dimensions), 'SEC URL': f.url,
                'Excerpt': f.section, 'Document matched': f.verified} for f in facts]), width='stretch')
            st.caption('Extension and segment contexts are exposed for review; similar labels are not automatically treated as equivalent.')
        elif page == 'Missing Data Investigator':
            year = st.selectbox('Fiscal year', range(selected_years[0], selected_years[1]+1))
            q = st.selectbox('Quarter', [1, 2, 3, 4])
            audit_panel(research.cell(name, year, q))
        else:
            names = [name]
            if page == 'Three-Statement Builder':
                statement = st.radio('Statement', ['Income', 'Balance sheet', 'Cash flow'], horizontal=True)
                names = [m.name for m in METRICS if m.statement == statement]
            cells = [research.cell(n, year, q) for n in names
                     for year in range(selected_years[0], selected_years[1]+1)
                     for q in ([1, 2, 3, 4, 0] if n in BY_NAME and BY_NAME[n].kind == 'flow' else [1, 2, 3, 4])]
            display(cells)
    else:
        st.info('Search a company and metric to begin. No account or paid API is required for visitors.')

st.divider()
st.caption('Financial research only. Verify source disclosures and accounting comparability before using results. QuarterFill does not provide investment advice.')
