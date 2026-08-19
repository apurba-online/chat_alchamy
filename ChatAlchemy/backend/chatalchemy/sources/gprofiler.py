from __future__ import annotations
from .base import BaseSource


class GProfilerSource(BaseSource):
    name = "gprofiler"
    endpoint = "https://biit.cs.ut.ee/gprofiler/api/gost/profile/"

    async def enrich(self, genes: list[str], sources: list[str] | None = None):
        payload = {"organism": "hsapiens", "query": genes, "ordered": False, "no_evidences": False, "user_threshold": 0.05, "sources": sources or ["GO:BP", "REAC", "KEGG"]}
        data, latency = await self._request_json("POST", self.endpoint, json=payload)
        out = []
        for r in data.get("result", []) or []:
            out.append({"term_id": r.get("native"), "term_name": r.get("name"), "source": r.get("source"), "p_value": r.get("p_value"), "intersection": r.get("intersections", [[]])[0] if r.get("intersections") else [], "term_size": r.get("term_size"), "query_size": r.get("query_size")})
        return out, latency
