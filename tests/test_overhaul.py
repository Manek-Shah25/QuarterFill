from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from quarterfill.concepts import BY_NAME, METRICS
from quarterfill.research import Research
from quarterfill.validation import validate
from quarterfill.filing_tables import parse_tables, number
from quarterfill.taxonomy import Taxonomy, custom_candidates
from quarterfill.sec import parse_inline
from quarterfill.engine import fiscal_periods, reconstruct
from quarterfill.models import Cell
from test_engine import fact, PERIODS


def research(facts,sic='3571'):
    r=Research.__new__(Research)
    r.company={'entityName':'Test'}; r.submissions={'tickers':['TEST'],'sic':sic}
    r.facts=facts; r.filings=[]; r.documents={}; r.taxonomies={}; r.html_documents={}
    r.log=[]; r.additional_version_scans=0; r.version_policy='strict'
    r._cell_cache={}; r._interval_cache={}; r.periods=lambda year:PERIODS
    return r


def test_registry_breadth_and_exclusions():
    assert sum(m.statement=='Income' for m in METRICS)>=24
    assert sum(m.statement=='Balance sheet' for m in METRICS)>=38
    assert sum(m.statement=='Cash flow' for m in METRICS)>=27
    assert all(m.definition and m.period_type in ('duration','instant') for m in METRICS)
    r=research([fact(100,start=None,concept='us-gaap:InventoryGross'),
                fact(200,start=None,concept='us-gaap:AccountsNotesAndOtherReceivablesNetCurrent')])
    assert r.cell('Inventory',2024,1).value is None
    assert r.cell('Receivables',2024,1).value is None
    assert r.cell('Combined receivables',2024,1).value==200


def test_cost_formula_and_industry_guard():
    facts=[fact(1200,concept='us-gaap:Revenues',table='income'),fact(470,concept='us-gaap:GrossProfit',table='income')]
    c=research(facts).cell('Cost of revenue',2024,1)
    assert c.value==730 and c.verified and c.accounting_status=='Derived'
    assert c.components[0].value==1200 and c.components[1].value==470
    assert research(facts,'6021').cell('Cost of revenue',2024,1).value is None
    assert research([facts[0],replace(facts[1],table='unrelated')]).cell('Cost of revenue',2024,1).value is None


def test_general_interval_recovery_and_underdetermined_case():
    facts=[fact(100,concept='us-gaap:ShareBasedCompensation'),
           fact(300,start='2024-07-01',end='2024-09-30'),
           fact(400,start='2024-10-01',end='2024-12-31'),
           fact(1000,end='2024-12-31',form='10-K')]
    assert research(facts).cell('Stock-based compensation',2024,2).value==200
    assert research(facts[:2]).cell('Stock-based compensation',2024,2).value is None


def test_explicit_version_policy_preserves_conflicts_by_default():
    facts=[fact(100,concept='us-gaap:InventoryNet',start=None),
           fact(110,concept='us-gaap:InventoryNet',start=None,filed='2025-05-01',accession='0000000001-25-000001')]
    r=research(facts)
    assert r.cell('Inventory',2024,1).accounting_status=='Ambiguous'
    r.version_policy='original'; assert r.cell('Inventory',2024,1).value==100
    r.version_policy='latest'; assert r.cell('Inventory',2024,1).value==110


def test_validation_requires_fx_and_never_mutates_reported_amount():
    def c(name,value):
        f=fact(value)
        return Cell('Test','T',name,2024,'Q1',f.start,f.end,'Directly reported',f.value,'USD',[f])
    values=[c('Change in cash including restricted cash',10),c('Cash from operations',100),
            c('Cash from investing',-60),c('Cash from financing',-25)]
    assert validate(values)[-1].status=='Not checked'
    values.append(c('Exchange-rate effect on cash',-5))
    assert validate(values)[-1].status=='Passed'
    values[0].value=Decimal(20)
    assert validate(values)[-1].status=='Review'
    assert values[0].value==20


