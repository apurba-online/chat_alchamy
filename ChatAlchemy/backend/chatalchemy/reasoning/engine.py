from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from ..evidence import analyze_conflicts
from ..generation import verify_claims
from ..llm import LLMClient
from ..models import Claim, EvidenceItem, QueryResponse, SourceTrace, TablePayload
from ..planner import RuleBasedPlanner
from ..sources import (
    ChEMBLSource,
    ClinicalTrialsSource,
    DailyMedSource,
    OpenFDASource,
    OpenTargetsSource,
    PubChemSource,
    RxNormSource,
)


@dataclass
class NormalizedDrug:
    original: str
    canonical: str
    evidence: list[EvidenceItem]
    trace: SourceTrace | None


class ChatAlchemyEngine:
    def __init__(
        self,
        *,
        llm: LLMClient | None = None,
        sources: dict[str, Any] | None = None,
        use_conflict: bool = True,
        use_verifier: bool = True,
        use_normalization: bool = True,
        use_deterministic_join: bool = True,
    ):
        self.planner = RuleBasedPlanner()
        self.use_conflict = use_conflict
        self.use_verifier = use_verifier
        self.use_normalization = use_normalization
        self.use_deterministic_join = use_deterministic_join
        self.llm = llm or LLMClient()
        self.sources = sources or {
            "rxnorm": RxNormSource(),
            "dailymed": DailyMedSource(),
            "openfda": OpenFDASource(),
            "clinicaltrials": ClinicalTrialsSource(),
            "chembl": ChEMBLSource(),
            "opentargets": OpenTargetsSource(),
            "pubchem": PubChemSource(),
        }
        self._normalization_cache: dict[str, NormalizedDrug] = {}

    async def close(self):
        await asyncio.gather(*(source.close() for source in self.sources.values()), return_exceptions=True)
        await self.llm.close()

    def _finish(
        self,
        answer: str,
        plan,
        claims: list[Claim],
        evidence: list[EvidenceItem],
        traces: list[SourceTrace],
        warnings: list[str],
        table: TablePayload | None = None,
    ) -> QueryResponse:
        conflicts = analyze_conflicts(evidence) if self.use_conflict else []
        if self.use_verifier:
            claims, supported = verify_claims(claims, evidence)
        else:
            supported = 1.0 if not claims else sum(bool(c.support_ids) for c in claims) / len(claims)
        return QueryResponse(
            answer=answer,
            plan=plan,
            claims=claims,
            evidence=evidence,
            conflicts=conflicts,
            traces=traces,
            supported_claim_rate=supported,
            warnings=list(dict.fromkeys(warnings)),
            table=table,
        )

    async def _normalize_drug(self, name: str) -> NormalizedDrug:
        key = " ".join(name.lower().split())
        if key in self._normalization_cache:
            return self._normalization_cache[key]
        if not self.use_normalization or "rxnorm" not in self.sources:
            result = NormalizedDrug(original=name, canonical=name, evidence=[], trace=None)
            self._normalization_cache[key] = result
            return result
        evidence, trace = await self.sources["rxnorm"].traced("resolve", self.sources["rxnorm"].resolve(name))
        canonical = str(evidence[0].value) if evidence else name
        result = NormalizedDrug(original=name, canonical=canonical, evidence=evidence, trace=trace)
        self._normalization_cache[key] = result
        return result

    async def _normalize_many(self, names: list[str]) -> list[NormalizedDrug]:
        unique = list(dict.fromkeys(name.strip() for name in names if name.strip()))
        return await asyncio.gather(*(self._normalize_drug(name) for name in unique)) if unique else []

    async def answer(
        self,
        question: str,
        max_results: int = 20,
        conversation: list[dict[str, str]] | None = None,
        user_evidence: list[dict[str, Any]] | None = None,
    ) -> QueryResponse:
        plan = self.planner.plan(question)
        evidence: list[EvidenceItem] = []
        traces: list[SourceTrace] = []
        warnings: list[str] = []
        claims: list[Claim] = []
        table: TablePayload | None = None

        if user_evidence:
            for item in user_evidence:
                evidence.append(
                    EvidenceItem.build(
                        subject=str(item.get("subject") or "user data"),
                        predicate=str(item.get("predicate") or "user_evidence"),
                        value=item.get("value"),
                        qualifiers=item.get("qualifiers") or {},
                        source="UserEvidence",
                        source_record_id=str(item.get("id")) if item.get("id") else None,
                        evidence_type="user",
                    )
                )

        candidates = list(
            dict.fromkeys(
                str(item.get("subject") or item.get("value") or "").strip()
                for item in (user_evidence or [])
                if item.get("predicate") == "candidate_drug"
                and str(item.get("subject") or item.get("value") or "").strip()
            )
        )
        if candidates and plan.intent in {"approval", "trials", "target_drugs"}:
            answer, extra_evidence, extra_traces, claims, table, extra_warnings = await self._user_candidate_join(
                plan, candidates, max_results
            )
            evidence.extend(extra_evidence)
            traces.extend(extra_traces)
            warnings.extend(extra_warnings)
            return self._finish(answer, plan, claims, evidence, traces, warnings, table)

        if plan.intent == "general":
            answer = await self._general_answer(question, conversation or [], user_evidence or [])
            return QueryResponse(
                answer=answer,
                plan=plan,
                claims=[],
                evidence=evidence,
                conflicts=[],
                traces=[],
                supported_claim_rate=1.0,
                warnings=[],
            )

        try:
            if plan.intent == "identity":
                drug = self._first_entity(plan, "drug")
                result, trace = await self.sources["rxnorm"].traced("resolve", self.sources["rxnorm"].resolve(drug))
                traces.append(trace)
                evidence.extend(result)
                if result:
                    item = result[0]
                    answer = f"According to live RxNorm data, **{drug}** resolves to **{item.value}**"
                    if item.qualifiers.get("rxcui"):
                        answer += f" (RxCUI {item.qualifiers['rxcui']})."
                    else:
                        answer += "."
                    claims = [Claim(text=answer, support_ids=[item.id])]
                else:
                    answer = f"I could not resolve **{drug}** in the live RxNorm service."
                    warnings.append("No live identity evidence was returned.")

            elif plan.intent == "label":
                drug = self._first_entity(plan, "drug")
                rows, trace = await self.sources["dailymed"].traced(
                    "label_records", self.sources["dailymed"].label_records(drug, max_results=max_results)
                )
                traces.append(trace)
                evidence.extend(rows)
                if rows:
                    answer = f"DailyMed returned **{len(rows)} label record(s)** for **{drug}**."
                    claims = [Claim(text=answer, support_ids=[item.id for item in rows])]
                    table = TablePayload(
                        headers=["Set ID", "Label", "Published", "SPL Version"],
                        rows=[
                            [
                                item.source_record_id,
                                item.value,
                                item.qualifiers.get("published_date"),
                                item.qualifiers.get("spl_version"),
                            ]
                            for item in rows
                        ],
                        caption=f"DailyMed label records for {drug}",
                    )
                else:
                    answer = f"No DailyMed label records were returned for **{drug}**."

            elif plan.intent == "approval":
                drug = self._first_entity(plan, "drug")
                rows, trace = await self.sources["openfda"].traced(
                    "approval_records", self.sources["openfda"].approval_records(drug, max_results=max_results)
                )
                traces.append(trace)
                evidence.extend(rows)
                if rows:
                    answer = f"Drugs@FDA/openFDA returned **{len(rows)} application record(s)** associated with **{drug}**."
                    claims = [Claim(text=answer, support_ids=[item.id for item in rows])]
                    table = TablePayload(
                        headers=["Application", "Sponsor", "Brand names"],
                        rows=[
                            [
                                item.value,
                                item.qualifiers.get("sponsor"),
                                ", ".join(item.qualifiers.get("brand_names") or []),
                            ]
                            for item in rows
                        ],
                        caption=f"FDA application records for {drug}",
                    )
                else:
                    answer = f"No Drugs@FDA/openFDA application records were returned for **{drug}**."

            elif plan.intent == "trials":
                drug = self._first_entity(plan, "drug", True)
                condition = plan.filters.get("condition")
                phase = plan.filters.get("phase")
                status = plan.filters.get("status")
                rows, trace = await self.sources["clinicaltrials"].traced(
                    "search_trials",
                    self.sources["clinicaltrials"].search_trials(drug, condition, phase, status, max_results),
                )
                traces.append(trace)
                evidence.extend(rows)
                label = " ".join(
                    piece
                    for piece in [
                        status.replace("_", " ").title() if status else None,
                        phase.replace("PHASE", "Phase ") if phase else None,
                        "trials",
                        f"involving {drug}" if drug else None,
                        f"for {condition}" if condition else None,
                    ]
                    if piece
                )
                answer = f"ClinicalTrials.gov returned **{len(rows)} {label.strip()}**."
                if rows:
                    claims = [Claim(text=answer, support_ids=[item.id for item in rows])]
                    table = TablePayload(
                        headers=["NCT ID", "Title", "Phase", "Status", "Conditions"],
                        rows=[
                            [
                                item.value,
                                item.qualifiers.get("title"),
                                ", ".join(item.qualifiers.get("phases") or []),
                                item.qualifiers.get("status"),
                                ", ".join(item.qualifiers.get("conditions") or []),
                            ]
                            for item in rows
                        ],
                        caption="Live ClinicalTrials.gov results",
                    )

            elif plan.intent == "target_drugs":
                target = self._first_entity(plan, "target")
                rows, trace = await self.sources["chembl"].traced(
                    "target_drugs", self.sources["chembl"].target_drugs(target, max_results=max_results)
                )
                traces.append(trace)
                evidence.extend(rows)
                names = [str(item.value) for item in rows]
                answer = f"ChEMBL returned **{len(names)} drug candidate(s)** with mechanisms linked to **{target}**."
                if names:
                    answer += " Examples: " + ", ".join(names[:10]) + "."
                    claims = [Claim(text=answer, support_ids=[item.id for item in rows])]
                    table = TablePayload(
                        headers=["Drug", "ChEMBL ID", "Mechanism", "Action"],
                        rows=[
                            [
                                item.value,
                                item.qualifiers.get("molecule_chembl_id"),
                                item.qualifiers.get("mechanism"),
                                item.qualifiers.get("action_type"),
                            ]
                            for item in rows
                        ],
                        caption=f"ChEMBL candidates targeting {target}",
                    )

            elif plan.intent == "gene":
                gene = self._first_entity(plan, "gene")
                rows, trace = await self.sources["opentargets"].traced(
                    "gene_details", self.sources["opentargets"].gene_details(gene, max_results=max_results)
                )
                traces.append(trace)
                evidence.extend(rows)
                identity = next((item for item in rows if item.predicate == "gene_identity"), None)
                associations = [item for item in rows if item.predicate == "gene_disease_association"]
                known = [item for item in rows if item.predicate == "known_drug"]
                if identity:
                    answer = (
                        f"Open Targets resolved **{gene}** as **{identity.value}** and returned "
                        f"**{len(associations)} disease association(s)** and **{len(known)} clinical drug candidate record(s)** in this query."
                    )
                    claims = [Claim(text=answer, support_ids=[item.id for item in rows])]
                    table = TablePayload(
                        headers=["Type", "Value", "Score / Stage", "Identifier"],
                        rows=[
                            ["Disease", item.value, item.qualifiers.get("score"), item.qualifiers.get("efo_id")]
                            for item in associations
                        ]
                        + [
                            [
                                "Drug",
                                item.value,
                                item.qualifiers.get("max_clinical_stage"),
                                item.qualifiers.get("chembl_id"),
                            ]
                            for item in known
                        ],
                        caption=f"Open Targets evidence for {gene}",
                    )
                else:
                    answer = f"Open Targets returned no target record for **{gene}**."

            elif plan.intent == "disease":
                disease = self._first_entity(plan, "condition")
                rows, trace = await self.sources["opentargets"].traced(
                    "disease_genes", self.sources["opentargets"].disease_genes(disease, max_results=max_results)
                )
                traces.append(trace)
                evidence.extend(rows)
                answer = f"Open Targets returned **{len(rows)} associated target gene(s)** for **{disease}**."
                if rows:
                    claims = [Claim(text=answer, support_ids=[item.id for item in rows])]
                    table = TablePayload(
                        headers=["Gene", "Gene name", "Ensembl ID", "Association score"],
                        rows=[
                            [
                                item.value,
                                item.qualifiers.get("gene_name"),
                                item.qualifiers.get("ensembl_id"),
                                item.qualifiers.get("score"),
                            ]
                            for item in rows
                        ],
                        caption=f"Open Targets genes associated with {disease}",
                    )

            elif plan.intent == "compound":
                name = self._first_entity(plan, "compound")
                rows, trace = await self.sources["pubchem"].traced("compound", self.sources["pubchem"].compound(name))
                traces.append(trace)
                evidence.extend(rows)
                if rows:
                    props = rows[0].value
                    answer = (
                        f"PubChem reports CID **{props.get('cid')}** for **{name}**, with canonical SMILES "
                        f"`{props.get('canonical_smiles')}` and IUPAC name **{props.get('iupac_name')}**."
                    )
                    claims = [Claim(text=answer, support_ids=[rows[0].id])]
                    table = TablePayload(
                        headers=["CID", "Canonical SMILES", "IUPAC name"],
                        rows=[[props.get("cid"), props.get("canonical_smiles"), props.get("iupac_name")]],
                        caption=f"PubChem properties for {name}",
                    )
                else:
                    answer = f"PubChem returned no compound properties for **{name}**."

            elif plan.intent == "cross_source":
                answer, extra_evidence, extra_traces, claims, table, extra_warnings = await self._cross_source(
                    plan, max_results
                )
                evidence.extend(extra_evidence)
                traces.extend(extra_traces)
                warnings.extend(extra_warnings)
            else:
                answer = "I could not map that question to a supported evidence operation."
                warnings.append("Planner abstained.")
        except Exception as exc:
            answer = "I could not complete the live biomedical query. I will not substitute an unsupported biomedical fact."
            warnings.append(str(exc))

        for trace in traces:
            if not trace.ok:
                warnings.append(f"{trace.source} failed during {trace.operation}: {trace.error}")
        return self._finish(answer, plan, claims, evidence, traces, warnings, table)

    async def _user_candidate_join(self, plan, candidates: list[str], max_results: int):
        evidence: list[EvidenceItem] = []
        traces: list[SourceTrace] = []
        warnings: list[str] = []
        rows: list[list[Any]] = []
        support_ids: list[str] = []
        accepted: list[str] = []
        normalized = await self._normalize_many(candidates)
        for item in normalized:
            evidence.extend(item.evidence)
            if item.trace:
                traces.append(item.trace)

        if plan.intent == "approval":
            async def check(item: NormalizedDrug):
                result = await self.sources["openfda"].traced(
                    "approval_records", self.sources["openfda"].approval_records(item.canonical, 3)
                )
                return item, result

            for item, (apps, trace) in await asyncio.gather(*(check(item) for item in normalized[:40])):
                traces.append(trace)
                evidence.extend(apps)
                if apps:
                    accepted.append(item.original)
                    support_ids.extend([e.id for e in item.evidence] + [e.id for e in apps])
                    rows.append([item.original, item.canonical, ", ".join(str(e.value) for e in apps)])
            answer = (
                f"From the uploaded candidate list, **{len(accepted)} drug(s)** had live Drugs@FDA/openFDA application records: "
                + (", ".join(accepted) if accepted else "none")
                + "."
            )
            table = TablePayload(
                headers=["Uploaded drug", "Canonical identity", "FDA application record(s)"],
                rows=rows,
                caption="Uploaded data × live FDA records",
            ) if rows else None

        elif plan.intent == "trials":
            condition = plan.filters.get("condition")
            phase = plan.filters.get("phase")
            status = plan.filters.get("status")

            async def check(item: NormalizedDrug):
                result = await self.sources["clinicaltrials"].traced(
                    "search_trials",
                    self.sources["clinicaltrials"].search_trials(item.canonical, condition, phase, status, 10),
                )
                return item, result

            for item, (trials, trace) in await asyncio.gather(*(check(item) for item in normalized[:30])):
                traces.append(trace)
                evidence.extend(trials)
                if trials:
                    accepted.append(item.original)
                    support_ids.extend([e.id for e in item.evidence] + [e.id for e in trials])
                    rows.append([item.original, item.canonical, ", ".join(str(e.value) for e in trials)])
            answer = (
                f"From the uploaded candidate list, **{len(accepted)} drug(s)** had matching live ClinicalTrials.gov records: "
                + (", ".join(accepted) if accepted else "none")
                + "."
            )
            table = TablePayload(
                headers=["Uploaded drug", "Canonical identity", "Matching trial(s)"],
                rows=rows,
                caption="Uploaded data × live ClinicalTrials.gov",
            ) if rows else None

        else:
            target = self._first_entity(plan, "target")
            drugs, trace = await self.sources["chembl"].traced(
                "target_drugs", self.sources["chembl"].target_drugs(target, max_results=50)
            )
            traces.append(trace)
            evidence.extend(drugs)
            live_names = [str(item.value) for item in drugs]
            live_normalized = await self._normalize_many(live_names)
            for item in live_normalized:
                evidence.extend(item.evidence)
                if item.trace:
                    traces.append(item.trace)
            live_by_canonical: dict[str, EvidenceItem] = {}
            source_by_name = {str(item.value).lower(): item for item in drugs}
            for item in live_normalized:
                source_item = source_by_name.get(item.original.lower())
                if source_item:
                    live_by_canonical[item.canonical.lower()] = source_item
            for item in normalized:
                hit = live_by_canonical.get(item.canonical.lower())
                if hit:
                    accepted.append(item.original)
                    support_ids.extend([e.id for e in item.evidence] + [hit.id])
                    rows.append([item.original, item.canonical, hit.qualifiers.get("molecule_chembl_id"), hit.qualifiers.get("mechanism")])
            answer = (
                f"From the uploaded candidate list, **{len(accepted)} drug(s)** matched live ChEMBL mechanisms for **{target}**: "
                + (", ".join(accepted) if accepted else "none")
                + "."
            )
            table = TablePayload(
                headers=["Uploaded drug", "Canonical identity", "ChEMBL ID", "Mechanism"],
                rows=rows,
                caption=f"Uploaded data × ChEMBL target {target}",
            ) if rows else None

        claims = [Claim(text=answer, support_ids=list(dict.fromkeys(support_ids)))] if support_ids else []
        return answer, evidence, traces, claims, table, warnings

    async def _cross_source(self, plan, max_results: int):
        target = self._first_entity(plan, "target")
        condition = plan.filters.get("condition")
        phase = plan.filters.get("phase")
        status = plan.filters.get("status")
        evidence: list[EvidenceItem] = []
        traces: list[SourceTrace] = []
        warnings: list[str] = []

        candidates, trace = await self.sources["chembl"].traced(
            "target_drugs", self.sources["chembl"].target_drugs(target, max_results=min(max_results, 15))
        )
        traces.append(trace)
        evidence.extend(candidates)
        normalized = await self._normalize_many([str(item.value) for item in candidates])
        for item in normalized:
            evidence.extend(item.evidence)
            if item.trace:
                traces.append(item.trace)

        async def check(item: NormalizedDrug):
            (apps, app_trace), (trials, trial_trace) = await asyncio.gather(
                self.sources["openfda"].traced(
                    "approval_records", self.sources["openfda"].approval_records(item.canonical, max_results=3)
                ),
                self.sources["clinicaltrials"].traced(
                    "search_trials",
                    self.sources["clinicaltrials"].search_trials(item.canonical, condition, phase, status, 10),
                ),
            )
            return item, apps, trials, app_trace, trial_trace

        accepted: list[str] = []
        support_ids: list[str] = []
        rows: list[list[Any]] = []
        checked = await asyncio.gather(*(check(item) for item in normalized[:10])) if normalized else []
        for item, apps, trials, app_trace, trial_trace in checked:
            traces.extend([app_trace, trial_trace])
            evidence.extend(apps)
            evidence.extend(trials)
            qualifies = bool(apps and trials) if self.use_deterministic_join else bool(apps or trials)
            if qualifies:
                accepted.append(item.original)
                support_ids.extend([e.id for e in item.evidence] + [e.id for e in apps] + [e.id for e in trials])
                rows.append(
                    [
                        item.original,
                        item.canonical,
                        ", ".join(str(e.value) for e in apps),
                        ", ".join(str(e.value) for e in trials),
                    ]
                )

        if self.use_deterministic_join:
            answer = (
                f"Using live ChEMBL, Drugs@FDA/openFDA, and ClinicalTrials.gov evidence, **{len(accepted)} candidate(s)** "
                "satisfied all requested constraints"
                + ((": " + ", ".join(accepted) + ".") if accepted else ".")
            )
        else:
            answer = (
                f"Using a naive non-intersection ablation, **{len(accepted)} candidate(s)** had at least one downstream source match: "
                + (", ".join(accepted) if accepted else "none")
                + "."
            )
        table = TablePayload(
            headers=["ChEMBL drug", "Canonical identity", "FDA application record(s)", "Matching trial(s)"],
            rows=rows,
            caption=f"Live cross-source {'intersection' if self.use_deterministic_join else 'union ablation'} for {target}",
        ) if rows else None
        claims = [Claim(text=answer, support_ids=list(dict.fromkeys(support_ids)))] if support_ids else []
        return answer, evidence, traces, claims, table, warnings

    async def _general_answer(self, question, conversation, user_evidence):
        if self.llm.available:
            context = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in conversation[-8:])
            supplied = "\n".join(str(item) for item in user_evidence[:30])
            return await self.llm.text(
                "You are ChatAlchemy, a biomedical and pharmaceutical research assistant. Be clear about when you are explaining general knowledge versus using supplied user evidence. Do not invent live database facts; questions requiring current database state should be handled by the evidence engine.",
                f"Conversation:\n{context}\n\nUser evidence:\n{supplied}\n\nQuestion:\n{question}",
            )
        if user_evidence:
            return (
                f"I found {len(user_evidence)} supplied evidence item(s). Configure the server-side OPENAI_API_KEY to enable "
                "natural-language synthesis of uploaded evidence; deterministic live database queries remain available without it."
            )
        return (
            "I can answer supported live pharmaceutical/biomedical database questions without an LLM. Configure the server-side "
            "OPENAI_API_KEY to enable broader conversational explanations."
        )

    @staticmethod
    def _first_entity(plan, entity_type: str, optional: bool = False):
        for entity in plan.entities:
            if entity.type == entity_type:
                return entity.text
        if optional:
            return None
        raise ValueError(f"Planner did not resolve a {entity_type} entity")
