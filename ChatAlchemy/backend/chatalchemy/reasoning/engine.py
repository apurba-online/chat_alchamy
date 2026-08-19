from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Any

import httpx

from ..evidence import ConflictEngine
from ..generation import ClaimVerifier
from ..models import Claim, EvidenceItem, QueryPlan, QueryResponse, SourceTrace
from ..planner import RuleBasedPlanner
from ..sources import ChEMBLSource, ClinicalTrialsSource, DailyMedSource, OpenFDASource, RxNormSource


class ChatAlchemyEngine:
    def __init__(self, *, client: httpx.AsyncClient | None = None, planner: RuleBasedPlanner | None = None, rxnorm: RxNormSource | None = None, openfda: OpenFDASource | None = None, clinicaltrials: ClinicalTrialsSource | None = None, chembl: ChEMBLSource | None = None, dailymed: DailyMedSource | None = None):
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=10.0), follow_redirects=True)
        self.planner = planner or RuleBasedPlanner()
        self.rxnorm = rxnorm or RxNormSource(self.client, min_interval=0.05)
        self.openfda = openfda or OpenFDASource(self.client, min_interval=0.25)
        self.clinicaltrials = clinicaltrials or ClinicalTrialsSource(self.client, min_interval=0.10)
        self.chembl = chembl or ChEMBLSource(self.client, min_interval=0.20)
        self.dailymed = dailymed or DailyMedSource(self.client, min_interval=0.20)
        self.conflicts = ConflictEngine()
        self.verifier = ClaimVerifier()

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def answer(self, question: str, *, max_results: int = 20) -> QueryResponse:
        plan = self.planner.plan(question)
        evidence: list[EvidenceItem] = []
        traces: list[SourceTrace] = []
        warnings: list[str] = []
        if plan.intent == "unknown":
            return self._finalize(plan, "I could not map that question to a supported live pharmaceutical query. Try asking about drug identity, DailyMed labels, FDA records, clinical trials, or a molecular target.", [], [], [], ["No supported typed query plan was produced."])

        if plan.intent == "identity":
            drug = self._entity_text(plan, "drug")
            resolved, ev, trace = await self._call("RxNorm", "resolve", self.rxnorm.resolve(drug))
            traces.append(trace); evidence.extend(ev or [])
            if resolved:
                plan.entities = [resolved]
                answer = f"RxNorm resolved {drug} to {resolved.canonical_name} (RxCUI {resolved.ids.get('rxcui')})."
                claims = [Claim(text=answer, support_ids=[evidence[0].id])]
            else:
                answer = f"RxNorm did not return an active match for {drug}."; claims = []
            return self._finalize(plan, answer, claims, evidence, traces, warnings)

        if plan.intent == "label":
            drug = self._entity_text(plan, "drug")
            resolved, ev, trace = await self._call("RxNorm", "resolve", self.rxnorm.resolve(drug))
            traces.append(trace); evidence.extend(ev or [])
            name = resolved.canonical_name if resolved and resolved.canonical_name else drug
            rxcui = resolved.ids.get("rxcui") if resolved else None
            if resolved: plan.entities = [resolved]
            labels, _, trace = await self._call("DailyMed", "label_records", self.dailymed.label_records(drug_name=name, rxcui=rxcui, limit=max_results))
            traces.append(trace); evidence.extend(labels or [])
            label_ev = [e for e in evidence if e.predicate == "dailymed_label_record"]
            if label_ev:
                ids = [str(e.value) for e in label_ev[:10]]
                answer = f"The live DailyMed query returned {len(label_ev)} SPL label record(s) for {name}. Set IDs: {', '.join(ids)}."
                claims = [Claim(text=answer, support_ids=[e.id for e in label_ev])]
            else:
                answer = f"The live DailyMed query returned no SPL label records for {name}."; claims = []
            return self._finalize(plan, answer, claims, evidence, traces, warnings)

        if plan.intent == "approval":
            drug = self._entity_text(plan, "drug")
            resolved, ev, trace = await self._call("RxNorm", "resolve", self.rxnorm.resolve(drug))
            traces.append(trace); evidence.extend(ev or [])
            names = [drug]
            if resolved:
                plan.entities = [resolved]
                if resolved.canonical_name and resolved.canonical_name.lower() != drug.lower(): names.insert(0, resolved.canonical_name)
            approvals, _, trace = await self._call("Drugs@FDA/openFDA", "approval_records", self.openfda.approval_records(names, limit=max_results))
            traces.append(trace); evidence.extend(approvals or [])
            app_evidence = [e for e in evidence if e.predicate == "fda_approval_record"]
            if app_evidence:
                apps = [str(e.value) for e in app_evidence[:10]]
                answer = f"I found {len(app_evidence)} Drugs@FDA application record(s) for {names[0]}. Applications: {', '.join(apps)}."
                claims = [Claim(text=answer, support_ids=[e.id for e in app_evidence])]
            else:
                answer = f"No matching Drugs@FDA application record was retrieved for {names[0]} in this live query."; claims = []
                warnings.append("No record retrieved is not proof that no FDA record exists; name/identifier coverage can differ across sources.")
            return self._finalize(plan, answer, claims, evidence, traces, warnings)

        if plan.intent == "trials":
            drug = self._entity_text(plan, "drug")
            condition = self._entity_text(plan, "condition", required=False)
            resolved, ev, trace = await self._call("RxNorm", "resolve", self.rxnorm.resolve(drug))
            traces.append(trace); evidence.extend(ev or [])
            intervention = resolved.canonical_name if resolved and resolved.canonical_name else drug
            if resolved:
                for i, e in enumerate(plan.entities):
                    if e.type == "drug": plan.entities[i] = resolved; break
            trials, _, trace = await self._call("ClinicalTrials.gov", "search_trials", self.clinicaltrials.search_trials(intervention=intervention, condition=condition, phase=plan.filters.get("phase"), status=plan.filters.get("status"), limit=min(max_results * 5, 100)))
            traces.append(trace); evidence.extend(trials or [])
            trial_ev = [e for e in evidence if e.predicate == "clinical_trial"]
            phase_text = plan.filters.get("phase") or "any phase"; status_text = plan.filters.get("status") or "any status"
            if trial_ev:
                ids = [str(e.value) for e in trial_ev[:10]]
                answer = f"The live ClinicalTrials.gov query returned {len(trial_ev)} matching trial(s) for {intervention} ({phase_text}, {status_text})." if plan.final_operation == "count" else f"The live ClinicalTrials.gov query returned {len(trial_ev)} matching trial(s) for {intervention}: {', '.join(ids)}."
                claims = [Claim(text=answer, support_ids=[e.id for e in trial_ev])]
            else:
                answer = f"The live ClinicalTrials.gov query returned no matching trials for {intervention} under the requested filters."; claims = []
            return self._finalize(plan, answer, claims, evidence, traces, warnings)

        if plan.intent == "target_drugs":
            target = self._entity_text(plan, "target")
            items, _, trace = await self._call("ChEMBL", "target_drugs", self.chembl.target_drugs(target, limit=max_results))
            traces.append(trace); evidence.extend(items or [])
            if items:
                names = self._unique([e.subject for e in items])
                answer = f"ChEMBL returned {len(names)} drug/molecule candidate(s) with mechanism evidence linked to {target}: {', '.join(names[:10])}."
                claims = [Claim(text=answer, support_ids=[e.id for e in items])]
            else:
                answer = f"No ChEMBL mechanism records were retrieved for target {target}."; claims = []
            return self._finalize(plan, answer, claims, evidence, traces, warnings)

        if plan.intent == "cross_source":
            target = self._entity_text(plan, "target"); condition = self._entity_text(plan, "condition", required=False)
            target_ev, _, trace = await self._call("ChEMBL", "target_drugs", self.chembl.target_drugs(target, limit=min(max_results, 15)))
            traces.append(trace); evidence.extend(target_ev or [])
            candidates = self._unique([e.subject for e in target_ev or []])
            if not candidates:
                warnings.append("No ChEMBL target candidates were available, so the cross-source intersection could not proceed.")
                return self._finalize(plan, f"No ChEMBL target-linked candidates were retrieved for {target}.", [], evidence, traces, warnings)
            async def check_candidate(name: str):
                approvals_task = self._call("Drugs@FDA/openFDA", "approval_records", self.openfda.approval_records([name], limit=10))
                trials_task = self._call("ClinicalTrials.gov", "search_trials", self.clinicaltrials.search_trials(intervention=name, condition=condition, phase=plan.filters.get("phase"), status=plan.filters.get("status"), limit=100))
                return name, await asyncio.gather(approvals_task, trials_task)
            results = await asyncio.gather(*(check_candidate(name) for name in candidates))
            qualified: list[str] = []; support: dict[str, list[str]] = defaultdict(list)
            for name, pair in results:
                (approvals, _, t1), (trials, _, t2) = pair; traces.extend([t1, t2]); approvals = approvals or []; trials = trials or []; evidence.extend(approvals); evidence.extend(trials)
                if approvals and trials:
                    qualified.append(name); support[name].extend([e.id for e in approvals + trials]); support[name].extend([e.id for e in target_ev if e.subject == name])
            if qualified:
                answer = f"Using live ChEMBL, Drugs@FDA/openFDA, and ClinicalTrials.gov evidence, {len(qualified)} candidate(s) satisfied all requested constraints: {', '.join(qualified[:10])}."
                claims = [Claim(text=answer, support_ids=self._unique([sid for n in qualified for sid in support[n]]))]
            else:
                answer = "No candidate satisfied all requested constraints in this live query across ChEMBL, Drugs@FDA/openFDA, and ClinicalTrials.gov."; claims = []
            return self._finalize(plan, answer, claims, evidence, traces, warnings)
        return self._finalize(plan, "No supported execution path was produced.", [], evidence, traces, ["Execution path missing."])

    async def _call(self, source: str, operation: str, awaitable):
        start = time.perf_counter()
        try:
            result = await awaitable; latency = (time.perf_counter() - start) * 1000
            if isinstance(result, tuple):
                count = len(result[1]) if len(result) > 1 and isinstance(result[1], list) else 1
                return result[0], result[1], SourceTrace(source=source, operation=operation, ok=True, latency_ms=latency, result_count=count)
            count = len(result) if isinstance(result, list) else int(result is not None)
            return result, None, SourceTrace(source=source, operation=operation, ok=True, latency_ms=latency, result_count=count)
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            return None, None, SourceTrace(source=source, operation=operation, ok=False, latency_ms=latency, result_count=0, error=str(exc))

    def _finalize(self, plan: QueryPlan, answer: str, claims: list[Claim], evidence: list[EvidenceItem], traces: list[SourceTrace], warnings: list[str]) -> QueryResponse:
        claims = self.verifier.verify(claims, evidence); conflicts = self.conflicts.assess(evidence)
        if any(not t.ok for t in traces): warnings = warnings + ["One or more live sources failed. The answer is limited to successfully retrieved evidence."]
        return QueryResponse(answer=answer, plan=plan, claims=claims, evidence=evidence, conflicts=conflicts, traces=traces, supported_claim_rate=self.verifier.supported_rate(claims), warnings=self._unique(warnings))

    @staticmethod
    def _entity_text(plan: QueryPlan, kind: str, required: bool = True) -> str | None:
        for entity in plan.entities:
            if entity.type == kind: return entity.text
        if required: raise ValueError(f"Planner did not identify required {kind} entity")
        return None

    @staticmethod
    def _unique(values: list[Any]) -> list[Any]:
        out = []; seen = set()
        for value in values:
            marker = str(value)
            if marker not in seen: seen.add(marker); out.append(value)
        return out
