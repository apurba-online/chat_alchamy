from __future__ import annotations

import os

import httpx

from ..models import EvidenceItem
from .base import LiveSource


class OpenFDASource(LiveSource):
    name = "Drugs@FDA/openFDA"
    base_url = "https://api.fda.gov/drug/drugsfda.json"

    @staticmethod
    def _is_no_match(exc: Exception) -> bool:
        """Return True only for openFDA's documented zero-match response shape.

        openFDA represents an empty search as HTTP 404 with
        `error.code=NOT_FOUND` and `error.message=No matches found!`. That is a
        valid empty evidence set, not an upstream outage. Other 404s remain
        failures so broken URLs/schema changes cannot masquerade as absence.
        """
        if not isinstance(exc, httpx.HTTPStatusError) or exc.response.status_code != 404:
            return False
        try:
            payload = exc.response.json()
        except Exception:
            return False
        error = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(error, dict):
            return False
        code = str(error.get("code") or "").upper()
        message = str(error.get("message") or "").lower()
        return code == "NOT_FOUND" and "no matches found" in message

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
        valid_empty_requests = 0
        hard_errors: list[Exception] = []
        for search in terms:
            try:
                candidate = await self._get(
                    self.base_url,
                    params={**params, "search": search},
                    attempts=1,
                )
                if candidate.get("results"):
                    data = candidate
                    break
                # A 2xx response with no rows is also a valid empty search.
                valid_empty_requests += 1
            except Exception as exc:
                if self._is_no_match(exc):
                    valid_empty_requests += 1
                    continue
                hard_errors.append(exc)

        if data is None:
            # Do not call the result a verified absence if any fallback search
            # suffered a real API/network/schema failure. A matching record may
            # have existed only in the failed search field.
            if hard_errors:
                raise hard_errors[-1]
            if valid_empty_requests:
                return []
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
