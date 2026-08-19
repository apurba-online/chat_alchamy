from __future__ import annotations

from typing import Any

from ..models import Entity, EvidenceItem
from .base import LiveSource


class RxNormSource(LiveSource):
    name = "RxNorm"
    base = "https://rxnav.nlm.nih.gov/REST"

    async def resolve(self, name: str) -> tuple[Entity | None, list[EvidenceItem]]:
        data = await self.get_json(
            f"{self.base}/approximateTerm.json",
            params={"term": name, "maxEntries": 5, "option": 1},
        )
        candidates = data.get("approximateGroup", {}).get("candidate", []) or []
        if not candidates:
            return None, []
        best = candidates[0]
        matched_rxcui = str(best.get("rxcui", "")).strip()
        if not matched_rxcui:
            return None, []

        props = await self.get_json(f"{self.base}/rxcui/{matched_rxcui}/properties.json")
        prop = props.get("properties") or {}
        matched_name = prop.get("name") or best.get("name") or name
        matched_tty = prop.get("tty")

        # Brand names and formulated products should normalize to their ingredient
        # concept when one is available. This makes cross-source joins stable and
        # ensures questions such as "generic identity of Tylenol" return the
        # ingredient rather than merely echoing the brand concept.
        canonical_rxcui = matched_rxcui
        canonical_name = matched_name
        canonical_tty = matched_tty
        if matched_tty not in {"IN", "PIN", "MIN"}:
            related = await self.get_json(
                f"{self.base}/rxcui/{matched_rxcui}/related.json",
                params={"tty": "IN PIN MIN"},
            )
            concepts: list[dict[str, Any]] = []
            for group in related.get("relatedGroup", {}).get("conceptGroup", []) or []:
                concepts.extend(group.get("conceptProperties", []) or [])
            if concepts:
                rank = {"IN": 0, "PIN": 1, "MIN": 2}
                ingredient = sorted(concepts, key=lambda c: rank.get(c.get("tty"), 9))[0]
                canonical_rxcui = str(ingredient.get("rxcui") or matched_rxcui)
                canonical_name = ingredient.get("name") or matched_name
                canonical_tty = ingredient.get("tty") or matched_tty

        ids = {"rxcui": canonical_rxcui}
        if canonical_rxcui != matched_rxcui:
            ids["matched_rxcui"] = matched_rxcui
        entity = Entity(text=name, type="drug", canonical_name=canonical_name, ids=ids)
        evidence = [
            EvidenceItem.build(
                subject=canonical_name,
                predicate="drug_identity",
                value=canonical_name,
                qualifiers={
                    "query_name": name,
                    "tty": canonical_tty,
                    "score": best.get("score"),
                    "matched_name": matched_name,
                    "matched_tty": matched_tty,
                    "matched_rxcui": matched_rxcui,
                },
                source=self.name,
                source_record_id=canonical_rxcui,
                source_url=f"https://rxnav.nlm.nih.gov/REST/rxcui/{canonical_rxcui}/properties.json",
            )
        ]
        return entity, evidence

    async def version(self) -> str | None:
        data = await self.get_json(f"{self.base}/version.json")
        return data.get("version")
