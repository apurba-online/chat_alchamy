from __future__ import annotations
from itertools import combinations
from typing import Any
from ..models import ConflictAssessment,EvidenceItem
MULTIVALUED={"clinical_trial","targeting_drug","known_drug","gene_disease_association","disease_gene_association","dailymed_label_record","fda_application_record"};CONTEXT_KEYS={"condition","disease","efo_id","jurisdiction","formulation","trial","phase","status"}
def _norm(v:Any)->str:
    if isinstance(v,dict):return str(sorted((str(k).lower(),_norm(val)) for k,val in v.items()))
    if isinstance(v,list):return str(sorted(_norm(x) for x in v))
    return str(v).strip().lower()
def assess_pair(a:EvidenceItem,b:EvidenceItem)->ConflictAssessment:
    if _norm(a.value)==_norm(b.value):return ConflictAssessment(evidence_a=a.id,evidence_b=b.id,relation="agreement",reason="The normalized values agree.")
    if a.predicate in MULTIVALUED:return ConflictAssessment(evidence_a=a.id,evidence_b=b.id,relation="complementary",reason="The predicate is naturally multi-valued, so different records can coexist.")
    qa={k:_norm(v) for k,v in a.qualifiers.items() if k in CONTEXT_KEYS and v not in (None,"",[])};qb={k:_norm(v) for k,v in b.qualifiers.items() if k in CONTEXT_KEYS and v not in (None,"",[])};shared=set(qa)&set(qb)
    if any(qa[k]!=qb[k] for k in shared):return ConflictAssessment(evidence_a=a.id,evidence_b=b.id,relation="context_difference",reason="Values differ under different biomedical context qualifiers.")
    return ConflictAssessment(evidence_a=a.id,evidence_b=b.id,relation="conflict",reason="Values are incompatible for the same normalized subject, predicate, and available context.")
def analyze_conflicts(evidence:list[EvidenceItem])->list[ConflictAssessment]:
    groups={}
    for e in evidence:groups.setdefault((e.subject.strip().lower(),e.predicate),[]).append(e)
    out=[]
    for group in groups.values():
        for a,b in combinations(group,2):
            if a.id!=b.id:out.append(assess_pair(a,b))
    return out
