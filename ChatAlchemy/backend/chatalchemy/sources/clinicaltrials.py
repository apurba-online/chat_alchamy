from __future__ import annotations

from typing import Any

from ..models import EvidenceItem
from .base import LiveSource

PHASE_ALIASES = {"1": "PHASE1", "I": "PHASE1", "2": "PHASE2", "II": "PHASE2", "3": "PHASE3", "III": "PHASE3", "4": "PHASE4", "IV": "PHASE4"}


class ClinicalTrialsSource(LiveSource):
    name = "ClinicalTrials.gov"
    endpoint = "https://clinicaltrials.gov/api/v2/studies"

    async def search_trials(self, *, intervention: str, condition: str | None = None, phase: str | None = None, status: str | None = None, limit: int = 100) -> list[EvidenceItem]:
        params: dict[str, Any] = {"query.intr": intervention, "pageSize": min(limit, 1000), "format": "json"}
        if condition:
            params["query.cond"] = condition
        data = await self.get_json(self.endpoint, params=params)
        out: list[EvidenceItem] = []
        desired_phase = PHASE_ALIASES.get(str(phase).upper(), str(phase).upper()) if phase else None
        desired_status = status.upper().replace(" ", "_") if status else None
        for study in data.get("studies", []) or []:
            protocol = study.get("protocolSection", {}) or {}
            ident = protocol.get("identificationModule", {}) or {}
            status_mod = protocol.get("statusModule", {}) or {}
            design = protocol.get("designModule", {}) or {}
            conditions_mod = protocol.get("conditionsModule", {}) or {}
            arms = protocol.get("armsInterventionsModule", {}) or {}
            nct = ident.get("nctId")
            phases = design.get("phases", []) or []
            overall = status_mod.get("overallStatus")
            conditions = conditions_mod.get("conditions", []) or []
            interventions = [i.get("name") for i in arms.get("interventions", []) or [] if i.get("name")]
            if desired_phase and desired_phase not in phases:
                continue
            if desired_status and (overall or "").upper() != desired_status:
                continue
            if not nct:
                continue
            out.append(EvidenceItem.build(subject=intervention, predicate="clinical_trial", value=nct, qualifiers={"title": ident.get("briefTitle"), "phase": phases, "status": overall, "condition": conditions, "interventions": interventions}, source=self.name, source_record_id=nct, source_url=f"https://clinicaltrials.gov/study/{nct}"))
        return out

    async def version(self) -> str | None:
        data = await self.get_json("https://clinicaltrials.gov/api/v2/version")
        return data.get("dataTimestamp") or data.get("apiVersion")
