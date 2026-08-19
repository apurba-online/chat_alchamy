from __future__ import annotations

import asyncio
from typing import Any

from ..models import EvidenceItem
from .base import LiveSource


class ChEMBLSource(LiveSource):
    name = "ChEMBL"
    base = "https://www.ebi.ac.uk/chembl/api/data"

    async def target_drugs(self, target_query: str, *, limit: int = 20) -> list[EvidenceItem]:
        target_data = await self.get_json(
            f"{self.base}/target/search.json",
            params={"q": target_query, "limit": 10},
        )
        targets = target_data.get("targets", []) or []
        if not targets:
            return []

        # Full-text target search can rank related complexes/protein families above
        # the therapeutically useful single-protein target. Try the best human
        # candidates until one has drug-mechanism records instead of assuming hit #1.
        ranked_targets = sorted(targets, key=lambda t: self._target_score(target_query, t), reverse=True)
        selected_target: dict[str, Any] | None = None
        mechanisms: list[dict[str, Any]] = []
        for target in ranked_targets[:6]:
            target_id = target.get("target_chembl_id")
            if not target_id:
                continue
            mech_data = await self.get_json(
                f"{self.base}/mechanism.json",
                params={"target_chembl_id": target_id, "limit": 1000},
            )
            candidate_mechanisms = mech_data.get("mechanisms", []) or []
            if candidate_mechanisms:
                selected_target = target
                mechanisms = candidate_mechanisms
                break

        if not selected_target or not mechanisms:
            return []
        target_id = selected_target["target_chembl_id"]

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
            evidence.append(
                EvidenceItem.build(
                    subject=name,
                    predicate="molecular_target",
                    value=target_query,
                    qualifiers={
                        "target_chembl_id": target_id,
                        "target_name": selected_target.get("pref_name"),
                        "target_type": selected_target.get("target_type"),
                        "organism": selected_target.get("organism"),
                        "mechanism": mech.get("mechanism_of_action"),
                        "action_type": mech.get("action_type"),
                        "molecule_chembl_id": mid,
                    },
                    source=self.name,
                    source_record_id=f"{mid}:{target_id}",
                    source_url=f"https://www.ebi.ac.uk/chembl/explore/compound/{mid}",
                )
            )
            if len(evidence) >= limit:
                break
        return evidence

    @staticmethod
    def _target_score(query: str, target: dict[str, Any]) -> tuple[int, int, int, int]:
        q = query.strip().lower()
        pref = (target.get("pref_name") or "").lower()
        organism = (target.get("organism") or "").lower()
        target_type = (target.get("target_type") or "").upper()
        component_text = " ".join(
            str(v).lower()
            for component in target.get("target_components", []) or []
            for synonym in component.get("target_component_synonyms", []) or []
            for v in [synonym.get("component_synonym")]
            if v
        )
        symbol_match = int(q == pref or q in component_text.split())
        human = int(organism == "homo sapiens")
        single_protein = int(target_type == "SINGLE PROTEIN")
        text_match = int(q in pref)
        return (symbol_match, human, single_protein, text_match)
