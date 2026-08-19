from __future__ import annotations

import os
from typing import Any

from ..models import EvidenceItem
from .base import LiveSource, SourceError


class OpenFDASource(LiveSource):
    name = "Drugs@FDA/openFDA"
    endpoint = "https://api.fda.gov/drug/drugsfda.json"

    async def approval_records(self, names: list[str], *, limit: int = 20) -> list[EvidenceItem]:
        api_key = os.getenv("OPENFDA_API_KEY")
        seen: set[str] = set()
        evidence: list[EvidenceItem] = []
        for name in [n for n in names if n]:
            queries = [f'openfda.generic_name:"{name}"', f'openfda.brand_name:"{name}"', f'products.active_ingredients.name:"{name}"']
            payload: dict[str, Any] = {}
            for query in queries:
                params: dict[str, Any] = {"search": query, "limit": min(limit, 99)}
                if api_key:
                    params["api_key"] = api_key
                try:
                    payload = await self.get_json(self.endpoint, params=params)
                except SourceError:
                    continue
                if payload.get("results"):
                    break
            for record in payload.get("results", []) or []:
                app = record.get("application_number") or "unknown"
                if app in seen:
                    continue
                seen.add(app)
                products = record.get("products", []) or []
                product_summary = [{"brand_name": p.get("brand_name"), "dosage_form": p.get("dosage_form"), "route": p.get("route"), "marketing_status": p.get("marketing_status")} for p in products[:8]]
                openfda = record.get("openfda", {}) or {}
                subject = (openfda.get("generic_name") or [name])[0]
                evidence.append(EvidenceItem.build(subject=subject, predicate="fda_approval_record", value=app, qualifiers={"sponsor": record.get("sponsor_name"), "products": product_summary}, source=self.name, source_record_id=app, source_url=f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={''.join(ch for ch in app if ch.isdigit())}"))
        return evidence
