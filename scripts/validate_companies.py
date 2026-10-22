"""Measured automated source matching, not a substitute for manual financial review."""
import argparse
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from quarterfill.sec import SECClient, SECError
from quarterfill.research import Research

TICKERS=['AAPL','MSFT','AMZN','GOOGL','META','NVDA','TSLA','JPM','BAC','WMT','COST','XOM','JNJ','PG','KO']


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--year',type=int,default=2025)
    parser.add_argument('--tickers',nargs='+',default=TICKERS)
    args=parser.parse_args()
    client=SECClient(cache='data/snapshots')
    companies={c['ticker']:c for c in client.companies()}
    target=Path('data/validation'); target.mkdir(parents=True,exist_ok=True)
    reports=[]
    for ticker in args.tickers:
        try:
            payload,submissions=client.company(companies[ticker]['cik_str'])
            research=Research(client,payload,submissions,history=True)
            research.investigate(args.year)
            cells=[research.cell(metric,args.year,q) for metric in ('Revenue','Capital expenditures','Cash','Diluted EPS') for q in range(1,5)]
            available=sum(c.value is not None for c in cells)
            matched=sum(c.verified for c in cells)
            report={'ticker':ticker,'year':args.year,'type':'Automated source matching; manual review pending',
                    'requested_cells':len(cells),'available_cells':available,'document_matched_cells':matched,
                    'cells':[c.audit() for c in cells], 'investigation':research.log,
                    'retrieved_at':datetime.now(timezone.utc).isoformat()}
            (target/f'{ticker}-{args.year}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            reports.append({k:v for k,v in report.items() if k not in ('cells','investigation')})
            print(ticker, 'available',available,'of',len(cells),'matched',matched,flush=True)
        except (SECError,KeyError) as exc:
            reports.append({'ticker':ticker,'error':str(exc)})
            print(ticker,str(exc),flush=True)
        combined=[]
        for path in target.glob(f'*-{args.year}.json'):
            recorded=json.loads(path.read_text(encoding='utf-8'))
            combined.append({k:v for k,v in recorded.items() if k not in ('cells','investigation')})
        (target/'summary.json').write_text(json.dumps(combined,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
