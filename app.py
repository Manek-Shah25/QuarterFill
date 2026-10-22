"""A small, plain-language interface for SEC financial statements."""
import os
from datetime import date, datetime
from html import escape

import pandas as pd
import streamlit as st

from quarterfill.companies import resolve_companies
from quarterfill.concepts import BY_NAME, DERIVED, METRICS
from quarterfill.presentation import amount, explanation, input_name, period, quarter_name, readable_date
from quarterfill.research import Research
from quarterfill.sec import SECClient, SECError, filing_url
from quarterfill.segments import segment_build, revenue_details


PAGES = ['Quarterly Lookup', 'Three-Statement Builder', 'Missing Data Investigator',
         'SEC Filing Explorer', 'Methodology and Data Health']
STATEMENTS = {'Income statement': 'Income', 'Balance sheet': 'Balance sheet', 'Cash flow statement': 'Cash flow'}
STATEMENTS['Revenue by segment'] = 'Segments'
METRIC_NAMES = {'SG&A': 'Selling, general and administrative costs', 'R&D': 'Research and development',
                'Diluted EPS': 'Earnings per share (diluted)', 'Basic EPS': 'Earnings per share (basic)'}

st.set_page_config(page_title='QuarterFill', page_icon='◧', layout='wide')
st.markdown('''<style>
.block-container{padding-top:2.4rem;max-width:1250px;padding-bottom:3rem}
h1{letter-spacing:-.045em}h2,h3{letter-spacing:-.02em}
[data-testid="stSidebar"]{background:#edf3f5}
.eyebrow{color:#087e8b;font-size:.8rem;letter-spacing:.12em;font-weight:700;text-transform:uppercase}
.work-answer{background:#eef7f5;border:1px solid #c8e2db;border-radius:14px;padding:24px;margin:12px 0 20px}
.work-answer .equation{font-size:clamp(1.15rem,2vw,1.8rem);font-weight:700;color:#164c47;line-height:1.6}
.work-answer .answer-label{color:#46716a;font-size:.85rem;margin-bottom:8px}
.source-card{border-left:3px solid #b8d4d0;padding:0 0 0 14px;margin:14px 0}
[data-testid="stMetric"]{background:#f0f5f7;border-radius:12px;padding:18px}
</style>''', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">Company financials, made clear</div>', unsafe_allow_html=True)
st.title('QuarterFill')
st.caption('Find a company. See its statements. Understand how a missing number was filled in.')
page = st.sidebar.radio('Pages', PAGES)


def configuration(name):
    try:
        return st.secrets.get(name, os.getenv(name, ''))
    except FileNotFoundError:
        return os.getenv(name, '')


@st.cache_resource
def client_resource(ua, mirror):
    return SECClient(ua, snapshot_url=mirror)


client = client_resource(configuration('SEC_USER_AGENT'), configuration('QUARTERFILL_SNAPSHOT_URL'))


def metric_label(name):
    return METRIC_NAMES.get(name, name)


def sentence(text):
    # Currency signs must remain text, not be interpreted as math delimiters.
    st.markdown(text.replace('$', r'\$'))


def show_work(cell, key):
    view = explanation(cell)
    st.subheader('How we got this number')
    st.caption(f'{metric_label(cell.metric)} · {quarter_name(cell.quarter)} · {cell.year}')
    answer = amount(cell.value, cell.unit) if cell.value is not None else view['label']
    st.markdown(f'<div class="work-answer"><div class="answer-label">{escape(view["label"])}</div>'
                f'<div class="equation">{escape(view["formula"] or answer)}</div></div>', unsafe_allow_html=True)
    for i, step in enumerate(view['steps'], 1):
        sentence(f'**{i}.** {step}')
    shown_start = None if cell.inputs and all(f.start is None for f in cell.inputs) else cell.start
    st.caption(period(shown_start, cell.end))
    if view['note']:
        st.info(view['note'])
    if cell.components:
        for i, component in enumerate(cell.components):
            with st.expander(f'{metric_label(component.metric)}: see this part of the calculation'):
                show_work(component, f'{key}_part_{i}')
    if cell.inputs:
        with st.expander('Check the company’s reports'):
            # Keep every supporting version available, without showing internal identifiers.
            seen = set()
            for i, fact in enumerate(cell.inputs):
                identity = (fact.url, fact.start, fact.end, fact.value)
                if identity in seen:
                    continue
                seen.add(identity)
                title = input_name(cell, i) if len(cell.inputs) == 2 and cell.operation == '-' else 'Reported amount'
                st.markdown(f'**{title}**')
                sentence(amount(fact.value, fact.unit))
                st.caption(period(fact.start, fact.end))
                report = 'Annual report' if fact.form.startswith('10-K') else 'Quarterly report'
                if fact.filed:
                    st.caption(f'{report} · filed {readable_date(fact.filed)}')
                if fact.url:
                    st.link_button('Read the original report', fact.url, key=f'{key}_source_{i}')
                if not fact.verified:
                    st.caption('This amount still needs to be checked against the original report.')
    for i, evidence in enumerate(cell.disclosure_evidence):
        st.text(evidence['quote'])
        st.link_button('Read the supporting report', evidence['url'], key=f'{key}_evidence_{i}')


def build_cells(research, names, years):
    return [research.cell(name, year, q) for name in names for year in range(years[0], years[1] + 1)
            for q in ([1, 2, 3, 4, 0] if name in BY_NAME and BY_NAME[name].kind == 'flow' else [1, 2, 3, 4])]


def statement_table(research, statement, years, key):
    if statement == 'Revenue by segment':
        revenue_segments(research, years, key)
        return smaller_revenue_groups(research, years, key)
    names = [m.name for m in METRICS if m.statement == STATEMENTS[statement]]
    cells = build_cells(research, names, years)
    st.session_state['cells'] = cells
    rows = []
    for year in range(years[0], years[1] + 1):
        for name in names:
            row = {'Line item': metric_label(name)}
            if years[0] != years[1]:
                row['Year'] = year
            for c in (c for c in cells if c.metric == name and c.year == year):
                label = 'Year total' if c.quarter == 'FY' else c.quarter
                value = amount(c.value, c.unit, compact=c.unit == 'USD')
                if c.value is not None and not c.verified:
                    value += ' · check'
                elif c.value is not None and c.status in ('Mathematically calculated', 'Derived from reported components'):
                    value += ' · calculated'
                row[label] = value
            rows.append(row)
    st.caption('Dollar amounts are in millions. Per-share amounts and share counts are labeled separately. A dash means we do not have a reliable number.')
    st.dataframe(pd.DataFrame(rows).fillna('—'), hide_index=True, width='stretch')
    if any(c.value is not None and not c.verified for c in cells):
        st.caption('“Check” means we still need to check the amount against the original company report.')
    left, middle, right = st.columns([3, 1, 1])
    name = left.selectbox('Explain a line item', names, format_func=metric_label, key=f'{key}_metric')
    year = middle.selectbox('Year', range(years[0], years[1] + 1), key=f'{key}_year')
    q = right.selectbox('Quarter', [1, 2, 3, 4], format_func=lambda n: f'Q{n}', key=f'{key}_quarter')
    show_work(research.cell(name, year, q), key)


def revenue_segments(research, years, key):
    st.write('See which parts of the business bring in revenue. We use the segments named in the company’s reports.')
    year = st.selectbox('Segment year', range(years[0], years[1] + 1), key=f'{key}_segment_year')
    builds = segment_build(research, year)
    if not builds:
        st.info('We could not find a reliable business-segment revenue breakdown in the reports we opened. Read the company’s segment note for more detail.')
        return
    build = builds[0]
    labels = ['Q1', 'Q2', 'Q3', 'Q4', 'Year total']
    rows = []
    for name, cells in build['rows'].items():
        row = {'Business segment': name}
        for label, cell in zip(labels, cells):
            row[label] = amount(cell.value, 'USD', compact=True)
            if cell.value is not None and cell.operation == '-':
                row[label] += ' · calculated'
        rows.append(row)
    for name, index in [('Sum of segments', 0), ('Company revenue', 1)]:
        rows.append({'Business segment': name, **{label: amount(pair[index].value, 'USD', compact=True)
                     for label, pair in zip(labels, build['totals'])}})
    st.caption('Dollar amounts are in millions. A dash means we do not have a reliable number. Segment names and definitions can change between years.')
    st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
    left, right = st.columns([3, 1])
    name = left.selectbox('Explain a segment', list(build['rows']), key=f'{key}_segment')
    q = right.selectbox('Quarter or year', range(5), format_func=lambda i: labels[i], key=f'{key}_segment_quarter')
    check = build['checks'][q]
    if check == 'The segments add up to company revenue.':
        st.success(check)
    else:
        st.info(check)
    with st.expander('Explain the main segment number'):
        show_work(build['rows'][name][q], f'{key}_segment_work')
    with st.expander('How the segments add together'):
        show_work(build['totals'][q][0], f'{key}_segment_total')


def smaller_revenue_groups(research, years, key):
    year = st.session_state.get(f'{key}_segment_year', years[0])
    details = revenue_details(research, year)
    # The main table already shows these standalone business-segment views.
    details = [g for g in details if g['parent'] != 'Whole company' or g['name'] != 'Business groups']
    st.subheader('Smaller revenue groups')
    st.caption('Open a business to see the smaller groups it reports. Separate product or country views stay separate. Do not add these tables to the main segments: that would count the same revenue again.')
    if not details:
        st.info('We could not find smaller revenue groups in the reports we opened. The company may not publish this detail, or it may only appear in written notes or an untagged table.')
        return
    def view_name(i):
        group = details[i]
        return f'{group["parent"]} → {group["name"]} (view {i + 1})'
    details.sort(key=lambda g: (not bool(g['scope']), g['parent'], g['name']))
    index = st.selectbox('Choose a business or revenue view', range(len(details)), format_func=view_name,
                         key=f'{key}_detail_view')
    group = details[index]
    labels = ['Q1', 'Q2', 'Q3', 'Q4', 'Year total']
    st.markdown(f'**{group["parent"]} — {group["name"]}**')
    if not group['scope']:
        st.caption('The report provides this view for the whole company. It does not identify a parent business for each row, so we have not assigned one.')
    rows = []
    for row in group['rows']:
        values = {'Revenue group': row['name']}
        for label, cell in zip(labels, row['cells']):
            values[label] = amount(cell.value, 'USD', compact=True)
            if cell.value is not None and cell.operation == '-':
                values[label] += ' · calculated'
        rows.append(values)
    rows.append({'Revenue group': 'Reported total for this view', **{
        label: amount(cell.value, 'USD', compact=True) for label, cell in zip(labels, group['parent_cells'])}})
    st.caption('Dollar amounts are in millions. A dash means a reliable number is unavailable. Groups and definitions may change between reports.')
    st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
    left, right = st.columns([3, 1])
    selected = left.selectbox('Explain a smaller group', range(len(group['rows'])),
                format_func=lambda i: group['rows'][i]['name'], key=f'{key}_detail_row_{index}')
    q = right.selectbox('Period', range(5), format_func=lambda i: labels[i], key=f'{key}_detail_period')
    st.info(group['checks'][q])
    show_work(group['rows'][selected]['cells'][q], f'{key}_detail_work')
    with st.expander('Check this group total'):
        show_work(group['totals'][q], f'{key}_detail_sum')
        show_work(group['parent_cells'][q], f'{key}_detail_parent')


def methodology():
    st.subheader('How QuarterFill works')
    st.markdown('''**1. Find the report.** We look at the company’s reports filed with the SEC.

**2. Look for the number.** If the company reported it for that quarter, we show it.

**3. Fill a gap when the math is safe.** Some reports add several quarters together.
We subtract the earlier quarters to find the one that is missing.''')
    with st.container(border=True):
        st.markdown('**A simple example**')
        sentence('Imagine a company spent $100 over the whole year. It spent $70 in the first three quarters.')
        st.markdown('<div class="work-answer"><div class="answer-label">Spending in the last quarter</div>'
                    '<div class="equation">$100 − $70 = $30</div></div>', unsafe_allow_html=True)
        st.caption('This is only an example, not a real company result.')
    st.subheader('What the labels mean')
    st.markdown('''**Found in a report:** The company gave us the number.

**Calculated:** We worked it out using numbers from the company’s reports. You can see every step.

**Not enough information:** We cannot safely work it out. We leave a blank instead of guessing.

**Reports disagree:** The reports show different amounts. We leave the number blank until it can be checked.''')
    st.subheader('A few simple rules')
    st.markdown('''- A blank is **not** the same as zero.
- Cash, debt and other balances are amounts **on a date**. We do not subtract them to fill a quarter.
- Earnings per share need special care. We do not subtract yearly per-share numbers.
- Companies can use different year-end dates. We use the dates in their reports.''')
    st.subheader('Are the reports available?')
    research = st.session_state.get('research')
    if not research:
        st.info('Look up a company first. We will show which reports we could check here.')
        return
    st.write(research.company['entityName'])
    checked = len(research.documents)
    unavailable = len({row.get('url') or row.get('file') for row in research.log
                       if row.get('status') == 'Filing verification unavailable'})
    col1, col2 = st.columns(2)
    col1.metric('Reports opened', checked)
    col2.metric('Reports we could not open', unavailable)
    if unavailable:
        st.warning('Some reports could not be checked. Affected numbers may be blank or need checking.')
    else:
        st.success('We could open the reports listed for this lookup. This does not mean every line item was available.')
    events = st.session_state.get('lookup_events', [])
    saved = any('snapshot' in event.get('status', '') for event in events)
    st.caption('Some reports came from saved copies of SEC filings.' if saved else 'Reports may come from the SEC or a previously saved copy.')
    times = [event['retrieved'] for event in events if event.get('retrieved')]
    if times:
        oldest = datetime.fromtimestamp(min(times)).strftime('%b %d, %Y')
        newest = datetime.fromtimestamp(max(times)).strftime('%b %d, %Y')
        st.caption(f'Report copies were saved on {oldest}.' if oldest == newest else f'Report copies were saved between {oldest} and {newest}.')


if page == 'Methodology and Data Health':
    methodology()
else:
    with st.form('company_lookup'):
        left, right = st.columns([3, 2])
        company_query = left.text_input('Company name or ticker', 'AAPL', placeholder='For example, NEOG or Apple')
        years = right.slider('Years', 2009, date.today().year, (date.today().year - 1, date.today().year - 1))
        run = st.form_submit_button('Show financial statements', type='primary')
    if run:
        for previous in ('research', 'cells', 'request', 'lookup_events'):
            st.session_state.pop(previous, None)
        event_start = len(client.events)
        try:
            with st.spinner('Finding the company and reading its reports…'):
                matches = resolve_companies(client.companies(), company_query)
                if len(matches) != 1:
                    if matches:
                        st.warning('More than one company has that name. Enter its ticker: ' + ', '.join(c['ticker'] for c in matches[:15]))
                    else:
                        st.warning('We could not find that company. Check the ticker or try its full name.')
                    st.stop()
                payload, submissions = client.company(matches[0]['cik_str'])
                research = Research(client, payload, submissions, history=True)
                for year in range(years[0], years[1] + 1):
                    research.investigate(year)
                st.session_state['research'] = research
                st.session_state['request'] = years
        except SECError:
            st.error('We could not get this company’s reports right now. Please try again later.')
        st.session_state['lookup_events'] = client.events[event_start:]
    research = st.session_state.get('research')
    if not research:
        st.info('Enter a company above to see its financial statements.')
    else:
        years = st.session_state['request']
        st.subheader(research.company['entityName'])
        if page == 'Quarterly Lookup':
            statement = st.radio('Financial statement', list(STATEMENTS), horizontal=True)
            statement_table(research, statement, years, 'lookup')
        elif page == 'Three-Statement Builder':
            for statement, tab in zip(STATEMENTS, st.tabs(list(STATEMENTS))):
                with tab:
                    statement_table(research, statement, years, STATEMENTS[statement])
        elif page == 'Missing Data Investigator':
            st.write('Choose the number you want to check. We will look for it and show the math if it can be calculated.')
            names = list(BY_NAME) + list(DERIVED)
            left, middle, right = st.columns([3, 1, 1])
            name = left.selectbox('Line item', names, format_func=metric_label)
            year = middle.selectbox('Year', range(years[0], years[1] + 1))
            q = right.selectbox('Quarter', [1, 2, 3, 4], format_func=lambda n: f'Q{n}')
            if st.button('Check the reports again'):
                with st.spinner('Looking for more information…'):
                    research.investigate_concept(name)
            show_work(research.cell(name, year, q), 'investigator')
        elif page == 'SEC Filing Explorer':
            st.write('Read the original company reports behind the numbers.')
            inspected = {row.get('accession') for row in research.log if row.get('accession')}
            filings = sorted([f for f in research.filings if f['accessionNumber'] in inspected],
                             key=lambda f: f.get('reportDate', ''), reverse=True)
            if not filings:
                st.info('No reports could be opened for this lookup yet.')
            else:
                def report_label(index):
                    filing = filings[index]
                    name = 'Annual report' if filing['form'].startswith('10-K') else 'Quarterly report'
                    return f'{name} · period ending {readable_date(filing.get("reportDate"))}'
                index = st.selectbox('Company report', range(len(filings)), format_func=report_label)
                filing = filings[index]
                st.caption(f'Filed {readable_date(filing["filingDate"])}')
                st.link_button('Read the original report', filing_url(research.company['cik'], filing))
                document = research.documents.get(filing['accessionNumber'])
                if document:
                    query = st.text_input('Find a word in this report', placeholder='For example, inventory or stock compensation')
                    if query:
                        text = document[1]
                        position = text.casefold().find(query.casefold())
                        if position >= 0:
                            st.markdown('**From the company’s report**')
                            st.text(text[max(0, position - 180):position + 900])
                        else:
                            st.info('We did not find those words. Try a shorter word or read the full report above.')
                else:
                    st.info('We could not open a copy here. You can try the original report link above.')

st.divider()
st.caption('Based on SEC filings. Check the original reports before using the numbers in a financial decision.')
