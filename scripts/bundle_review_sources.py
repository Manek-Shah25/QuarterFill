"""Bundle authentic cached responses used by the seven-company regression suite."""
import gzip
import json
from pathlib import Path
from urllib.parse import urlparse

CIKS={320193,104169,789019,796343,731766,18230,19617}
target=Path('data/snapshots')
for path in Path('data/cache').glob('*.json'):
    envelope=json.loads(path.read_text(encoding='utf-8'))
    parts=urlparse(envelope['url']).path.split('/')
    selected=any(f'CIK{cik:010}' in parts[-1] for cik in CIKS)
    selected=selected or ('data' in parts and any(str(cik) in parts for cik in CIKS))
    if selected and not (target/(path.name+'.gz')).exists():
        with gzip.open(target/(path.name+'.gz'),'wt',encoding='utf-8') as stream:
            json.dump(envelope,stream)
print('Bundled original response envelopes; run snapshot_manifest.py to verify checksums.')
