from __future__ import annotations

import asyncio
import re

from .oracle import LiveOracle as _BaseLiveOracle


class LiveOracle(_BaseLiveOracle):
    """Direct-source oracle with current source contracts and failure semantics.

    This remains separate from the application source adapter: it does not call
    ChatAlchemy's planner, evidence objects, deterministic composition, relation
    classifier, or evidence-link validator. These overrides keep the direct
    source procedure compatible with current APIs and ensure that complete
    upstream failure becomes oracle unavailability rather than an empty gold set.
    """

    @staticmethod
    def _normalise(text: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", text.lower()))

    async def _ot_search_id(self, query_text: str, entity: str) -> str | None:
        endpoint = "https://api.platform.opentargets.org/api/v4/graphql"
        query = '''
        query Search($q: String!) {
          search(queryString: $q, page: {index: 0, size: 20}) {
            hits { id entity name description score }
          }
        }
        '''
        payload = await self._post(endpoint, query, {"q": query_text})
        hits = [
            hit
            for hit in (((payload.get("data") or {}).get("search") or {}).get("hits") or [])
            if str(hit.get("entity") or "").lower() == entity.lower() and hit.get("id")
        ]
        if not hits:
            return None

        wanted = self._normalise(query_text)

        def rank(hit: dict) -> tuple[int, float]:
            name = self._normalise(str(hit.get("name") or ""))
            exact = 1 if name == wanted else 0
            return exact, float(hit.get("score") or 0.0)

        best = max(hits, key=rank)
        return str(best["id"])

    async def _approvals(self, drug: str, limit: int = 20):
        endpoint = "https://api.fda.gov/drug/drugsfda.json"
        payload = None
        successful_requests = 0
        last_error: Exception | None = None
        searches = [
            f'openfda.generic_name:"{drug}"',
            f'openfda.brand_name:"{drug}"',
            f'products.active_ingredients.name:"{drug}"',
        ]
        for search in searches:
            try:
                candidate = await self._get(
                    endpoint,
                    {"search": search, "limit": min(limit, 100)},
                    attempts=1,
                )
                successful_requests += 1
                if candidate.get("results"):
                    payload = candidate
                    break
                if payload is None:
                    payload = candidate
            except Exception as exc:
                last_error = exc

        if successful_requests == 0 and last_error is not None:
            raise last_error

        rows = (payload or {}).get("results") or []
        apps = sorted({str(row.get("application_number")) for row in rows if row.get("application_number")})
        return apps, [self._record("Drugs@FDA/openFDA", record) for record in apps]

    async def _target_drugs(self, target: str, limit: int = 20):
        base = "https://www.ebi.ac.uk/chembl/api/data"
        targets = (
            await self._get(
                f"{base}/target/search.json",
                {"q": target, "limit": 10},
            )
        ).get("targets") or []

        def score(row: dict) -> int:
            text = " ".join(
                str(row.get(key, ""))
                for key in ["pref_name", "target_chembl_id", "organism", "target_type"]
            ).upper()
            return (
                (10 if target.upper() in text else 0)
                + (5 if row.get("organism") == "Homo sapiens" else 0)
                + (3 if row.get("target_type") == "SINGLE PROTEIN" else 0)
            )

        selected = [
            row
            for row in sorted(targets, key=score, reverse=True)[:6]
            if row.get("target_chembl_id")
        ]
        mechanisms: list[dict] = []
        successful_mechanism_requests = 0
        last_error: Exception | None = None
        for item in selected:
            target_id = item.get("target_chembl_id")
            try:
                response = await self._get(
                    f"{base}/mechanism.json",
                    {"target_chembl_id": target_id, "limit": 50},
                    attempts=1,
                )
                successful_mechanism_requests += 1
                mechanisms.extend(response.get("mechanisms") or [])
            except Exception as exc:
                last_error = exc

        if selected and successful_mechanism_requests == 0 and last_error is not None:
            raise last_error

        molecule_ids = list(
            dict.fromkeys(
                str(mechanism.get("molecule_chembl_id"))
                for mechanism in mechanisms
                if mechanism.get("molecule_chembl_id")
            )
        )[:limit]

        async def fetch(molecule_id: str):
            try:
                return molecule_id, await self._get(
                    f"{base}/molecule/{molecule_id}.json",
                    attempts=1,
                )
            except Exception:
                # Mechanism records are still valid even if optional preferred
                # molecule-name enrichment is temporarily unavailable.
                return molecule_id, {}

        molecules = dict(await asyncio.gather(*(fetch(mid) for mid in molecule_ids))) if molecule_ids else {}
        names = [str((molecules.get(mid) or {}).get("pref_name") or mid).lower() for mid in molecule_ids]
        return sorted(set(names)), [self._record("ChEMBL", mid) for mid in molecule_ids]
