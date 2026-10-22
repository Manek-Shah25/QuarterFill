import pytest
from quarterfill.companies import resolve_companies, CompanyDirectory
from quarterfill.sec import SECClient

COMPANIES=[{'ticker':'NEOG','title':'NEOGEN CORP','cik_str':711377},
           {'ticker':'NEO','title':'NEOGENOMICS INC','cik_str':1077183},
           {'ticker':'BRK-B','title':'BERKSHIRE HATHAWAY INC','cik_str':1067983}]


@pytest.mark.parametrize('query',['NEOG','neog',' NEOG '])
def test_exact_neog_wins_over_neogenomics(query):
    assert [c['ticker'] for c in resolve_companies(COMPANIES,query)]==['NEOG']


def test_share_class_and_cik():
    assert resolve_companies(COMPANIES,'BRK.B')[0]['ticker']=='BRK-B'
    assert resolve_companies(COMPANIES,'0000711377')[0]['ticker']=='NEOG'


def test_ambiguous_name_still_requires_choice():
    assert len(resolve_companies(COMPANIES,'neogen'))==2
    assert not resolve_companies(COMPANIES,'')


def test_literal_symbol_precedes_punctuation_alias():
    entries=COMPANIES+[{'ticker':'BRK.B','title':'A different literal symbol','cik_str':999}]
    assert resolve_companies(entries,'BRK.B')[0]['cik_str']==999


def test_every_official_sec_ticker_resolves_to_its_own_company(tmp_path):
    companies=SECClient(user_agent='',cache=tmp_path).companies()
    directory=CompanyDirectory(companies)
    for company in companies:
        for symbol in (company['ticker'],company['ticker'].lower(),' '+company['ticker']+' '):
            matches=directory.resolve(symbol)
            assert len(matches)==1, f'Ambiguous exact ticker: {symbol}'
            assert matches[0]['cik_str']==company['cik_str']
