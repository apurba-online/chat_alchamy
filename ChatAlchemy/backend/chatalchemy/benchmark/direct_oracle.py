from __future__ import annotations

import asyncio
import re

import httpx

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

    @staticmethod
    def _openfda_no_match(exc: Exception) -> bool:
        if not isinstance(exc, httpx.HTTPStatusError) or exc.response.status_code != 404:
            return False
        try:
            payload = exc.response.json()
        except Exception:
            return False
        error = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(error, dict):
            return False
        return (
            str(error.get("code") or "").upper() == "NOT_FOUND"
            and "no matches found" in str(error.get("message") or "").lower()
        )

    async def _identity(self, drug: str):
        base = "https://rxnav.nlm.nih.gov/REST"
        ids: list[str] = []
        try:
            exact = await self._get(
                f"{base}/rxcui.json",
                {"name": drug, "search": 2},
                attempts=1,
            )
            ids = [str(value) for value in (exact.get("idGroup") or {}).get("rxnormId", []) or []]
        except Exception:
            # Approximate term resolution is the intended fallback for aliases.
            ids = []

        if not ids:
            approximate = await self._get(
                f"{base}/approximateTerm.json",
                {"term": drug, "maxEntries": 8, "option": 1},
            )
            ids = [
                str(candidate.get("rxcui"))
                for candidate in (approximate.get("approximateGroup") or {}).get("candidate", []) or []
                if candidate.get("rxcui")
            ]
        if not ids:
            return None, []

        ranked: list[tuple[int, dict]] = []
        property_successes = 0
        property_errors: list[Exception] = []
        for rid in ids[:8]:
            try:
                props = (await self._get(f"{base}/rxcui/{rid}/properties.json")).get("properties") or {}
                property_successes += 1
            except Exception as exc:
                property_errors.append(exc)
                continue
            if props:
                ranked.append(({"IN": 0, "PIN": 1, "MIN": 2}.get(props.get("tty", ""), 9), props))

        if not ranked:
            if property_successes == 0 and property_errors:
                raise property_errors[-1]
            return None, []

        ranked.sort(key=lambda item: item[0])
        best = ranked[0][1]
        if ranked[0][0] >= 9 and best.get("rxcui"):
            related_successes = 0
            related_errors: list[Exception] = []
            for tty in ("IN", "PIN", "MIN"):
                try:
                    related = await self._get(
                        f"{base}/rxcui/{best['rxcui']}/related.json",
                        {"tty": tty},
                        attempts=1,
                    )
                    related_successes += 1
                except Exception as exc:
                    related_errors.append(exc)
                    continue
                concepts = [
                    concept
                    for group in (related.get("relatedGroup") or {}).get("conceptGroup", []) or []
                    for concept in group.get("conceptProperties") or []
                ]
                if concepts:
                    best = concepts[0]
                    break
            if related_successes == 0 and related_errors:
                raise related_errors[-1]

        rid = best.get("rxcui")
        return str(best.get("name") or drug).lower(), [self._record("RxNorm", rid)]

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
        valid_empty_requests = 0
        hard_errors: list[Exception] = []
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
                if candidate.get("results"):
                    payload = candidate
                    break
                valid_empty_requests += 1
            except Exception as exc:
                if self._openfda_no_match(exc):
                    valid_empty_requests += 1
                    continue
                hard_errors.append(exc)

        if payload is None:
            if hard_errors:
                raise hard_errors[-1]
            if valid_empty_requests:
                return [], []
            return [], []

        rows = payload.get("results") or []
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
