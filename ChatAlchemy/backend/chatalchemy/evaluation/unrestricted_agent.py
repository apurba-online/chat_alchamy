from __future__ import annotations

import json
from typing import Any

from ..llm import LLMClient
from ..models import EvidenceItem

TOOL_NAMES = (
    "rxnorm",
    "dailymed",
    "openfda",
    "clinicaltrials",
    "chembl",
    "opentargets",
    "pubchem",
    "none",
)
DEFAULT_MAX_TOOL_STEPS = 40


class UnrestrictedToolAgent:
    """Evaluation baseline: an LLM chooses calls to the same live source adapters.

    This baseline intentionally does not use ChatAlchemy's typed planner,
    normalization logic, deterministic final joins, conflict analysis, or claim
    verifier. It is not used by the production application.

    The default 40-step ceiling is deliberately generous enough to cover the
    order of source calls used by ChatAlchemy's hardest multi-candidate
    cross-source path. Actual calls are recorded and reported separately.
    """

    def __init__(self, llm: LLMClient, sources: dict[str, Any], *, max_steps: int = DEFAULT_MAX_TOOL_STEPS, max_results: int = 20):
        self.llm = llm
        self.sources = sources
        self.max_steps = max_steps
        self.max_results = max_results

    @staticmethod
    def _decision_schema() -> dict[str, Any]:
        nullable = {"type": ["string", "null"]}
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "done": {"type": "boolean"},
                "tool": {"type": "string", "enum": list(TOOL_NAMES)},
                "drug": nullable,
                "target": nullable,
                "condition": nullable,
                "phase": nullable,
                "status": nullable,
                "gene": nullable,
                "compound": nullable,
                "reason": {"type": "string"},
            },
            "required": ["done", "tool", "drug", "target", "condition", "phase", "status", "gene", "compound", "reason"],
        }

    @staticmethod
    def _evidence_payload(items: list[EvidenceItem]) -> list[dict[str, Any]]:
        return [
            {
                "subject": item.subject,
                "predicate": item.predicate,
                "value": item.value,
                "qualifiers": item.qualifiers,
                "source": item.source,
                "source_record_id": item.source_record_id,
                "source_url": item.source_url,
                "retrieved_at": item.retrieved_at,
            }
            for item in items
        ]

    @staticmethod
    def _add_usage(total: dict[str, int], usage: dict[str, int]) -> None:
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            total[key] = total.get(key, 0) + int(usage.get(key, 0))

    async def _execute(self, decision: dict[str, Any]) -> list[EvidenceItem]:
        tool = decision.get("tool")
        if tool == "rxnorm":
            return await self.sources["rxnorm"].resolve(decision.get("drug") or "")
        if tool == "dailymed":
            return await self.sources["dailymed"].label_records(decision.get("drug") or "", max_results=self.max_results)
        if tool == "openfda":
            return await self.sources["openfda"].approval_records(decision.get("drug") or "", max_results=self.max_results)
        if tool == "clinicaltrials":
            return await self.sources["clinicaltrials"].search_trials(
                drug=decision.get("drug"),
                condition=decision.get("condition"),
                phase=decision.get("phase"),
                status=decision.get("status"),
                max_results=self.max_results,
            )
        if tool == "chembl":
            return await self.sources["chembl"].target_drugs(decision.get("target") or "", max_results=self.max_results)
        if tool == "opentargets":
            return await self.sources["opentargets"].gene_details(decision.get("gene") or "", max_results=self.max_results)
        if tool == "pubchem":
            return await self.sources["pubchem"].compound(decision.get("compound") or decision.get("drug") or "")
        return []

    async def retrieve(self, question: str, *, uploaded_candidates: list[str] | None = None) -> dict[str, Any]:
        evidence: list[EvidenceItem] = []
        trace: list[dict[str, Any]] = []
        usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        instructions = (
            "You are an unrestricted biomedical tool-use baseline. Choose the next tool needed to answer the question. "
            "You have RxNorm, DailyMed, Drugs@FDA/openFDA, ClinicalTrials.gov, ChEMBL, Open Targets, and PubChem. "
            "You may call tools sequentially and inspect prior evidence. Do not assume ChatAlchemy's routing or joins. "
            "For ClinicalTrials.gov use canonical phase values PHASE1/PHASE2/PHASE3/PHASE4 and statuses such as "
            "RECRUITING, COMPLETED, or ACTIVE_NOT_RECRUITING. Set done=true and tool=none when retrieval is sufficient."
        )
        for step in range(self.max_steps):
            state = {
                "question": question,
                "uploaded_candidates": uploaded_candidates or [],
                "step": step,
                "remaining_steps": self.max_steps - step,
                "evidence": self._evidence_payload(evidence),
                "previous_tool_calls": trace,
            }
            decision = await self.llm.json(
                instructions,
                json.dumps(state, default=str),
                "tool_decision",
                self._decision_schema(),
            )
            self._add_usage(usage, self.llm.last_usage)
            if decision.get("done") or decision.get("tool") == "none":
                trace.append({"step": step, "decision": decision, "ok": True, "result_count": 0})
                break
            try:
                items = await self._execute(decision)
                evidence.extend(items)
                trace.append({"step": step, "decision": decision, "ok": True, "result_count": len(items)})
            except Exception as exc:
                trace.append({"step": step, "decision": decision, "ok": False, "result_count": 0, "error": f"{type(exc).__name__}: {exc}"})
        return {"evidence": evidence, "trace": trace, "usage": usage}
