from __future__ import annotations
from ..models import Claim,EvidenceItem
def verify_claims(claims:list[Claim],evidence:list[EvidenceItem]):
    ids={e.id for e in evidence};verified=[]
    for c in claims:verified.append(c.model_copy(update={"supported":bool(c.support_ids) and all(s in ids for s in c.support_ids)}))
    return verified,(sum(c.supported for c in verified)/len(verified) if verified else 1.0)
