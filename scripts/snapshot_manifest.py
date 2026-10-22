import gzip
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

directory=Path('data/snapshots')
records=[]
for path in sorted(directory.glob('*.json.gz')):
    with gzip.open(path,'rt',encoding='utf-8') as stream:
        envelope=json.load(stream)
    assert urlparse(envelope['url']).hostname in ('www.sec.gov','data.sec.gov')
    assert hashlib.sha256(envelope['body'].encode()).hexdigest()==envelope['sha256']
    records.append({'file':path.name,'url':envelope['url'],'retrieved_at_unix':envelope['at'],'sha256':envelope['sha256']})
(directory/'manifest.json').write_text(json.dumps({'type':'Authentic SEC response inventory; not live','records':records},indent=2),encoding='utf-8')
print(f'Validated {len(records)} compressed official response envelopes')