def test_untagged_note_requires_exact_dates_definition_scale_and_category():
    filing={'accessionNumber':'0000000001-24-000001','form':'10-Q','filingDate':'2024-05-01'}
    html='<table><tr><td>Consolidated balance sheet, in millions</td><td>March 31, 2024</td></tr><tr><td>Inventory</td><td>(12.5)</td></tr></table>'
    facts=parse_tables(html,'1',filing,'https://www.sec.gov/report.htm',METRICS,[])
    f=next(f for f in facts if f.concept=='html:inventory')
    assert f.value==-12500000 and f.start is None and f.scale==6
    assert parse_tables(html.replace('in millions',''), '1',filing,'url',METRICS,[])==[]
    assert number('( 12,500 )')==Decimal('-12500')


def test_custom_extension_needs_definition_schema_and_statement_relationship():
    tax=Taxonomy()
    tax.read('''<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:co="urn:test" xmlns:xbrli="http://www.xbrl.org/2003/instance" targetNamespace="urn:test"><xs:element name="MerchandiseInventories" id="co_MerchandiseInventories" xbrli:periodType="instant" type="xbrli:monetaryItemType"><xs:annotation><xs:documentation>Equivalent definition: InventoryNet, net of applicable allowances.</xs:documentation></xs:annotation></xs:element></xs:schema>''','schema')
    tax.labels['co:MerchandiseInventories']['label']='Inventory'
    tax.roles['co:MerchandiseInventories'].add('urn:ConsolidatedBalanceSheets')
    facts=[fact(100,start=None,concept='co:MerchandiseInventories')]
    assert custom_candidates(BY_NAME['Inventory'],tax,facts)[0].definition
    tax.concepts['co:MerchandiseInventories']['definition']='Inventory segment forecast'
    assert custom_candidates(BY_NAME['Inventory'],tax,facts)==[]
    tax.labels['co:MerchandiseInventories']['label']='Merchandise inventories'
    tax.concepts['co:MerchandiseInventories']['definition']='Carrying amount of current asset inventories, net of valuation reserves.'
    assert custom_candidates(BY_NAME['Inventory'],tax,facts)


def test_inline_parentheses_scale_and_sign_are_not_applied_twice():
    html='''<html xmlns:ix="urn:ix"><xbrli:context id="c"><xbrli:period><xbrli:instant>2024-03-31</xbrli:instant></xbrli:period></xbrli:context><xbrli:unit id="u"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit><ix:nonFraction name="co:Loss" contextRef="c" unitRef="u" sign="-" scale="6">(12)</ix:nonFraction></html>'''
    parsed,_=parse_inline(html,'1',{'accessionNumber':'a','form':'10-Q','filingDate':'2024-05-01'},'url')
    assert parsed[0].value==-12000000 and parsed[0].scale==6


def test_transition_annual_period_is_never_mislabeled_as_a_quarter():
    f=fact(100,start='2024-07-01',end='2024-12-31',form='10-KT',concept='us-gaap:Revenues')
    periods=fiscal_periods([f],2024)
    assert periods==('2024-07-01',{0:'2024-12-31'})
    assert reconstruct('T','T',BY_NAME['Revenue'],[f],2024,0,periods).value==100
    assert reconstruct('T','T',BY_NAME['Revenue'],[f],2024,4,periods).value is None


def test_presentation_formula_requires_every_calculation_child():
    facts=[fact(470,concept='us-gaap:GrossProfit',table='income'),
           fact(200,concept='us-gaap:OperatingExpenses',table='income')]
    taxonomy=Taxonomy()
    taxonomy.calculations=[('us-gaap:OperatingIncomeLoss','us-gaap:GrossProfit','1','income'),
                           ('us-gaap:OperatingIncomeLoss','us-gaap:OperatingExpenses','-1','income')]
    r=research(facts); r.taxonomies={'a':taxonomy}
    assert r.cell('Operating income',2024,1).value==270
    taxonomy.calculations.append(('us-gaap:OperatingIncomeLoss','co:ExtraExpense','-0.5','income'))
    r=research(facts); r.taxonomies={'a':taxonomy}
    assert r.cell('Operating income',2024,1).value is None
