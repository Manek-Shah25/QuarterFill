"""Retrieve authentic official SEC records; no fabricated fallback data."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quarterfill.sec import SECClient
from quarterfill.research import Research


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tickers',nargs='+',required=True)
    parser.add_argument('--years',nargs='+',type=int,required=True)
    args=parser.parse_args()
    client=SECClient(cache='data/snapshots')
    companies={c['ticker']: c for c in client.companies()}
    manifest=[]
    for ticker in args.tickers:
        payload,submissions=client.company(companies[ticker]['cik_str'])
        research=Research(client,payload,submissions,history=True)
        for year in args.years:
            research.investigate(year)
        manifest.append({'ticker':ticker,'years':args.years,'investigation':research.log})
    Path('data/snapshots/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
