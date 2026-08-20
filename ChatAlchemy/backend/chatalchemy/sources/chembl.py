from __future__ import annotations

import asyncio

from ..models import EvidenceItem
from .base import LiveSource


class ChEMBLSource(LiveSource):
    name = "ChEMBL"
    base_url = "https://www.ebi.ac.uk/chembl/api/data"

    async def target_drugs(self, target: str, max_results: int = 20) -> list[EvidenceItem]:
        if not target:
            return []

        targets = (
            await self._get(
                f"{self.base_url}/target/search.json",
                params={"q": target, "limit": 10},
            )
        ).get("targets") or []

        def score(row: dict) -> int:
            text = " ".join(
                str(row.get(key, ""))
                for key in ["pref_name", "target_chembl_id", "organism", "target_type"]
            ).upper()
            value = 10 if target.upper() in text else 0
            value += 5 if row.get("organism") == "Homo sapiens" else 0
            value += 3 if row.get("target_type") == "SINGLE PROTEIN" else 0
            return value

        selected_targets = [row for row in sorted(targets, key=score, reverse=True)[:6] if row.get("target_chembl_id")]
        mechanism_rows: list[tuple[str, dict]] = []
        mechanism_failures: list[Exception] = []
        successful_mechanism_requests = 0

        for row in selected_targets:
            target_id = str(row["target_chembl_id"])
            try:
                payload = await self._get(
                    f"{self.base_url}/mechanism.json",
                    params={"target_chembl_id": target_id, "limit": 50},
                    attempts=1,
                )
                successful_mechanism_requests += 1
                mechanism_rows.extend((target_id, item) for item in payload.get("mechanisms") or [])
            except Exception as exc:
                mechanism_failures.append(exc)

        if selected_targets and successful_mechanism_requests == 0 and mechanism_failures:
            # A failed mechanism service is not the same thing as a target with
            # no mechanism records. Let the trace layer surface the outage.
            raise mechanism_failures[-1]
        if not mechanism_rows:
            return []

        molecule_ids: list[str] = []
        for _, mechanism in mechanism_rows:
            molecule_id = mechanism.get("molecule_chembl_id")
            if molecule_id and molecule_id not in molecule_ids:
                molecule_ids.append(str(molecule_id))

        async def molecule(molecule_id: str) -> tuple[str, dict]:
            try:
                return molecule_id, await self._get(
                    f"{self.base_url}/molecule/{molecule_id}.json",
                    attempts=1,
                )
            except Exception:
                # The mechanism row itself is still a valid ChEMBL record; if
                # optional molecule-name enrichment fails, retain the ChEMBL ID.
                return molecule_id, {}

        molecules = dict(
            await asyncio.gather(*(molecule(molecule_id) for molecule_id in molecule_ids[:max_results]))
        )

        out: list[EvidenceItem] = []
        seen: set[str] = set()
        for target_id, mechanism in mechanism_rows:
            molecule_id = mechanism.get("molecule_chembl_id")
            if not molecule_id or molecule_id in seen:
                continue
            molecule_id = str(molecule_id)
            seen.add(molecule_id)
            molecule_payload = molecules.get(molecule_id) or {}
            name = molecule_payload.get("pref_name") or molecule_id
            out.append(
                EvidenceItem.build(
                    subject=target.upper(),
                    predicate="targeting_drug",
                    value=name,
                    qualifiers={
                        "molecule_chembl_id": molecule_id,
                        "target_chembl_id": target_id,
                        "mechanism": mechanism.get("mechanism_of_action"),
                        "action_type": mechanism.get("action_type"),
                    },
                    source=self.name,
                    source_record_id=molecule_id,
                    source_url=f"https://www.ebi.ac.uk/chembl/explore/compound/{molecule_id}",
                )
            )
            if len(out) >= max_results:
                break
        return out
