from __future__ import annotations

import asyncio

from ..models import EvidenceItem
from .base import LiveSource


class OpenTargetsSource(LiveSource):
    name = "Open Targets"
    endpoint = "https://api.platform.opentargets.org/api/v4/graphql"

    async def _search_id(self, query_text: str, entity: str) -> str | None:
        query = '''
        query Search($q: String!, $entities: [String!]) {
          search(queryString: $q, entityNames: $entities, page: {index: 0, size: 5}) {
            hits { id entity name description }
          }
        }
        '''
        payload = await self._post_json(
            self.endpoint,
            {"query": query, "variables": {"q": query_text, "entities": [entity]}},
        )
        hits = (((payload.get("data") or {}).get("search") or {}).get("hits") or [])
        return str(hits[0].get("id")) if hits and hits[0].get("id") else None

    async def _drug_name(self, chembl_id: str) -> str:
        query = '''query Drug($id: String!) { drug(chemblId: $id) { id name } }'''
        try:
            payload = await self._post_json(self.endpoint, {"query": query, "variables": {"id": chembl_id}})
            drug = (payload.get("data") or {}).get("drug") or {}
            return str(drug.get("name") or chembl_id)
        except Exception:
            return chembl_id

    async def gene_details(self, gene: str, max_results: int = 10) -> list[EvidenceItem]:
        target_id = await self._search_id(gene, "target")
        if not target_id:
            return []

        query = '''
        query Target($id: String!) {
          target(ensemblId: $id) {
            id
            approvedSymbol
            approvedName
            associatedDiseases(page: {index: 0, size: 20}) {
              rows { disease { id name } score }
            }
            drugAndClinicalCandidates {
              rows {
                id
                drugId
                targetId
                maxClinicalStage
                diseases { diseaseId diseaseFromSource }
              }
            }
          }
        }
        '''
        payload = await self._post_json(self.endpoint, {"query": query, "variables": {"id": target_id}})
        obj = (payload.get("data") or {}).get("target") or {}
        if not obj:
            return []

        symbol = str(obj.get("approvedSymbol") or gene).upper()
        out = [
            EvidenceItem.build(
                subject=symbol,
                predicate="gene_identity",
                value=obj.get("approvedName") or symbol,
                qualifiers={"ensembl_id": target_id},
                source=self.name,
                source_record_id=target_id,
                source_url=f"https://platform.opentargets.org/target/{target_id}",
            )
        ]

        for row in ((obj.get("associatedDiseases") or {}).get("rows") or [])[:max_results]:
            disease = row.get("disease") or {}
            if not disease.get("name"):
                continue
            out.append(
                EvidenceItem.build(
                    subject=symbol,
                    predicate="gene_disease_association",
                    value=disease.get("name"),
                    qualifiers={"efo_id": disease.get("id"), "score": row.get("score")},
                    source=self.name,
                    source_record_id=disease.get("id"),
                    source_url=(
                        f"https://platform.opentargets.org/disease/{disease.get('id')}"
                        if disease.get("id")
                        else None
                    ),
                )
            )

        clinical_rows = ((obj.get("drugAndClinicalCandidates") or {}).get("rows") or [])[:max_results]
        drug_ids = list(dict.fromkeys(str(row.get("drugId")) for row in clinical_rows if row.get("drugId")))
        names = dict(
            await asyncio.gather(*((lambda drug_id: self._named_pair(drug_id))(drug_id) for drug_id in drug_ids))
        ) if drug_ids else {}

        for row in clinical_rows:
            drug_id = row.get("drugId")
            if not drug_id:
                continue
            disease_items = row.get("diseases") or []
            qualifiers = {
                "chembl_id": drug_id,
                "max_clinical_stage": row.get("maxClinicalStage"),
                "diseases": [item.get("diseaseFromSource") for item in disease_items if item.get("diseaseFromSource")],
                "disease_ids": [item.get("diseaseId") for item in disease_items if item.get("diseaseId")],
                "clinical_candidate_id": row.get("id"),
            }
            out.append(
                EvidenceItem.build(
                    subject=symbol,
                    predicate="known_drug",
                    value=names.get(str(drug_id), str(drug_id)),
                    qualifiers=qualifiers,
                    source=self.name,
                    source_record_id=str(drug_id),
                    source_url=f"https://platform.opentargets.org/target/{target_id}",
                )
            )
        return out

    async def _named_pair(self, drug_id: str) -> tuple[str, str]:
        return drug_id, await self._drug_name(drug_id)

    async def disease_genes(self, disease: str, max_results: int = 20) -> list[EvidenceItem]:
        disease_id = await self._search_id(disease, "disease")
        if not disease_id:
            return []
        query = '''
        query Disease($id: String!) {
          disease(efoId: $id) {
            id
            name
            associatedTargets(page: {index: 0, size: 50}) {
              rows { target { id approvedSymbol approvedName } score }
            }
          }
        }
        '''
        payload = await self._post_json(self.endpoint, {"query": query, "variables": {"id": disease_id}})
        obj = (payload.get("data") or {}).get("disease") or {}
        out: list[EvidenceItem] = []
        for row in ((obj.get("associatedTargets") or {}).get("rows") or [])[:max_results]:
            target = row.get("target") or {}
            if not target.get("approvedSymbol"):
                continue
            out.append(
                EvidenceItem.build(
                    subject=obj.get("name") or disease,
                    predicate="disease_gene_association",
                    value=target.get("approvedSymbol"),
                    qualifiers={
                        "ensembl_id": target.get("id"),
                        "gene_name": target.get("approvedName"),
                        "efo_id": disease_id,
                        "score": row.get("score"),
                    },
                    source=self.name,
                    source_record_id=target.get("id"),
                    source_url=f"https://platform.opentargets.org/disease/{disease_id}",
                )
            )
        return out
