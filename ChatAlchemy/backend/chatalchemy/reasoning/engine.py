from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from ..models import Claim, EvidenceItem, QueryResponse, SourceTrace
from ..planner.rule_based import RuleBasedPlanner
from ..sources.rxnorm import RxNormSource
from ..sources.dailymed import DailyMedSource
from ..sources.openfda import OpenFDASource
from ..sources.clinicaltrials import ClinicalTrialsSource
from ..sources.chembl import ChEMBLSource
from ..sources.opentargets import OpenTargetsSource
from ..sources.pubchem import PubChemSource
from ..evidence.conflict import assess_conflicts
from ..generation.verifier import verify_claims


@dataclass(frozen=True)
class EngineConfig:
    use_normalization: bool = True
    use_deterministic_joins: bool = True
    use_conflict_analysis: bool = True
    use_claim_verifier: bool = True


class ReasoningEngine:
    def __init__(self, sources: dict[str, Any] | None = None, config: EngineConfig | None = None):
        self.config = config or EngineConfig()
        self.planner = RuleBasedPlanner()
        self.sources = sources or {"rxnorm": RxNormSource(), "dailymed": DailyMedSource(), "openfda": OpenFDASource(), "clinicaltrials": ClinicalTrialsSource(), "chembl": ChEMBLSource(), "opentargets": OpenTargetsSource(), "pubchem": PubChemSource()}

    async def answer(self, question: str, max_results: int = 20, user_evidence: list[dict[str, Any]] | None = None) -> QueryResponse:
        plan = self.planner.plan(question)
        if plan.final_operation == "abstain":
            return QueryResponse(answer="I do not have a supported live-source plan for that question yet.", plan=plan, evidence=[], warnings=["No typed retrieval plan matched the question."], abstained=True)
        evidence: list[EvidenceItem] = []; traces: list[SourceTrace] = []; warnings: list[str] = []; canonical_drug: str | None = None; rxcui: str | None = None
        for op in plan.operations:
            source = self.sources[op.source]; started = time.perf_counter()
            try:
                if op.source == "rxnorm":
                    drug = op.arguments.get("drug")
                    if not drug: continue
                    items, latency = await source.resolve(drug, max_results=5)
                    if items and self.config.use_normalization:
                        canonical_drug = items[0].canonical_subject or str(items[0].value); rxcui = items[0].identifiers.get("rxcui")
                elif op.source == "dailymed":
                    drug = canonical_drug or op.arguments.get("drug"); items, latency = await source.labels(drug, rxcui=rxcui, max_results=max_results)
                elif op.source == "openfda":
                    drug = canonical_drug or op.arguments.get("drug")
                    if not drug and evidence: drug = str(evidence[-1].value)
                    items, latency = await source.approvals(drug, max_results=max_results)
                elif op.source == "clinicaltrials":
                    args = op.arguments | plan.filters; drug = canonical_drug or args.get("drug")
                    items, latency = await source.search(drug=drug, condition=args.get("condition"), phase=args.get("phase"), status=args.get("status"), max_results=max_results)
                elif op.source == "chembl": items, latency = await source.target_drugs(op.arguments.get("target"), max_results=max_results)
                elif op.source == "opentargets":
                    if op.action == "disease_targets": items, latency = await source.disease_targets(op.arguments.get("disease"), max_results=max_results)
                    else: items, latency = await source.gene_diseases(op.arguments.get("gene"), max_results=max_results)
                elif op.source == "pubchem": items, latency = await source.compound(op.arguments.get("name"))
                else: items, latency = [], (time.perf_counter() - started) * 1000
                evidence.extend(items); traces.append(SourceTrace(source=op.source, operation=op.action, success=True, latency_ms=latency, record_count=len(items)))
            except Exception as exc:
                elapsed = (time.perf_counter() - started) * 1000; traces.append(SourceTrace(source=op.source, operation=op.action, success=False, latency_ms=elapsed, error=str(exc))); warnings.append(f"{op.source} failed: {exc}")
        if user_evidence:
            for idx, item in enumerate(user_evidence):
                evidence.append(EvidenceItem(id=f"user-{idx}", source="user", subject=str(item.get("subject", "user evidence")), canonical_subject=item.get("canonical_subject"), predicate=str(item.get("predicate", "reported_fact")), value=item.get("value"), context=item.get("context", {}), raw=item))
        if plan.intent == "cross_source" and self.config.use_deterministic_joins:
            evidence = await self._cross_source_filter(evidence, plan, max_results, traces, warnings)
        conflicts = assess_conflicts(evidence) if self.config.use_conflict_analysis else []
        answer, claims = self._render(plan.intent, evidence, plan.final_operation)
        if self.config.use_claim_verifier: claims, rate = verify_claims(claims, evidence)
        else: rate = 0.0
        if claims and rate < 1.0: warnings.append("One or more generated claims lacked valid evidence support and should not be treated as verified.")
        return QueryResponse(answer=answer, plan=plan, evidence=evidence, conflicts=conflicts, claims=claims, supported_claim_rate=rate, traces=traces, warnings=warnings, abstained=not evidence and bool(warnings))

    async def _cross_source_filter(self, evidence, plan, max_results, traces, warnings):
        candidates = [e for e in evidence if e.source == "chembl" and e.predicate == "target_drug"]
        if not candidates: return evidence
        async def check(candidate):
            name = str(candidate.value); approvals = []; trials = []
            try: approvals, la = await self.sources["openfda"].approvals(name, max_results=5)
            except Exception as exc: la = 0; warnings.append(f"openfda failed for {name}: {exc}")
            try: trials, lt = await self.sources["clinicaltrials"].search(drug=name, condition=plan.filters.get("condition"), phase=plan.filters.get("phase"), status=plan.filters.get("status"), max_results=5)
            except Exception as exc: lt = 0; warnings.append(f"clinicaltrials failed for {name}: {exc}")
            traces.append(SourceTrace(source="openfda", operation="approval_records", success=bool(approvals), latency_ms=la, record_count=len(approvals))); traces.append(SourceTrace(source="clinicaltrials", operation="search_trials", success=bool(trials), latency_ms=lt, record_count=len(trials)))
            return candidate, approvals, trials
        checked = await asyncio.gather(*(check(c) for c in candidates[:max_results])); kept = []
        for candidate, approvals, trials in checked:
            if approvals and trials: kept.extend([candidate, *approvals, *trials])
        return kept

    @staticmethod
    def _render(intent: str, evidence: list[EvidenceItem], final_operation: str):
        if not evidence: return "No supporting records were returned by the live sources for this query.", []
        if intent == "identity":
            e = evidence[0]; text = f"The canonical identity returned by RxNorm is {e.value} (RxCUI {e.identifiers.get('rxcui','N/A')})."; return text, [Claim(text=text, support_evidence_ids=[e.id])]
        relevant = evidence
        if intent == "label": relevant = [e for e in evidence if e.predicate == "label_record"]
        elif intent == "approval": relevant = [e for e in evidence if e.predicate == "fda_application_record"]
        elif intent == "trials": relevant = [e for e in evidence if e.predicate == "clinical_trial"]
        elif intent == "target_drugs": relevant = [e for e in evidence if e.predicate == "target_drug"]
        elif intent == "disease_targets": relevant = [e for e in evidence if e.predicate == "disease_target"]
        elif intent == "gene_diseases": relevant = [e for e in evidence if e.predicate == "gene_disease"]
        elif intent == "compound": relevant = [e for e in evidence if e.predicate == "compound_properties"]
        elif intent == "cross_source":
            names = []
            for e in evidence:
                if e.predicate == "target_drug" and str(e.value) not in names: names.append(str(e.value))
            text = f"{len(names)} candidate(s) satisfied the requested live-source constraints: {', '.join(names) if names else 'none'}."; ids = [e.id for e in evidence if e.predicate == "target_drug"]
            return text, [Claim(text=text, support_evidence_ids=ids)] if ids else []
        if final_operation == "count":
            text = f"The live query returned {len(relevant)} matching record(s)."; return text, [Claim(text=text, support_evidence_ids=[e.id for e in relevant])]
        vals = [str(e.value) for e in relevant]; text = f"The live sources returned {len(relevant)} matching record(s): " + "; ".join(vals[:20]); return text, [Claim(text=text, support_evidence_ids=[e.id for e in relevant])]
