from __future__ import annotations

import os

from ..models import EvidenceItem
from .base import LiveSource


class OpenFDASource(LiveSource):
    name = "Drugs@FDA/openFDA"
    base_url = "https://api.fda.gov/drug/drugsfda.json"

    async def approval_records(self, drug: str, max_results: int = 20) -> list[EvidenceItem]:
        if not drug:
            return []

        terms = [
            f'openfda.generic_name:"{drug}"',
            f'openfda.brand_name:"{drug}"',
            f'products.active_ingredients.name:"{drug}"',
        ]
        params: dict[str, object] = {"limit": min(max_results, 100)}
        key = os.getenv("OPENFDA_API_KEY")
        if key:
            params["api_key"] = key

        data: dict | None = None
        successful_requests = 0
        last_error: Exception | None = None
        for search in terms:
            try:
                candidate = await self._get(
                    self.base_url,
                    params={**params, "search": search},
                    attempts=1,
                )
                successful_requests += 1
                if candidate.get("results"):
                    data = candidate
                    break
                if data is None:
                    # Preserve a genuine successful empty response so we can
                    # distinguish it from the case where every request failed.
                    data = candidate
            except Exception as exc:
                last_error = exc

        if successful_requests == 0 and last_error is not None:
            raise last_error
        if not data or not data.get("results"):
            return []

        out: list[EvidenceItem] = []
        for app in (data.get("results") or [])[:max_results]:
            appno = app.get("application_number")
            names = sorted(
                {
                    product.get("brand_name")
                    for product in app.get("products") or []
                    if product.get("brand_name")
                }
            )
            out.append(
                EvidenceItem.build(
                    subject=drug,
                    predicate="fda_application_record",
                    value=appno or "application record",
                    qualifiers={
                        "sponsor": app.get("sponsor_name"),
                        "brand_names": names,
                    },
                    source=self.name,
                    source_record_id=appno,
                    source_url="https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm",
                )
            )
        return out
