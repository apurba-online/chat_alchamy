from __future__ import annotations

import asyncio
from typing import Any

from ..models import EvidenceItem
from .base import LiveSource


class ChEMBLSource(LiveSource):
    name = "ChEMBL"
    base = "https://www.ebi.ac.uk/chembl/api/data"

    async def target_drugs(self, target_query: str, *, limit: int = 20) -> list[EvidenceItem]:
        target_data = await self.get_json(f"{self.base}/target/search.json", params={"q": target_query, "limit": 10})
        targets = target_data.get("targets", []) or []
        if not targets:
            return []
        target = self._pick_target(target_query, targets)
        target_id = target.get("target_chembl_id")
        if not target_id:
            return []
        mech_data = await self.get_json(f"{self.base}/mechanism.json", params={"target_chembl_id": target_id, "limit": 1000})
        mechanisms = mech_data.get("mechanisms", []) or []
        molecule_ids: list[str] = []
        for mech in mechanisms:
            mid = mech.get("molecule_chembl_id") or mech.get("parent_molecule_chembl_id")
            if mid and mid not in molecule_ids:
                molecule_ids.append(mid)
            if len(molecule_ids) >= limit:
                break
        sem = asyncio.Semaphore(6)
        async def get_name(mid: str) -> tuple[str, str]:
            async with sem:
                try:
                    data = await self.get_json(f"{self.base}/molecule/{mid}.json")
                    return mid, data.get("pref_name") or mid
                except Exception:
                    return mid, mid
        names = dict(await asyncio.gather(*(get_name(mid) for mid in molecule_ids))) if molecule_ids else {}
        evidence: list[EvidenceItem] = []
        for mech in mechanisms:
            mid = mech.get("molecule_chembl_id") or mech.get("parent_molecule_chembl_id")
            if not mid or mid not in names:
                continue
            name = names[mid]
            evidence.append(EvidenceItem.build(subject=name, predicate="molecular_target", value=target_query, qualifiers={"target_chembl_id": target_id, "target_name": target.get("pref_name"), "mechanism": mech.get("mechanism_of_action"), "action_type": mech.get("action_type"), "molecule_chembl_id": mid}, source=self.name, source_record_id=f"{mid}:{target_id}", source_url=f"https://www.ebi.ac.uk/chembl/explore/compound/{mid}"))
            if len(evidence) >= limit:
                break
        return evidence

    @staticmethod
    def _pick_target(query: str, targets: list[dict[str, Any]]) -> dict[str, Any]:
        q = query.strip().lower()
        def score(t: dict[str, Any]) -> tuple[int, int]:
            pref = (t.get("pref_name") or "").lower()
            exact = int(pref == q or q in pref.split())
            human = int((t.get("organism") or "").lower() == "homo sapiens")
            return (exact, human)
        return sorted(targets, key=score, reverse=True)[0]
