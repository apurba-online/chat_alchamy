from __future__ import annotations

from ..models import EvidenceItem
from .base import LiveSource


class DailyMedSource(LiveSource):
    name = "DailyMed"
    endpoint = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json"

    async def label_records(self, *, drug_name: str | None = None, rxcui: str | None = None, limit: int = 20) -> list[EvidenceItem]:
        params: dict[str, str | int] = {"pagesize": min(limit, 100), "page": 1}
        if rxcui:
            params["rxcui"] = rxcui
        elif drug_name:
            params["drug_name"] = drug_name
            params["name_type"] = "both"
        else:
            return []
        data = await self.get_json(self.endpoint, params=params)
        out: list[EvidenceItem] = []
        for row in data.get("data", []) or []:
            setid = row.get("setid")
            if not setid:
                continue
            out.append(EvidenceItem.build(subject=drug_name or rxcui or "drug", predicate="dailymed_label_record", value=setid, qualifiers={"title": row.get("title"), "spl_version": row.get("spl_version"), "published_date": row.get("published_date")}, source=self.name, source_record_id=setid, source_url=f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={setid}"))
        return out
