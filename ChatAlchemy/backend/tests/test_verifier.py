from chatalchemy.models import Claim,EvidenceItem
from chatalchemy.generation.verifier import verify_claims
def test_verifier_rejects_missing_ids():
    e=EvidenceItem(id='e1',source='x',subject='s',predicate='p',value='v'); claims,rate=verify_claims([Claim(text='x',support_evidence_ids=['e1']),Claim(text='y',support_evidence_ids=['bad'])],[e]); assert claims[0].verified and not claims[1].verified and rate==0.5
