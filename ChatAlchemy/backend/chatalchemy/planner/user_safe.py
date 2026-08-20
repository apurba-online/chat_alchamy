from __future__ import annotations

import re

from ..models import Entity, Operation, QueryPlan
from .rule_based import RuleBasedPlanner as _BaseRuleBasedPlanner


class RuleBasedPlanner(_BaseRuleBasedPlanner):
    """Natural-language guardrails around the deterministic planner.

    These corrections are part of the pre-Freeze-v2 software-correctness pass.
    They address user wording that is more varied than the controlled public
    benchmark templates without replacing the auditable typed planner.
    """

    _GENE_STOPWORDS = {
        "IS",
        "ARE",
        "WAS",
        "WERE",
        "BE",
        "THE",
        "A",
        "AN",
        "WHAT",
        "WHICH",
        "WHO",
        "RESPONSIBLE",
        "ASSOCIATED",
        "RELATED",
        "INVOLVED",
        "LINKED",
        "FOR",
        "WITH",
        "IN",
        "TO",
        "OF",
    }

    _DISEASE_GENE_PATTERNS = (
        r"\bgenes?\s+(?:are\s+|is\s+)?(?:responsible\s+for|associated\s+with|related\s+to|involved\s+in|linked\s+to)\s+(.+?)(?:\?|$)",
        r"\bgenes?\s+(?:cause|causes|drives?|contributes?\s+to)\s+(.+?)(?:\?|$)",
    )

    _APPROVAL_SUBJECT_PATTERNS = (
        r"\b(?:is|was)\s+([A-Za-z0-9][A-Za-z0-9 ._-]{0,60}?)\s+FDA[- ]approved\b",
        r"\bhas\s+([A-Za-z0-9][A-Za-z0-9 ._-]{0,60}?)\s+been\s+approved\s+by\s+(?:the\s+)?FDA\b",
        r"\b(?:did|does)\s+(?:the\s+)?FDA\s+approve\s+([A-Za-z0-9][A-Za-z0-9 ._-]{0,60}?)(?:\?|$)",
    )

    @staticmethod
    def _norm(text: str | None) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", (text or "").lower()))

    @classmethod
    def _approval_subject(cls, q: str) -> str | None:
        for pattern in cls._APPROVAL_SUBJECT_PATTERNS:
            match = re.search(pattern, q, re.I)
            if match:
                value = match.group(1).strip(" .?")
                if value:
                    return value
        return None

    def plan(self, question: str) -> QueryPlan:
        q = " ".join(question.strip().split())

        # Natural disease -> gene questions should query disease associations,
        # not treat the word following "gene" as a gene symbol.
        for pattern in self._DISEASE_GENE_PATTERNS:
            match = re.search(pattern, q, re.I)
            if match:
                disease = match.group(1).strip(" .?")
                if disease:
                    return QueryPlan(
                        question=q,
                        intent="disease",
                        entities=[Entity(text=disease, type="condition")],
                        operations=[
                            Operation(
                                source="opentargets",
                                action="disease_genes",
                                arguments={"disease": disease},
                            )
                        ],
                        final_operation="list",
                    )

        plan = super().plan(q)

        # "Trials for <condition>?" is a condition-only query. The base grammar
        # can parse the same phrase as both a drug and a condition because the
        # preposition "for" is ambiguous. If both extracted entities normalize to
        # the same text, keep the condition and remove the spurious intervention.
        if plan.intent == "trials":
            drug = next((entity.text for entity in plan.entities if entity.type == "drug"), None)
            condition = str(plan.filters.get("condition") or "").strip() or None
            if drug and condition and self._norm(drug) == self._norm(condition):
                plan = plan.model_copy(
                    update={
                        "entities": [entity for entity in plan.entities if entity.type != "drug"],
                        "operations": [operation for operation in plan.operations if operation.source != "rxnorm"],
                    }
                )

        # Subject-first approval wording such as "Is pembrolizumab FDA approved?"
        # should not be parsed as the literal drug name "pembrolizumab FDA
        # approved". Replace only when an explicit FDA-approval construction is
        # present; the controlled benchmark routes remain unchanged.
        if plan.intent == "approval":
            drug = self._approval_subject(q)
            if drug:
                entities = [entity for entity in plan.entities if entity.type != "drug"]
                entities.insert(0, Entity(text=drug, type="drug"))
                operations = []
                for operation in plan.operations:
                    if operation.source in {"rxnorm", "openfda"}:
                        arguments = dict(operation.arguments)
                        arguments["drug"] = drug
                        operation = operation.model_copy(update={"arguments": arguments})
                    operations.append(operation)
                plan = plan.model_copy(update={"entities": entities, "operations": operations})

        return plan

    @classmethod
    def _gene(cls, q: str):
        gene = _BaseRuleBasedPlanner._gene(q)
        if gene and gene.upper() in cls._GENE_STOPWORDS:
            return None
        return gene
