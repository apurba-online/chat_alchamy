from __future__ import annotations

import re
from typing import Any

from ..models import EvidenceItem
from .base import LiveSource


class OpenTargetsSource(LiveSource):
    name = "Open Targets"
    endpoint = "https://api.platform.opentargets.org/api/v4/graphql"

    @staticmethod
    def _normalise_name(text: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", text.lower()))

    async def _graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        """Execute GraphQL and treat a 200-with-errors response as a source failure.

        GraphQL transports commonly return HTTP 200 even when the query itself
        failed validation or execution. If those errors are ignored, the caller
        can incorrectly report a successful zero-result query. ChatAlchemy must
        distinguish source failure from a genuine empty evidence set.
        """
        payload = await self._post_json(
            self.endpoint,
            {"query": query, "variables": variables},
        )
        errors = payload.get("errors") or []
        if errors:
            messages = "; ".join(str(item.get("message") or item) for item in errors[:5])
            raise RuntimeError(f"Open Targets GraphQL error: {messages}")
        return payload

    async def _search_hit(self, query_text: str, entity: str) -> dict | None:
        query = '''
        query Search($q: String!) {
          search(queryString: $q, page: {index: 0, size: 20}) {
            hits { id entity name description score }
          }
        }
        '''
        variants = list(dict.fromkeys([query_text, re.sub(r"[-–—]+", " ", query_text)]))
        hits: list[dict] = []
        for variant in variants:
            payload = await self._graphql(query, {"q": variant})
            returned = (((payload.get("data") or {}).get("search") or {}).get("hits") or [])
            hits.extend(hit for hit in returned if str(hit.get("entity") or "").lower() == entity.lower())

        unique: dict[str, dict] = {}
        for hit in hits:
            hit_id = str(hit.get("id") or "")
            if hit_id and hit_id not in unique:
                unique[hit_id] = hit
        if not unique:
            return None

        wanted = self._normalise_name(query_text)
        wanted_tokens = set(wanted.split())

        def score(hit: dict) -> tuple[float, float, int]:
            name = self._normalise_name(str(hit.get("name") or ""))
            description = self._normalise_name(str(hit.get("description") or ""))
            name_tokens = set(name.split())
            overlap = len(wanted_tokens & name_tokens) / max(1, len(wanted_tokens | name_tokens))
            exact = 1.0 if name == wanted else 0.0
            containment = 1.0 if wanted and (wanted in name or name in wanted) else 0.0
            description_overlap = len(wanted_tokens & set(description.split())) / max(1, len(wanted_tokens))
            upstream_score = float(hit.get("score") or 0.0)
            return (
                exact * 100 + containment * 20 + overlap * 10 + description_overlap,
                upstream_score,
                -len(name),
            )

        return max(unique.values(), key=score)

    async def _search_id(self, query_text: str, entity: str) -> str | None:
        hit = await self._search_hit(query_text, entity)
        return str(hit.get("id")) if hit and hit.get("id") else None

    async def gene_details(self, gene: str, max_results: int = 10) -> list[EvidenceItem]:
        target_id = await self._search_id(gene, "target")
        if not target_id:
            return []

        # Current Open Targets GraphQL replaces backing-model IDs with resolved
        # objects in ClinicalTargetFromTarget: `drugId` -> `drug`, `diseaseId`
        # -> `disease`, and `targetId` is excluded entirely.
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
                drug { id name }
                maxClinicalStage
                diseases {
                  diseaseFromSource
                  disease { id name }
                }
              }
            }
          }
        }
        '''
        payload = await self._graphql(query, {"id": target_id})
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
        for row in clinical_rows:
            drug = row.get("drug") or {}
            drug_id = drug.get("id")
            if not drug_id:
                continue
            disease_items = row.get("diseases") or []
            mapped_diseases = [item.get("disease") or {} for item in disease_items]
            qualifiers = {
                "chembl_id": drug_id,
                "max_clinical_stage": row.get("maxClinicalStage"),
                "diseases": [
                    item.get("diseaseFromSource") or mapped.get("name")
                    for item, mapped in zip(disease_items, mapped_diseases)
                    if item.get("diseaseFromSource") or mapped.get("name")
                ],
                "disease_ids": [mapped.get("id") for mapped in mapped_diseases if mapped.get("id")],
                "clinical_candidate_id": row.get("id"),
            }
            out.append(
                EvidenceItem.build(
                    subject=symbol,
                    predicate="known_drug",
                    value=drug.get("name") or str(drug_id),
                    qualifiers=qualifiers,
                    source=self.name,
                    source_record_id=str(drug_id),
                    source_url=f"https://platform.opentargets.org/target/{target_id}",
                )
            )
        return out

    async def disease_genes(self, disease: str, max_results: int = 20) -> list[EvidenceItem]:
        hit = await self._search_hit(disease, "disease")
        disease_id = str(hit.get("id")) if hit and hit.get("id") else None
        if not disease_id:
            return []

        query = '''
        query Disease($id: String!) {
          disease(efoId: $id) {
            id
            name
            associatedTargets(
              page: {index: 0, size: 50}
              orderByScore: "score desc"
              enableIndirect: true
            ) {
              rows { target { id approvedSymbol approvedName } score }
            }
          }
        }
        '''
        payload = await self._graphql(query, {"id": disease_id})
        obj = (payload.get("data") or {}).get("disease") or {}
        if not obj:
            return []

        canonical_name = str(obj.get("name") or hit.get("name") or disease)
        out: list[EvidenceItem] = []
        for row in ((obj.get("associatedTargets") or {}).get("rows") or [])[:max_results]:
            target = row.get("target") or {}
            if not target.get("approvedSymbol"):
                continue
            out.append(
                EvidenceItem.build(
                    subject=canonical_name,
                    predicate="disease_gene_association",
                    value=target.get("approvedSymbol"),
                    qualifiers={
                        "ensembl_id": target.get("id"),
                        "gene_name": target.get("approvedName"),
                        "efo_id": disease_id,
                        "score": row.get("score"),
                        "include_indirect": True,
                    },
                    source=self.name,
                    source_record_id=target.get("id"),
                    source_url=f"https://platform.opentargets.org/disease/{disease_id}/associations",
                )
            )
        return out
