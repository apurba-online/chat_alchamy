from __future__ import annotations
from ..models import Claim, EvidenceItem


def verify_claims(claims: list[Claim], evidence: list[EvidenceItem]) -> tuple[list[Claim], float]:
    valid = {e.id for e in evidence}
    verified = []
    for claim in claims:
        ids = [i for i in claim.support_evidence_ids if i in valid]
        verified.append(claim.model_copy(update={"support_evidence_ids": ids, "verified": bool(ids)}))
    rate = sum(c.verified for c in verified) / len(verified) if verified else 0.0
    return verified, rate
