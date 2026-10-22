from streamlit.testing.v1 import AppTest
from pathlib import Path


def test_page_routes_without_network():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    assert not app.exception
    for page in ('Excel Export Center', 'Methodology and Data Health', 'SEC Filing Explorer',
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
