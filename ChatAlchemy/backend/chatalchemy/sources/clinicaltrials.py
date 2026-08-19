from __future__ import annotations

from ..models import EvidenceItem
from .base import LiveSource


class ClinicalTrialsSource(LiveSource):
    name = "ClinicalTrials.gov"
    base_url = "https://clinicaltrials.gov/api/v2/studies"

    async def _search(self, drug: str | None, condition: str | None, page_size: int) -> dict:
        params: dict[str, object] = {"pageSize": min(page_size, 100)}
        if drug:
            params["query.intr"] = drug
        if condition:
            params["query.cond"] = condition
        try:
            return await self._get(self.base_url, params=params)
        except Exception as primary:
            terms = [x for x in [drug, condition] if x]
            if not terms:
                raise primary
            return await self._get(
                self.base_url,
                params={"pageSize": min(page_size, 100), "query.term": " AND ".join(terms)},
            )

    async def search_trials(
        self,
        drug: str | None = None,
        condition: str | None = None,
        phase: str | None = None,
        status: str | None = None,
        max_results: int = 20,
    ) -> list[EvidenceItem]:
        data = await self._search(drug, condition, max_results * 3)
        out: list[EvidenceItem] = []
        for study in data.get("studies") or []:
            protocol = study.get("protocolSection") or {}
            identification = protocol.get("identificationModule") or {}
            design = protocol.get("designModule") or {}
            status_module = protocol.get("statusModule") or {}
            conditions = protocol.get("conditionsModule") or {}
            arms = protocol.get("armsInterventionsModule") or {}
            nct = identification.get("nctId")
            phases = design.get("phases") or []
            overall = status_module.get("overallStatus")
            if phase and phase not in phases:
                continue
            if status and overall != status:
                continue
            interventions = [i.get("name") for i in arms.get("interventions") or [] if i.get("name")]
            out.append(
                EvidenceItem.build(
                    subject=drug or condition or nct or "trial",
                    predicate="clinical_trial",
                    value=nct,
                    qualifiers={
                        "title": identification.get("briefTitle"),
                        "phases": phases,
                        "status": overall,
                        "conditions": conditions.get("conditions") or [],
                        "interventions": interventions,
                    },
                    source=self.name,
                    source_record_id=nct,
                    source_url=f"https://clinicaltrials.gov/study/{nct}" if nct else None,
                )
            )
            if len(out) >= max_results:
                break
        return out
