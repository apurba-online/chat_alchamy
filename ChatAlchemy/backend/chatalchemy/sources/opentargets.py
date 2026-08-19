from __future__ import annotations

from uuid import uuid4
from .base import BaseSource
from ..models import EvidenceItem


class OpenTargetsSource(BaseSource):
    name = "opentargets"
    endpoint = "https://api.platform.opentargets.org/api/v4/graphql"

    async def disease_targets(self, disease: str, max_results: int = 20) -> tuple[list[EvidenceItem], float]:
        search_q = """query Search($q:String!){search(queryString:$q,entityNames:[\"disease\"],page:{index:0,size:5}){hits{id name entity}}}"""
        found, latency = await self._request_json("POST", self.endpoint, json={"query": search_q, "variables": {"q": disease}})
        hits = (((found.get("data") or {}).get("search") or {}).get("hits") or [])
        if not hits:
            return [], latency
        did = hits[0].get("id")
        assoc_q = """query Assoc($id:String!,$size:Int!){disease(efoId:$id){id name associatedTargets(page:{index:0,size:$size}){rows{score target{id approvedSymbol approvedName}}}}}"""
        data, lat2 = await self._request_json("POST", self.endpoint, json={"query": assoc_q, "variables": {"id": did, "size": max_results}})
        latency += lat2
        disease_obj = ((data.get("data") or {}).get("disease") or {})
        rows = ((disease_obj.get("associatedTargets") or {}).get("rows") or [])
        out = []
        for row in rows:
            target = row.get("target") or {}
            eid = target.get("id")
            symbol = target.get("approvedSymbol") or target.get("approvedName")
            out.append(EvidenceItem(id=f"ot-{uuid4().hex[:12]}", source=self.name, source_record_id=f"{did}:{eid}", source_url=f"https://platform.opentargets.org/disease/{did}/associations", subject=disease_obj.get("name") or disease, canonical_subject=disease_obj.get("name") or disease, predicate="disease_target", value=symbol, identifiers={"efo_id": did or "", "ensembl_id": eid or ""}, context={"association_score": row.get("score")}, raw=row))
        return out, latency

    async def gene_diseases(self, gene: str, max_results: int = 20) -> tuple[list[EvidenceItem], float]:
        search_q = """query Search($q:String!){search(queryString:$q,entityNames:[\"target\"],page:{index:0,size:5}){hits{id name entity}}}"""
        found, latency = await self._request_json("POST", self.endpoint, json={"query": search_q, "variables": {"q": gene}})
        hits = (((found.get("data") or {}).get("search") or {}).get("hits") or [])
        if not hits:
            return [], latency
        tid = hits[0].get("id")
        q = """query Assoc($id:String!,$size:Int!){target(ensemblId:$id){id approvedSymbol approvedName associatedDiseases(page:{index:0,size:$size}){rows{score disease{id name}}}}}"""
        data, lat2 = await self._request_json("POST", self.endpoint, json={"query": q, "variables": {"id": tid, "size": max_results}})
        latency += lat2
        target = ((data.get("data") or {}).get("target") or {})
        rows = ((target.get("associatedDiseases") or {}).get("rows") or [])
        out = []
        for row in rows:
            d = row.get("disease") or {}
            out.append(EvidenceItem(id=f"ot-{uuid4().hex[:12]}", source=self.name, source_record_id=f"{tid}:{d.get('id')}", source_url=f"https://platform.opentargets.org/target/{tid}/associations", subject=target.get("approvedSymbol") or gene, canonical_subject=target.get("approvedSymbol") or gene, predicate="gene_disease", value=d.get("name"), identifiers={"ensembl_id": tid or "", "efo_id": d.get("id") or ""}, context={"association_score": row.get("score")}, raw=row))
        return out, latency
