from streamlit.testing.v1 import AppTest
from pathlib import Path


def test_page_routes_without_network():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    assert not app.exception
    assert 'Excel Export Center' not in app.sidebar.radio[0].options
    for page in ('Methodology and Data Health', 'SEC Filing Explorer',
                 'Three-Statement Builder', 'Missing Data Investigator'):
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception


def test_real_bundled_lookup():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=40).run()
    app.slider[0].set_range(2025,2025)
    app.button[0].click().run()
    assert not app.exception
    assert 'cells' in app.session_state
    cells=app.session_state['cells']
    assert any(c.value is not None and c.verified for c in cells)
    next(r for r in app.radio if r.label=='Financial statement').set_value('Revenue by segment').run()
    assert not app.exception
    assert 'Americas' in app.dataframe[0].value['Business segment'].tolist()


def test_neog_exact_ticker_end_to_end():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=40).run()
    app.text_input[0].set_value('NEOG')
    app.slider[0].set_range(2025,2025)
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state['research'].company['cik']==711377
    next(r for r in app.radio if r.label=='Financial statement').set_value('Cash flow statement').run()
    quarters=[c for c in app.session_state['cells'] if c.quarter!='FY' and c.metric=='Stock-based compensation']
    assert len(quarters)==4
    assert all(c.value is not None and c.verified for c in quarters)


def test_methodology_is_plain_language():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    app.sidebar.radio[0].set_value('Methodology and Data Health').run()
    text=' '.join(element.value for element in app.markdown)
    for word in ('XBRL','CompanyFacts','DuckDB','Parquet','accession','regression','interpolation'):
        assert word not in text
    assert 'A blank is' in text
    assert 'A simple example' in text
    assert not app.file_uploader


def test_loaded_pages_hide_developer_fields():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'),default_timeout=60).run()
    app.button[0].click().run()
    for page in ('Quarterly Lookup','Three-Statement Builder','Missing Data Investigator','SEC Filing Explorer','Methodology and Data Health'):
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception
        text=' '.join(str(e.value) for e in app.markdown)
        for word in ('us-gaap:','contextref','Audit ID','Fact ID','CompanyConcept','DuckDB'):
            assert word not in text
        for table in app.dataframe:
            assert not {'Concept','Dimensions','Audit ID','Unit','SEC URL'}.intersection(table.value.columns)
    assert not app.get('download_button')
