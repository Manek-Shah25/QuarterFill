from test_engine import fact, cell, FLOWS


def test_direct_quarter_conflicting_ytd_is_flagged():
    direct=fact(999,start='2024-04-01',end='2024-06-30')
    result=cell(FLOWS+[direct],2)
    assert result.value is None
    assert result.status=='Ambiguous or conflicting'
