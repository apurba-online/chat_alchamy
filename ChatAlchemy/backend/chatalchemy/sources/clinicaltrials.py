from __future__ import annotations

from ..models import EvidenceItem
from .base import LiveSource


class ClinicalTrialsSource(LiveSource):
    name = "ClinicalTrials.gov"
    base_url = "https://clinicaltrials.gov/api/v2/studies"

    @staticmethod
    def _params(
        drug: str | None,
        condition: str | None,
        phase: str | None,
        status: str | None,
        page_size: int,
        page_token: str | None = None,
    ) -> dict[str, object]:
        params: dict[str, object] = {
            "pageSize": min(max(page_size, 1), 100),
            "format": "json",
        }
        if drug:
            params["query.intr"] = drug
        if condition:
            params["query.cond"] = condition
        if status:
            # API v2 exposes overall status as a server-side filter. Applying it
            # before pagination avoids a false empty result when the first 100
            # unfiltered studies contain no matching status.
            params["filter.overallStatus"] = status
        if phase:
            # Phase is expressed through the API v2 advanced filter grammar.
            # We still verify the returned record locally below so an upstream
            # query-language change cannot silently broaden the result set.
            params["filter.advanced"] = f"AREA[Phase]{phase}"
        if page_token:
            params["pageToken"] = page_token
        return params

    async def _search_page(
        self,
        drug: str | None,
        condition: str | None,
        phase: str | None,
        status: str | None,
        page_size: int,
        page_token: str | None = None,
    ) -> dict:
        params = self._params(drug, condition, phase, status, page_size, page_token)
        try:
            return await self._get(self.base_url, params=params)
        except Exception as primary:
            # Older/changed API deployments may reject a structured query
            # parameter. Fall back once to query.term while retaining the same
            # status/phase filters where possible. A failure of the fallback is
            # propagated and therefore visible in the source trace.
            terms = [value for value in (drug, condition) if value]
            if not terms:
                raise primary
            fallback: dict[str, object] = {
                "pageSize": min(max(page_size, 1), 100),
                "format": "json",
                "query.term": " AND ".join(terms),
            }
            if status:
                fallback["filter.overallStatus"] = status
            if phase:
                fallback["filter.advanced"] = f"AREA[Phase]{phase}"
            if page_token:
                fallback["pageToken"] = page_token
            return await self._get(self.base_url, params=fallback)

    async def search_trials(
        self,
        drug: str | None = None,
        condition: str | None = None,
        phase: str | None = None,
        status: str | None = None,
        max_results: int = 20,
    ) -> list[EvidenceItem]:
        out: list[EvidenceItem] = []
        seen: set[str] = set()
        page_token: str | None = None

        # At most a few pages are needed because public requests are capped at
        # 100 returned evidence items. The hard page bound also prevents an
        # upstream pagination loop from turning one request into unbounded work.
        for _ in range(5):
            remaining = max_results - len(out)
            if remaining <= 0:
                break
            data = await self._search_page(
                drug,
                condition,
                phase,
                status,
                page_size=min(max(remaining, 20), 100),
                page_token=page_token,
            )

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
                if not nct or nct in seen:
                    continue
                seen.add(str(nct))
                interventions = [
                    intervention.get("name")
                    for intervention in arms.get("interventions") or []
                    if intervention.get("name")
                ]
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
                        source_url=f"https://clinicaltrials.gov/study/{nct}",
                    )
                )
                if len(out) >= max_results:
                    break

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return out
