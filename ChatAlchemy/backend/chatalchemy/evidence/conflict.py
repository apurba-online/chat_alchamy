from __future__ import annotations

from collections import defaultdict
from ..models import ConflictAssessment, EvidenceItem

_CONTEXT_KEYS = ("condition", "jurisdiction", "formulation", "trial", "status", "phases")
_MULTI = {"clinical_trial", "label_record", "target_drug", "disease_target", "gene_disease", "fda_application_record"}


def assess_conflicts(evidence: list[EvidenceItem]) -> list[ConflictAssessment]:
    groups: dict[tuple[str, str], list[EvidenceItem]] = defaultdict(list)
    for ev in evidence:
        groups[((ev.canonical_subject or ev.subject).casefold(), ev.predicate)].append(ev)
    out: list[ConflictAssessment] = []
    for _, items in groups.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                if a.value == b.value:
                    relation, reason = "agreement", "Both evidence records support the same value."
                elif a.predicate in _MULTI:
                    relation, reason = "complementary", "The predicate is naturally multi-valued; different records can both be true."
                else:
                    differing_context = [k for k in _CONTEXT_KEYS if a.context.get(k) != b.context.get(k) and (a.context.get(k) is not None or b.context.get(k) is not None)]
                    if differing_context:
                        relation, reason = "context_difference", f"Values differ under different context: {', '.join(differing_context)}."
                    else:
                        relation, reason = "conflict", "The records assert incompatible values without a detected contextual distinction."
                out.append(ConflictAssessment(evidence_ids=[a.id, b.id], relation=relation, reason=reason))
    return out
