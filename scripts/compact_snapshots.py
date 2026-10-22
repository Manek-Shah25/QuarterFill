"""Losslessly compress acquired SEC envelopes for free hosting."""
import gzip
from pathlib import Path

for path in Path('data/snapshots').glob('*.json'):
    if path.name == 'manifest.json':
        continue
    target=path.with_suffix('.json.gz')
    with gzip.open(target,'wb',compresslevel=9) as stream:
        stream.write(path.read_bytes())
    # Remove only the exact envelope whose verified compressed replacement was written.
    with gzip.open(target,'rb') as stream:
        assert stream.read() == path.read_bytes()
    path.unlink()
