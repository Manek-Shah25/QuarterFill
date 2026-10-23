from quarterfill.cash import cash_balance
from quarterfill.sec import SECClient
from quarterfill.research import Research
from test_engine import fact, PERIODS


def cash_fact(value, tag, **kw):
    return fact(value, start=None, concept='us-gaap:'+tag, **kw)


def balance(facts):
    return cash_balance('Test','TEST',facts,2024,1,PERIODS)


def test_cash_only_and_combined_cash_are_definitions_not_conflicting_aliases():
    cash = cash_fact(100,'Cash')
    assert balance([cash]).value == 100
    assert balance([cash,cash_fact(150,'CashAndCashEquivalentsAtCarryingValue')]).value == 150
    combined = balance([cash,cash_fact(50,'CashEquivalentsAtCarryingValue')])
    assert combined.value == 150 and combined.verified and combined.components


def test_restricted_cash_is_never_substituted_for_ordinary_cash():
    assert balance([cash_fact(50,'RestrictedCash')]).value is None
    total = cash_fact(150,'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents')
    assert balance([total]).value is None
    assert balance([total,cash_fact(50,'RestrictedCash')]).value is None
    result = balance([total,cash_fact(50,'RestrictedCashAndCashEquivalents')])
    assert result.value == 100 and result.verified
    assert balance([cash_fact(100,'Cash',end='2023-12-31')]).value is None


def test_conflicting_cash_total_does_not_fall_back_to_a_different_definition():
    assert balance([cash_fact(100,'CashAndCashEquivalentsAtCarryingValue'),
                    cash_fact(200,'CashAndCashEquivalentsAtCarryingValue'),cash_fact(50,'Cash')]).value is None


def test_real_tmdx_cash_is_available_and_checked_in_all_four_quarters():
    client = SECClient()
    company, submissions = client.company(1756262)
    research = Research(client,company,submissions)
    research.investigate(2025)
    cells = [research.cell('Cash',2025,q) for q in (1,2,3,4)]
    assert [c.value for c in cells] == [310143000,400575000,466174000,488366000]
    assert all(c.verified for c in cells)
    assert all(f.concept=='us-gaap:Cash' for c in cells for f in c.inputs)
