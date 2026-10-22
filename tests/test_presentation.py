from dataclasses import replace
from decimal import Decimal
from quarterfill.presentation import amount, explanation
from test_engine import cell, FLOWS


def test_subtraction_is_explained_with_exact_amounts():
    result=explanation(cell(FLOWS,4))
    assert result['formula']=='$700 − $450 = $250'
    assert 'full year' in result['steps'][0]
    assert 'first 3 quarters' in result['steps'][1]
    assert 'quarter 4' in result['steps'][2]


def test_missing_never_looks_like_zero():
    missing=explanation(cell([],1))
    assert amount(None)=='—'
    assert missing['formula']==''
    assert 'guessing' in missing['steps'][1]
    assert amount(Decimal(0))=='$0'


def test_rounding_is_only_in_statement_display():
    assert amount(Decimal('3982000'),'USD',True)=='3.982'
    assert amount(Decimal('3982000'))=='$3,982,000'
    assert amount(Decimal('1.23'),'USD/shares')=='$1.23 per share'


def test_unverified_amount_is_explained():
    result=explanation(cell([replace(FLOWS[0],verified=False)],1))
    assert 'not checked' in result['note']
