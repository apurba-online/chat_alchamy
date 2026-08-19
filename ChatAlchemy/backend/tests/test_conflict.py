from chatalchemy.evidence import assess_pair
from chatalchemy.models import EvidenceItem
def ev(value,predicate="trial_status",qualifiers=None):return EvidenceItem.build(subject="NCT1",predicate=predicate,value=value,source="test",qualifiers=qualifiers or {})
def test_agreement():assert assess_pair(ev("Recruiting"),ev("recruiting")).relation=="agreement"
def test_context_difference():assert assess_pair(ev("approved","indication",{"condition":"NSCLC"}),ev("not approved","indication",{"condition":"melanoma"})).relation=="context_difference"
def test_conflict_same_context():assert assess_pair(ev("Recruiting"),ev("Completed")).relation=="conflict"
def test_multivalue_complementary():assert assess_pair(ev("NCT1","clinical_trial"),ev("NCT2","clinical_trial")).relation=="complementary"
