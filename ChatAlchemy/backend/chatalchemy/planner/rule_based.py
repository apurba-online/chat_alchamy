from __future__ import annotations

import re

from ..models import Entity, Operation, QueryPlan


class RuleBasedPlanner:
    STATUS_MAP = {
        "recruiting": "RECRUITING",
        "active, not recruiting": "ACTIVE_NOT_RECRUITING",
        "active not recruiting": "ACTIVE_NOT_RECRUITING",
        "completed": "COMPLETED",
        "not yet recruiting": "NOT_YET_RECRUITING",
        "terminated": "TERMINATED",
        "withdrawn": "WITHDRAWN",
    }

    def plan(self, question: str) -> QueryPlan:
        q = " ".join(question.strip().split())
        low = q.lower()
        phase = self._phase(low)
        status = self._status(low)
        target = self._target(q)

        if target and ("fda" in low or "approved" in low) and ("trial" in low or phase or status):
            condition = self._condition(q)
            return QueryPlan(
                question=q,
                intent="cross_source",
                entities=[Entity(text=target, type="target")] + ([Entity(text=condition, type="condition")] if condition else []),
                filters={"phase": phase, "status": status, "condition": condition},
                operations=[
                    Operation(source="chembl", action="target_drugs", arguments={"target": target}),
                    Operation(source="openfda", action="approval_records"),
                    Operation(source="clinicaltrials", action="search_trials"),
                ],
                final_operation="intersection",
            )
        if any(x in low for x in ["pubchem", "smiles", "iupac", "chemical structure", "compound properties"]):
            drug = self._compound_name(q)
            return QueryPlan(question=q, intent="compound", entities=[Entity(text=drug, type="compound")] if drug else [], operations=[Operation(source="pubchem", action="compound", arguments={"name": drug})], final_operation="list")
        if target and ("drug" in low or "target" in low or "inhibitor" in low or "mechanism" in low or "molecule" in low):
            return QueryPlan(question=q, intent="target_drugs", entities=[Entity(text=target, type="target")], operations=[Operation(source="chembl", action="target_drugs", arguments={"target": target})], final_operation="list")
        if any(x in low for x in ["gene", "ensembl", "open targets", "opentargets"]):
            gene = self._gene(q)
            if gene:
                return QueryPlan(question=q, intent="gene", entities=[Entity(text=gene, type="gene")], operations=[Operation(source="opentargets", action="gene_details", arguments={"gene": gene})], final_operation="list")
        if any(x in low for x in ["disease genes", "genes associated with", "targets associated with", "disease association"]):
            disease = self._condition(q) or self._tail_phrase(q)
            return QueryPlan(question=q, intent="disease", entities=[Entity(text=disease, type="condition")] if disease else [], operations=[Operation(source="opentargets", action="disease_genes", arguments={"disease": disease})], final_operation="list")
        if "trial" in low or "clinicaltrials" in low or phase or status:
            drug = self._drug_for_trial(q)
            condition = self._condition(q)
            entities = []
            if drug:
                entities.append(Entity(text=drug, type="drug"))
            if condition:
                entities.append(Entity(text=condition, type="condition"))
            return QueryPlan(
                question=q,
                intent="trials",
                entities=entities,
                filters={"phase": phase, "status": status, "condition": condition},
                operations=[
                    Operation(source="rxnorm", action="resolve", arguments={"drug": drug}),
                    Operation(source="clinicaltrials", action="search_trials", arguments={"drug": drug, "condition": condition, "phase": phase, "status": status}),
                ],
                final_operation="count" if any(x in low for x in ["how many", "count", "number of"]) else "list",
            )
        if any(x in low for x in ["dailymed", "drug label", "label record", "spl record", "spl label"]):
            drug = self._drug_after_keyword(q, ["for", "of", "about"]) or self._tail_entity(q)
            return QueryPlan(question=q, intent="label", entities=[Entity(text=drug, type="drug")] if drug else [], operations=[Operation(source="rxnorm", action="resolve", arguments={"drug": drug}), Operation(source="dailymed", action="label_records", arguments={"drug": drug})], final_operation="list")
        if "fda" in low or "approved" in low or "approval" in low:
            drug = self._drug_after_keyword(q, ["for", "of", "is", "about"]) or self._tail_entity(q)
            return QueryPlan(question=q, intent="approval", entities=[Entity(text=drug, type="drug")] if drug else [], operations=[Operation(source="rxnorm", action="resolve", arguments={"drug": drug}), Operation(source="openfda", action="approval_records", arguments={"drug": drug})], final_operation="list")
        if any(x in low for x in ["generic identity", "generic ingredient", "generic name", "canonical", "rxcui", "identify", "resolve"]):
            drug = self._identity_drug(q)
            return QueryPlan(question=q, intent="identity", entities=[Entity(text=drug, type="drug")] if drug else [], operations=[Operation(source="rxnorm", action="resolve", arguments={"drug": drug})], final_operation="identity")
        return QueryPlan(question=q, intent="general", operations=[], final_operation="generate")

    @staticmethod
    def _phase(low: str):
        m = re.search(r"phase\s*([1-4]|i{1,3}|iv)\b", low, re.I)
        if not m:
            return None
        token = m.group(1).upper()
        return {"I": "PHASE1", "II": "PHASE2", "III": "PHASE3", "IV": "PHASE4"}.get(token, f"PHASE{token}")

    def _status(self, low: str):
        for text, canonical in sorted(self.STATUS_MAP.items(), key=lambda item: len(item[0]), reverse=True):
            if text in low:
                return canonical
        return None

    @staticmethod
    def _target(q: str):
        patterns = [
            r"targeting\s+([A-Za-z0-9_-]{2,20})",
            r"\btarget\s+([A-Za-z0-9_-]{2,20})",
            r"\bfor\s+([A-Z0-9-]{2,12})\b",
            r"\b([A-Z0-9-]{2,12})\s+inhibitors?\b",
        ]
        for pattern in patterns:
            m = re.search(pattern, q)
            if m and m.group(1).upper() not in {"FDA", "PHASE"}:
                return m.group(1).upper()
        return None

    @staticmethod
    def _gene(q: str):
        m = re.search(r"\bgene\s+([A-Za-z0-9-]{2,20})\b", q, re.I)
        if m:
            return m.group(1).upper()
        m = re.search(r"\b([A-Z][A-Z0-9-]{1,14})\b", q)
        if m and m.group(1) not in {"FDA", "DNA", "RNA", "NCT", "SPL"}:
            return m.group(1)
        m = re.search(r"(?:target)\s+([A-Za-z0-9-]{2,20})", q, re.I)
        return m.group(1).upper() if m else None

    @staticmethod
    def _condition(q: str):
        if any(token in q.lower() for token in ["trial", "studies", "clinicaltrials"]):
            terminal = re.search(r".*\b(?:for|in)\s+(.+?)(?:\?|$)", q, re.I)
            if terminal:
                text = terminal.group(1).strip(" .?")
                if text and not text.lower().startswith(("my uploaded", "uploaded")):
                    return text

        explicit_patterns = [
            r"(?:trials?|studies)\s+(?:for|of)\s+[^?]+?\s+in\s+(.+?)(?:\?|$)",
            r"(?:trials?|studies)\s+(?:involving|using|use|uses)\s+[^?]+?\s+(?:for|in)\s+(.+?)(?:\?|$)",
            r"(?:trials?|studies)\s+(?:for|in)\s+(.+?)(?:\?|$)",
            r"(?:clinicaltrials\.gov\s+studies)\s+(?:for|in)\s+(.+?)(?:\?|$)",
        ]
        for pattern in explicit_patterns:
            m = re.search(pattern, q, re.I)
            if m:
                text = m.group(1).strip(" .?")
                if text:
                    return text

        matches = list(re.finditer(r"\b(?:for|with|in)\s+(.+?)(?:\?|$)", q, re.I))
        for m in reversed(matches):
            text = m.group(1).strip(" .?")
            text = re.sub(r"^(?:recruiting\s+)?phase\s*[1-4iv]+\s+(?:trials?\s+)?", "", text, flags=re.I)
            text = re.sub(r"\s+(?:trials?|studies)\b.*$", "", text, flags=re.I)
            if text.lower().startswith(("drug ", "the drug ", "my uploaded", "uploaded")):
                continue
            return text or None
        return None

    @staticmethod
    def _drug_for_trial(q: str):
        if "uploaded" in q.lower():
            return None
        patterns = [
            r"(?:trials?|studies)\s+(?:involving|using|use|uses)\s+([A-Za-z0-9][A-Za-z0-9 ._-]{1,60}?)(?:\s+for\s+|\s+in\s+|\?|$)",
            r"(?:involving|involve|using|use|uses)\s+([A-Za-z0-9][A-Za-z0-9 ._-]{1,60}?)(?:\s+for\s+|\s+in\s+|\?|$)",
            r"trials?\s+(?:for|of)\s+([A-Za-z0-9][A-Za-z0-9 ._-]{1,60}?)(?:\s+for\s+|\s+in\s+|\?|$)",
        ]
        for pattern in patterns:
            m = re.search(pattern, q, re.I)
            if m:
                return m.group(1).strip(" .?")
        return None

    @staticmethod
    def _identity_drug(q: str):
        patterns = [
            r"\b(?:identify|resolve)\s+(?:drug\s+)?([A-Za-z0-9][A-Za-z0-9 ._-]{0,60}?)(?:\s+using\s+RxNorm|\s+with\s+RxNorm|\?|$)",
            r"\b(?:generic\s+(?:identity|name|ingredient)|canonical\s+(?:drug\s+)?identity|RxCUI(?:-linked)?\s+(?:generic\s+)?identity)\s+(?:of|for)\s+([A-Za-z0-9][A-Za-z0-9 ._-]{0,60}?)(?:\?|$)",
            r"\bcorresponds\s+to\s+([A-Za-z0-9][A-Za-z0-9 ._-]{0,60}?)(?:\?|$)",
            r"\bUsing\s+RxNorm,\s*identify\s+([A-Za-z0-9][A-Za-z0-9 ._-]{0,60}?)(?:\?|$)",
        ]
        for pattern in patterns:
            m = re.search(pattern, q, re.I)
            if m:
                return m.group(1).strip(" .?")
        return RuleBasedPlanner._drug_after_keyword(q, ["of", "for", "is"]) or RuleBasedPlanner._tail_entity(q)

    @staticmethod
    def _compound_name(q: str):
        patterns = [
            r"\b(?:for|of|about)\s+([A-Za-z0-9][A-Za-z0-9 ._-]{0,60}?)(?:\?|$)",
            r"\blook\s+up\s+(?:PubChem\s+compound\s+properties\s+for\s+)?([A-Za-z0-9][A-Za-z0-9 ._-]{0,60}?)(?:\s+in\s+PubChem|\?|$)",
        ]
        for pattern in patterns:
            m = re.search(pattern, q, re.I)
            if m:
                return m.group(1).strip(" .?")
        return RuleBasedPlanner._tail_entity(q)

    @staticmethod
    def _drug_after_keyword(q: str, keywords: list[str]):
        for keyword in keywords:
            m = re.search(rf"\b{re.escape(keyword)}\s+([A-Za-z0-9][A-Za-z0-9 ._-]{{0,60}}?)(?:\?|$)", q, re.I)
            if m:
                return re.sub(r"^(?:drug|brand)\s+", "", m.group(1).strip(" .?"), flags=re.I)
        return None

    @staticmethod
    def _tail_entity(q: str):
        text = q.strip(" .?")
        if not text:
            return None
        m = re.search(r"(?:of|for|about|is)\s+([^?]+)$", text, re.I)
        return m.group(1).strip(" .?") if m else text.split()[-1]

    @staticmethod
    def _tail_phrase(q: str):
        text = q.strip(" .?")
        m = re.search(r"(?:with|for|of)\s+(.+)$", text, re.I)
        return m.group(1).strip() if m else text
