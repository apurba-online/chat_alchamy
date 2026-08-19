from __future__ import annotations

from itertools import combinations

from ..models import ConflictAssessment, EvidenceItem


class ConflictEngine:
    MULTIVALUED_PREDICATES = {"fda_approval_record", "dailymed_label_record", "clinical_trial", "molecular_target"}
    CONTEXT_KEYS = ("condition", "jurisdiction", "formulation", "trial")

    def assess(self, evidence: list[EvidenceItem]) -> list[ConflictAssessment]:
        assessments: list[ConflictAssessment] = []
        groups: dict[tuple[str, str], list[EvidenceItem]] = {}
        for item in evidence:
            groups.setdefault((item.subject.lower(), item.predicate), []).append(item)
        for items in groups.values():
            for a, b in combinations(items, 2):
                if a.source == b.source and a.source_record_id == b.source_record_id:
                    continue
                relation, reason = self._relation(a, b)
                assessments.append(ConflictAssessment(evidence_a=a.id, evidence_b=b.id, relation=relation, reason=reason))
        return assessments

    def _relation(self, a: EvidenceItem, b: EvidenceItem) -> tuple[str, str]:
        if a.value == b.value:
            return "agreement", "The two evidence items report the same value."
        if a.predicate in self.MULTIVALUED_PREDICATES:
            return "complementary", "The predicate can legitimately have multiple values or records."
        for key in self.CONTEXT_KEYS:
            av = a.qualifiers.get(key)
            bv = b.qualifiers.get(key)
            if av and bv and av != bv:
                return "context_difference", f"The values refer to different {key} contexts."
        return "conflict", "Same entity and predicate have incompatible values without a visible context difference."
