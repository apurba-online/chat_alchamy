from __future__ import annotations

from ..models import Claim, EvidenceItem


class ClaimVerifier:
    def verify(self, claims: list[Claim], evidence: list[EvidenceItem]) -> list[Claim]:
        valid_ids = {e.id for e in evidence}
        for claim in claims:
            claim.supported = bool(claim.support_ids) and all(sid in valid_ids for sid in claim.support_ids)
        return claims

    @staticmethod
    def supported_rate(claims: list[Claim]) -> float:
        if not claims:
            return 1.0
        return sum(1 for c in claims if c.supported) / len(claims)
