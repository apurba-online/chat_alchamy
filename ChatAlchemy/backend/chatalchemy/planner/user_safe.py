from __future__ import annotations

import re

from ..models import Entity, Operation, QueryPlan
from .rule_based import RuleBasedPlanner as _BaseRuleBasedPlanner


class RuleBasedPlanner(_BaseRuleBasedPlanner):
    """User-facing guardrails around the frozen rule-based planner.

    The publication benchmark remains tied to the frozen method commit. These
    guards only prevent obvious natural-language parsing failures in the web
    application, such as interpreting "gene is" as gene symbol "IS".
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

        return super().plan(q)

    @classmethod
    def _gene(cls, q: str):
        gene = _BaseRuleBasedPlanner._gene(q)
        if gene and gene.upper() in cls._GENE_STOPWORDS:
            return None
        return gene
