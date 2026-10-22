from io import BytesIO
from zipfile import ZipFile
import pytest
import duckdb
from quarterfill.offline import import_fsn
from quarterfill.store import save_audits
from test_engine import cell, FLOWS


def test_offline_import():
    stream=BytesIO()
    with ZipFile(stream,'w') as z:
        z.writestr('sub.txt','adsh\tcik\tform\nA\t1\t10-K\n')
        z.writestr('num.txt','adsh\ttag\tversion\tvalue\nA\tAssets\tus-gaap/2025\t100\n')
        z.writestr('tag.txt','tag\tversion\ttlabel\nAssets\tus-gaap/2025\tAssets\n')
    rows,tables=import_fsn(stream.getvalue())
    assert rows.iloc[0]['cik']=='1' and rows.iloc[0]['value']=='100'


def test_durable_idempotent_provenance(tmp_path):
    c=cell(FLOWS,4)
    save_audits([c],tmp_path)
    save_audits([c],tmp_path)
    db=duckdb.connect()
    try:
        assert db.execute('SELECT count(*) FROM read_parquet(?)',[str(tmp_path/'audits.parquet')]).fetchone()[0]==1
    finally:
        db.close()
