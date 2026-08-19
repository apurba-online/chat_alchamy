from __future__ import annotations

from ..models import EvidenceItem
from .base import LiveSource


class RxNormSource(LiveSource):
    name = "RxNorm"
    base_url = "https://rxnav.nlm.nih.gov/REST"

    async def _properties(self, rxcui: str) -> dict:
        return (await self._get(f"{self.base_url}/rxcui/{rxcui}/properties.json")).get("properties") or {}

    async def _ingredient_for(self, rxcui: str) -> dict | None:
        for tty in ("IN", "PIN", "MIN"):
            try:
                data = await self._get(
                    f"{self.base_url}/rxcui/{rxcui}/related.json",
                    params={"tty": tty},
                    attempts=1,
                )
            except Exception:
                continue
            candidates: list[dict] = []
            for group in (data.get("relatedGroup") or {}).get("conceptGroup", []) or []:
                candidates.extend(group.get("conceptProperties") or [])
            if candidates:
                return candidates[0]
        return None

    async def resolve(self, drug: str) -> list[EvidenceItem]:
        if not drug:
            return []

        rxcuis: list[str] = []
        try:
            exact = await self._get(
                f"{self.base_url}/rxcui.json",
                params={"name": drug, "search": 2},
                attempts=1,
            )
            rxcuis = [str(x) for x in (exact.get("idGroup") or {}).get("rxnormId", []) or []]
        except Exception:
            rxcuis = []

        if not rxcuis:
            data = await self._get(
                f"{self.base_url}/approximateTerm.json",
                params={"term": drug, "maxEntries": 8, "option": 1},
            )
            rxcuis = [str(c.get("rxcui")) for c in (data.get("approximateGroup") or {}).get("candidate", []) or [] if c.get("rxcui")]

        if not rxcuis:
            return []

        ranked: list[tuple[int, dict]] = []
        for rxcui in rxcuis[:8]:
            try:
                props = await self._properties(rxcui)
            except Exception:
                continue
            if props:
                ranked.append(({"IN": 0, "PIN": 1, "MIN": 2}.get(props.get("tty", ""), 9), props))
        if not ranked:
            return []
        ranked.sort(key=lambda item: item[0])
        best = ranked[0][1]

        if ranked[0][0] >= 9 and best.get("rxcui"):
            ingredient = await self._ingredient_for(str(best["rxcui"]))
            if ingredient:
                best = ingredient

        name = best.get("name") or drug
        rxcui = str(best.get("rxcui") or "")
        return [
            EvidenceItem.build(
                subject=drug,
                predicate="canonical_drug_identity",
                value=name,
                qualifiers={"rxcui": rxcui, "tty": best.get("tty")},
                source=self.name,
                source_record_id=rxcui or None,
                source_url=f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/properties.json" if rxcui else None,
            )
        ]
