"""Compare a Git revision and this resolver against fixed, source-reviewed figures.

Both runs use the default strict version policy and the same cached SEC payloads.
Unsupported metrics count as missing. This is a coverage regression, not a claim
of independent audit accuracy across all companies.
"""
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from quarterfill.sec import SECClient
from quarterfill.research import Research
from quarterfill.concepts import BY_NAME


def main(ref='c314c96569290ca976b448c00ae71f36c28845b1'):
    expected=json.loads(Path('tests/fixtures/overhaul_expected.json').read_text())
    results=[]
    with tempfile.TemporaryDirectory(prefix='quarterfill-baseline-') as tmp:
        package=Path(tmp)/'baseline_quarterfill'; package.mkdir()
        files=subprocess.check_output(['git','ls-tree','-r','--name-only',ref,'quarterfill'],text=True).splitlines()
        for path in files:
            if path.endswith('.py'):
                destination=package/Path(path).relative_to('quarterfill')
                destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes(subprocess.check_output(['git','show',ref+':'+path]))
        sys.path.insert(0,tmp)
        old=importlib.import_module('baseline_quarterfill.research')
        old_registry=importlib.import_module('baseline_quarterfill.concepts').BY_NAME
        client=SECClient()
        for ticker,spec in expected['companies'].items():
            company,submissions=client.company(spec['cik'])
            before=old.Research(client,company,submissions); before.investigate(2025)
            after=Research(client,company,submissions); after.investigate(2025)
            for name,value in spec['metrics'].items():
                q=4 if BY_NAME[name].kind=='instant' else 0
                original=before.cell(name,2025,q) if name in old_registry else None
                revised=after.cell(name,2025,q)
                results.append({'ticker':ticker,'metric':name,'expected':value,
                    'baseline_value':str(original.value) if original and original.value is not None else None,
                    'revised_value':str(revised.value) if revised.value is not None else None,
                    'baseline_matches':bool(original and original.verified and original.value==Decimal(value)),
                    'revised_matches':revised.verified and revised.value==Decimal(value)})
            print(ticker,flush=True)
    output={'baseline_commit':ref,'version_policy':'strict for both implementations','requested':len(results),
            'baseline_matches':sum(r['baseline_matches'] for r in results),
            'revised_matches':sum(r['revised_matches'] for r in results),'results':results}
    Path('data/validation/overhaul-benchmark.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    print({k:v for k,v in output.items() if k!='results'})


if __name__=='__main__':
    main(*sys.argv[1:])
