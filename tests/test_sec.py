import json
from quarterfill.sec import SECClient, SECError


def test_historical_index_failure_keeps_recent_records(tmp_path, monkeypatch):
    c=SECClient(cache=tmp_path)
    def fail(url):
        raise SECError('Blocked')
    monkeypatch.setattr(c,'json',fail)
    submissions={'filings':{'recent':{'accessionNumber':['a'],'form':['10-Q']},'files':[{'name':'old.json'}]}}
    assert c.filings(submissions,True)==[{'accessionNumber':'a','form':'10-Q'}]
    assert c.history_errors[0]['scope']=='Historical submissions index'
