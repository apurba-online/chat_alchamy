from __future__ import annotations

import re
from ..models import Entity, Operation, QueryPlan


class RuleBasedPlanner:
    STATUS_MAP = {"recruiting": "RECRUITING", "active, not recruiting": "ACTIVE_NOT_RECRUITING", "active not recruiting": "ACTIVE_NOT_RECRUITING", "completed": "COMPLETED", "not yet recruiting": "NOT_YET_RECRUITING", "terminated": "TERMINATED"}

    def plan(self, question: str) -> QueryPlan:
        q = " ".join(question.strip().split()); low = q.lower(); phase = self._phase(low); status = self._status(low); target = self._target(q)
        if target and ("fda" in low or "approved" in low) and ("trial" in low or phase or status):
            condition = self._condition(q)
            return QueryPlan(question=q, intent="cross_source", entities=[Entity(text=target, type="target")], filters={"phase": phase, "status": status, "condition": condition}, operations=[Operation(source="chembl", action="target_drugs", arguments={"target": target}), Operation(source="openfda", action="approval_records"), Operation(source="clinicaltrials", action="search_trials")], final_operation="intersection")
        if any(k in low for k in ["open targets", "opentargets", "associated genes", "associated targets", "genes associated"]):
            if "gene" in low and any(k in low for k in ["disease", "diseases", "associated with"]):
                gene = self._gene(q)
                if gene:
                    return QueryPlan(question=q, intent="gene_diseases", entities=[Entity(text=gene, type="gene")], operations=[Operation(source="opentargets", action="gene_diseases", arguments={"gene": gene})])
            disease = self._after(q, ["for", "with", "to", "of"]) or self._tail(q)
            return QueryPlan(question=q, intent="disease_targets", entities=[Entity(text=disease, type="disease")] if disease else [], operations=[Operation(source="opentargets", action="disease_targets", arguments={"disease": disease})])
        if "smiles" in low or "iupac" in low or "pubchem" in low or "chemical structure" in low:
            drug = self._after(q, ["for", "of", "about"]) or self._tail(q)
            return QueryPlan(question=q, intent="compound", entities=[Entity(text=drug, type="drug")] if drug else [], operations=[Operation(source="pubchem", action="compound", arguments={"name": drug})])
        if target and ("drug" in low or "target" in low or "inhibitor" in low):
            return QueryPlan(question=q, intent="target_drugs", entities=[Entity(text=target, type="target")], operations=[Operation(source="chembl", action="target_drugs", arguments={"target": target})])
        if "trial" in low or "clinicaltrials" in low or phase or status:
            drug = self._drug_for_trial(q); condition = self._condition(q); entities = [Entity(text=drug, type="drug")] if drug else []
            if condition: entities.append(Entity(text=condition, type="condition"))
            return QueryPlan(question=q, intent="trials", entities=entities, filters={"phase": phase, "status": status, "condition": condition}, operations=[Operation(source="rxnorm", action="resolve", arguments={"drug": drug}), Operation(source="clinicaltrials", action="search_trials", arguments={"drug": drug, "condition": condition, "phase": phase, "status": status})], final_operation="count" if any(x in low for x in ["how many", "count", "number of"]) else "list")
        if any(x in low for x in ["dailymed", "drug label", "label record", "spl record", "spl label"]):
            drug = self._after(q, ["for", "of", "about"]) or self._tail(q)
            return QueryPlan(question=q, intent="label", entities=[Entity(text=drug, type="drug")] if drug else [], operations=[Operation(source="rxnorm", action="resolve", arguments={"drug": drug}), Operation(source="dailymed", action="label_records", arguments={"drug": drug})])
        if "fda" in low or "approved" in low or "approval" in low:
            drug = self._after(q, ["for", "of", "is", "about"]) or self._tail(q)
            return QueryPlan(question=q, intent="approval", entities=[Entity(text=drug, type="drug")] if drug else [], operations=[Operation(source="rxnorm", action="resolve", arguments={"drug": drug}), Operation(source="openfda", action="approval_records", arguments={"drug": drug})])
        if any(x in low for x in ["generic identity", "generic name", "canonical", "rxcui", "identify"]):
            drug = self._after(q, ["of", "for", "is"]) or self._tail(q)
            return QueryPlan(question=q, intent="identity", entities=[Entity(text=drug, type="drug")] if drug else [], operations=[Operation(source="rxnorm", action="resolve", arguments={"drug": drug})], final_operation="identity")
        return QueryPlan(question=q, intent="unknown", operations=[], final_operation="abstain")

    @staticmethod
    def _phase(low: str):
        m = re.search(r"phase\s*([1-4]|i{1,3}|iv)\b", low, re.I)
        if not m: return None
        token = m.group(1).upper(); return {"I":"PHASE1","II":"PHASE2","III":"PHASE3","IV":"PHASE4"}.get(token, f"PHASE{token}")

    def _status(self, low: str):
        for text, canonical in sorted(self.STATUS_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            if text in low: return canonical
        return None

    @staticmethod
    def _target(q: str):
        for p in [r"targeting\s+([A-Za-z0-9_-]{2,20})", r"target\s+([A-Za-z0-9_-]{2,20})", r"([A-Z0-9-]{2,12})\s+inhibitors?"]:
            m = re.search(p, q)
            if m: return m.group(1).upper()
        return None

    @staticmethod
    def _gene(q: str):
        m = re.search(r"\b([A-Z][A-Z0-9-]{1,14})\b", q); return m.group(1) if m else None

    @staticmethod
    def _condition(q: str):
        m = re.search(r"\b(?:for|with|in)\s+(.+?)(?:\?|$)", q, re.I)
        if not m: return None
        text = m.group(1).strip(" .?"); text = re.sub(r"^(?:recruiting\s+)?phase\s*[1-4iv]+\s+(?:trials?\s+)?", "", text, flags=re.I); text = re.sub(r"\s+(?:trials?|studies)\b.*$", "", text, flags=re.I); return text or None

    @staticmethod
    def _drug_for_trial(q: str):
        for p in [r"(?:involving|involve|using|of)\s+([A-Za-z0-9][A-Za-z0-9 ._-]{1,60}?)(?:\s+for\s+|\s+in\s+|\?|$)", r"trials?\s+(?:for|of)\s+([A-Za-z0-9][A-Za-z0-9 ._-]{1,60}?)(?:\s+for\s+|\s+in\s+|\?|$)"]:
            m = re.search(p, q, re.I)
            if m: return m.group(1).strip(" .?")
        return None

    @staticmethod
    def _after(q: str, words: list[str]):
        for w in words:
            m = re.search(rf"\b{re.escape(w)}\s+([A-Za-z0-9][A-Za-z0-9 ._-]{{1,80}}?)(?:\?|$)", q, re.I)
            if m: return re.sub(r"^(?:drug|brand)\s+", "", m.group(1).strip(" .?"), flags=re.I)
        return None

    @staticmethod
    def _tail(q: str):
        text = q.strip(" .?")
        if not text: return None
        m = re.search(r"(?:of|for|about|is)\s+([^?]+)$", text, re.I); return m.group(1).strip(" .?") if m else text.split()[-1]
