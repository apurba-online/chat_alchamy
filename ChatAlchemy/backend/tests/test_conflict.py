from chatalchemy.evidence import ConflictEngine
from chatalchemy.models import EvidenceItem


def ev(predicate, value, **qualifiers):
    return EvidenceItem.build(subject="Drug X", predicate=predicate, value=value, qualifiers=qualifiers, source=f"source-{value}")


def test_true_conflict_when_same_context_differs():
    items = [ev("regulatory_status", "approved", condition="Disease A", jurisdiction="US"), ev("regulatory_status", "phase_3", condition="Disease A", jurisdiction="US")]
    assert ConflictEngine().assess(items)[0].relation == "conflict"


def test_context_difference_not_conflict():
    items = [ev("regulatory_status", "approved", condition="Disease A"), ev("regulatory_status", "phase_3", condition="Disease B")]
    assert ConflictEngine().assess(items)[0].relation == "context_difference"


def test_multivalued_records_are_complementary():
    items = [ev("clinical_trial", "NCT1", trial="NCT1"), ev("clinical_trial", "NCT2", trial="NCT2")]
    assert ConflictEngine().assess(items)[0].relation == "complementary"
