from chatalchemy.evidence.conflict import assess_conflicts
from chatalchemy.models import EvidenceItem
def ev(i,v,context=None,p='trial_status'): return EvidenceItem(id=i,source='x',subject='A',canonical_subject='A',predicate=p,value=v,context=context or {})
def test_agreement(): assert assess_conflicts([ev('1','yes'),ev('2','yes')])[0].relation=='agreement'
def test_context_difference(): assert assess_conflicts([ev('1','Recruiting',{'trial':'NCT1'}),ev('2','Completed',{'trial':'NCT2'})])[0].relation=='context_difference'
def test_true_conflict(): assert assess_conflicts([ev('1','A'),ev('2','B')])[0].relation=='conflict'
def test_multivalued_complementary(): assert assess_conflicts([ev('1','NCT1',p='clinical_trial'),ev('2','NCT2',p='clinical_trial')])[0].relation=='complementary'
