from chatalchemy.generation import verify_claims
from chatalchemy.models import Claim,EvidenceItem
def test_claim_verification():
    e=EvidenceItem.build(subject="x",predicate="p",value="v",source="s");claims,rate=verify_claims([Claim(text="x",support_ids=[e.id]),Claim(text="y",support_ids=["missing"])],[e]);assert [c.supported for c in claims]==[True,False];assert rate==0.5
