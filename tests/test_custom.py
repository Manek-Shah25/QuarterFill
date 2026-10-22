from dataclasses import replace
import pytest
from quarterfill.research import Research
from quarterfill.engine import reconstruct
from quarterfill.concepts import Metric
from test_engine import FLOWS, PERIODS, cell


def test_explicit_segment_scope():
    metric=Metric('Segment revenue','Custom','flow',(),unit='USD')
    facts=[replace(f,concept='custom:Revenue',dimensions=('custom:SegmentAxis=custom:A',)) for f in FLOWS]
    selected=reconstruct('T','T',metric,facts,2024,2,PERIODS,'custom:Revenue',('custom:SegmentAxis=custom:A',))
    assert selected.value==160
    assert reconstruct('T','T',metric,facts,2024,2,PERIODS,'custom:Revenue').value is None


def test_qualitative_requires_exact_disclosure():
    research=Research.__new__(Research)
    research.company={'cik':1}
    research.documents={'0000000001-24-000001':([], 'The company has no inventory because its operations consist solely of services.')}
    research.filings=[{'accessionNumber':'0000000001-24-000001','primaryDocument':'report.htm'}]
    missing=cell([],1)
    with pytest.raises(ValueError):
        research.classify_disclosure(missing,'0000000001-24-000001','Invented disclosure not present','Not applicable','Reason')
    result=research.classify_disclosure(missing,'0000000001-24-000001',research.documents['0000000001-24-000001'][1],
                                      'Not applicable','Requested scope has no inventory by the explicit disclosure.')
    assert result.value is None and result.status=='Not applicable'
    assert result.disclosure_evidence[0]['source_matched']
