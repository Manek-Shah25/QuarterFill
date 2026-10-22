"""Portable offline analytical storage; hosted app may use ephemeral copies."""
import json
from pathlib import Path
import duckdb
import pandas as pd


def save_audits(cells, directory):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    records=[{'id':c.id, 'ticker':c.ticker, 'metric':c.metric, 'year':c.year,
              'quarter':c.quarter, 'status':c.status, 'verified':c.verified,
              'audit_json':json.dumps(c.audit())} for c in cells]
    if not records:
        return
    frame=pd.DataFrame(records)
    con=duckdb.connect(str(directory/'provenance.duckdb'))
    try:
        con.register('incoming',frame)
        con.execute('CREATE TABLE IF NOT EXISTS audits AS SELECT * FROM incoming WHERE false')
        con.execute('INSERT INTO audits SELECT * FROM incoming WHERE id NOT IN (SELECT id FROM audits)')
        target=str(directory/'audits.parquet').replace("'","''")
        con.execute(f"COPY audits TO '{target}' (FORMAT PARQUET)")
    finally:
        con.close()
