from dataclasses import replace
from types import SimpleNamespace
from quarterfill.sec import SECClient
from quarterfill.research import Research
from quarterfill.segments import segment_build
from test_engine import FLOWS, PERIODS


def test_segment_math_scope_and_missing():
    revenue = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
    facts = [replace(f, concept=revenue) for f in FLOWS]
    for member, share in [('FoodSafetyMember', 0.6), ('AnimalSafetyMember', 0.4)]:
        facts += [replace(f, value=f.value * str_decimal(share),
                   dimensions=('us-gaap:StatementBusinessSegmentsAxis=test:' + member,))
                  for f in facts[:4]]
    # An overlapping product total and a multi-axis detail must never enter the sum.
    facts += [replace(facts[0], dimensions=('srt:ProductOrServiceAxis=test:AllProductsMember',)),
              replace(facts[0], dimensions=('us-gaap:StatementBusinessSegmentsAxis=test:FoodSafetyMember',
                                             'srt:ProductOrServiceAxis=test:ProductsMember'))]
    research = SimpleNamespace(facts=facts, company={'entityName':'Test'}, submissions={'tickers':['TEST']},
                               periods=lambda year: PERIODS)
    build = segment_build(research, 2024)[0]
    assert set(build['rows']) == {'Food Safety', 'Animal Safety'}
    assert build['rows']['Food Safety'][3].value == 150
    assert build['rows']['Food Safety'][3].verified
    assert all(c == 'The segments add up to company revenue.' for c in build['checks'])
    research.facts = [f for f in facts if not (f.dimensions and 'AnimalSafetyMember' in f.dimensions[0] and f.end == PERIODS[1][4])]
    build = segment_build(research, 2024)[0]
    assert build['rows']['Animal Safety'][3].value is None
    assert build['totals'][3][0].value is None


def str_decimal(value):
    from decimal import Decimal
    return Decimal(str(value))


def test_real_neog_and_apple_segments():
    for cik, expected in [(711377, {'Food Safety', 'Animal Safety'}),
                           (320193, {'Americas', 'Europe', 'Greater China', 'Japan', 'Rest Of Asia Pacific'})]:
        client = SECClient()
        company, submissions = client.company(cik)
        research = Research(client, company, submissions)
        research.investigate(2025)
        build = segment_build(research, 2025)[0]
        assert set(build['rows']) == expected
        assert all(cells[0].value is not None and cells[0].verified for cells in build['rows'].values())
        assert build['checks'][0] == 'The segments add up to company revenue.'
        if cik == 711377:
            assert build['rows']['Food Safety'][3].value == 161826000
            # Later NEOG disclosures disagree: preserve the conflict rather than guess.
            assert build['rows']['Animal Safety'][3].value is None
