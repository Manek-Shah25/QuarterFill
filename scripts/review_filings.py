"""Prepare source excerpts for human review; generated values are NOT manual fixtures."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from quarterfill.sec import SECClient
from quarterfill.research import Research
from quarterfill.concepts import BY_NAME

TARGETS={
    'AAPL':['Inventory','Revenue','Cost of revenue','Capital expenditures'],
    'WMT':['Inventory','Cost of revenue','Accounts payable'],
    'MSFT':['Deferred revenue (current)','Deferred revenue (noncurrent)','Finite-lived intangible assets'],
    'ADBE':['Deferred revenue (current)','Cash from operations','Stock-based compensation'],
    'UNH':['Receivables','Combined receivables','Goodwill','Intangible assets'],
    'CAT':['Inventory','Property and equipment, net','Depreciation and amortization','Property depreciation and amortization','Capital expenditures'],
    'JPM':['Revenue','Total assets','Total liabilities','Equity including noncontrolling interests','Cash from operations'],
}


if __name__=='__main__':
    client=SECClient()
    companies={c['ticker']:c for c in client.companies()}
    output=[]
    for ticker,names in TARGETS.items():
        company,submissions=client.company(companies[ticker]['cik_str'])
        research=Research(client,company,submissions)
        research.investigate(2025)
        research.version_policy='original'
        cells=[research.cell(n,2025,4 if BY_NAME[n].kind=='instant' else 0) for n in names]
        output.append({'ticker':ticker,'cik':company['cik'],'cells':[c.audit() for c in cells]})
        print(ticker,[(c.metric,str(c.value),c.verified) for c in cells],flush=True)
        Path('data/validation/overhaul-review.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
