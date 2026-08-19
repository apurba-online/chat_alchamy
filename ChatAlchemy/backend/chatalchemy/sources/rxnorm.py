from __future__ import annotations

from ..models import Entity, EvidenceItem
from .base import LiveSource


class RxNormSource(LiveSource):
    name = "RxNorm"
    base = "https://rxnav.nlm.nih.gov/REST"

    async def resolve(self, name: str) -> tuple[Entity | None, list[EvidenceItem]]:
        data = await self.get_json(f"{self.base}/approximateTerm.json", params={"term": name, "maxEntries": 5, "option": 1})
        candidates = data.get("approximateGroup", {}).get("candidate", []) or []
        if not candidates:
            return None, []
        best = candidates[0]
        rxcui = str(best.get("rxcui", "")).strip()
        if not rxcui:
            return None, []
        props = await self.get_json(f"{self.base}/rxcui/{rxcui}/properties.json")
        prop = props.get("properties") or {}
        canonical = prop.get("name") or best.get("name") or name
        entity = Entity(text=name, type="drug", canonical_name=canonical, ids={"rxcui": rxcui})
        evidence = [EvidenceItem.build(subject=canonical, predicate="drug_identity", value=canonical, qualifiers={"query_name": name, "tty": prop.get("tty"), "score": best.get("score")}, source=self.name, source_record_id=rxcui, source_url=f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/properties.json")]
        return entity, evidence

    async def version(self) -> str | None:
        data = await self.get_json(f"{self.base}/version.json")
        return data.get("version")
