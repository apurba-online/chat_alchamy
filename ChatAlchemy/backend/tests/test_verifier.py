from chatalchemy.generation import ClaimVerifier
from chatalchemy.models import Claim, EvidenceItem


def test_claim_verifier_requires_real_evidence_ids():
    evidence = [EvidenceItem.build(subject="A", predicate="p", value="v", source="S")]
    claims = [Claim(text="supported", support_ids=[evidence[0].id]), Claim(text="unsupported", support_ids=["missing"])]
    verified = ClaimVerifier().verify(claims, evidence)
    assert verified[0].supported is True
    assert verified[1].supported is False
    assert ClaimVerifier.supported_rate(verified) == 0.5
