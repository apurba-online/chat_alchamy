from __future__ import annotations

import re

from .oracle import LiveOracle as _BaseLiveOracle


class LiveOracle(_BaseLiveOracle):
    """Direct-source oracle with current Open Targets search semantics.

    This remains separate from the application source adapter: it does not call
    ChatAlchemy's planner, evidence objects, deterministic composition, relation
    classifier, or evidence-link validator. The override only keeps the direct
    source procedure compatible with the current Open Targets search endpoint.
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
