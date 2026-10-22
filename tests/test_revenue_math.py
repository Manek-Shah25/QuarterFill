from dataclasses import replace
from types import SimpleNamespace
from quarterfill.revenue_math import RevenueMath
from quarterfill.segments import supplemental_rows
from quarterfill.presentation import explanation
from test_engine import fact, PERIODS


REVENUE = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'


def model(facts):
    research = SimpleNamespace(company={'entityName':'Test'}, submissions={'tickers':['TEST']}, periods=lambda y: PERIODS)
    return RevenueMath(research, 2024, [replace(f, concept=REVENUE) for f in facts])


def test_all_reported_period_paths_can_find_fourth_quarter():
    m = model([fact(10), fact(20,start='2024-04-01',end='2024-06-30'),
               fact(30,start='2024-07-01',end='2024-09-30'), fact(100,end='2024-12-31',form='10-K')])
    cells = m.cells(REVENUE, (), 'Revenue')
    assert [c.value for c in cells] == [10,20,30,40,100]
    assert cells[3].verified
    assert len(cells[3].inputs) == 4
    assert cells[3].audit()['components']


def test_two_quarters_do_not_invent_the_other_two_or_a_zero():
    m = model([fact(10),fact(20,start='2024-04-01',end='2024-06-30')])
    assert [c.value for c in m.cells(REVENUE, (), 'Revenue')] == [10,20,None,None,None]


def test_inconsistent_period_paths_are_flagged():
    m = model([fact(10),fact(20,start='2024-04-01',end='2024-06-30'),fact(90,end='2024-06-30')])
    assert all(c.value is None for c in m.cells(REVENUE, (), 'Revenue')[:2])
    assert m.cells(REVENUE, (), 'Revenue')[0].status == 'Ambiguous or conflicting'


def test_parent_minus_sibling_and_temporal_paths_work_together():
    axis = 'us-gaap:StatementBusinessSegmentsAxis='
    a, b = (axis+'test:AMember',), (axis+'test:BMember',)
    facts = []
    for table, end, parent, av, bv in [('q1','2024-03-31',100,60,40),
                                     ('q2','2024-06-30',250,150,None),
                                     ('fy','2024-12-31',700,420,280)]:
        for dims, value in [((),parent),(a,av),(b,bv)]:
            if value is not None:
                facts.append(fact(value,end=end,dimensions=dims,table=table))
    m = model(facts)
    cells = m.cells(REVENUE,b,'Business B')
    assert cells[1].value == 60
    assert cells[1].verified
    # The complete group proof and individual source amounts remain available.
    assert any(c.disclosure_evidence for c in m.values[(REVENUE,b)].values())
    assert cells[2].value is None  # Two remaining unknown quarters are still underdetermined.


def test_overlap_does_not_create_a_residual():
    axis = 'srt:ProductOrServiceAxis='
    facts = [fact(100,table='one'), fact(70,table='one',dimensions=(axis+'test:AMember',)),
             fact(80,table='one',dimensions=(axis+'test:BMember',)),
             fact(200,end='2024-06-30',table='two'),
             fact(120,end='2024-06-30',table='two',dimensions=(axis+'test:AMember',))]
    m = model(facts)
    assert not m.partitions
    assert m.cells(REVENUE,(axis+'test:BMember',),'B')[1].value is None


def test_two_complete_product_views_are_equations_not_one_overlapping_sum():
    axis = 'srt:ProductOrServiceAxis='
    facts = []
    for table, children in [('broad', [('A',60),('B',40)]), ('detail',[('X',30),('Y',70)])]:
        facts.append(fact(100,table=table))
        facts.extend(fact(value,table=table,dimensions=(axis+'test:'+name+'Member',)) for name,value in children)
    facts += [fact(250,end='2024-06-30'), fact(150,end='2024-06-30',dimensions=(axis+'test:AMember',)),
              fact(80,end='2024-06-30',dimensions=(axis+'test:XMember',))]
    m = model(facts)
    assert len(m.partitions) == 2
    assert m.cells(REVENUE,(axis+'test:BMember',),'B')[1].value == 60
    assert m.cells(REVENUE,(axis+'test:YMember',),'Y')[1].value == 100


def test_percentage_and_core_have_real_inputs_and_zero_is_not_divided():
    parent = ('us-gaap:StatementBusinessSegmentsAxis=test:FoodMember',)
    genomics = tuple(sorted((*parent,'srt:ProductOrServiceAxis=test:GenomicsMember')))
    m = model([fact(100), fact(70,dimensions=parent), fact(20,dimensions=genomics)])
    extras = supplemental_rows(m,REVENUE,parent,'Food')
    assert extras['% of company revenue'][0].value == 70
    assert extras['Core revenue (minus Genomics)'][0].value == 50
    assert '× 100' in explanation(extras['% of company revenue'][0])['formula']
    m = model([fact(0), fact(0,dimensions=parent)])
    assert supplemental_rows(m,REVENUE,parent,'Food')['% of company revenue'][0].value is None


def test_conflicting_independent_group_equations_do_not_pick_the_first():
    axis = 'us-gaap:StatementBusinessSegmentsAxis='
    a, b = (axis+'test:AMember',), (axis+'test:BMember',)
    x = tuple(sorted((*b,'srt:ProductOrServiceAxis=test:XMember')))
    y = tuple(sorted((*b,'srt:ProductOrServiceAxis=test:YMember')))
    facts = [fact(100,table='root'),fact(60,dimensions=a,table='root'),fact(40,dimensions=b,table='root'),
             fact(40,dimensions=b,table='children'),fact(10,dimensions=x,table='children'),fact(30,dimensions=y,table='children'),
             fact(250,end='2024-06-30'),fact(150,end='2024-06-30',dimensions=a),
             fact(60,end='2024-06-30',dimensions=x),fact(50,end='2024-06-30',dimensions=y)]
    cell = model(facts).cells(REVENUE,b,'Business B')[1]
    assert cell.value is None and cell.status == 'Ambiguous or conflicting'
