from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any

from ..llm import LLMClient
from ..models import BiomedicalExtractResponse
from ..sources import OpenTargetsSource

COMMON_GENE_EXCLUSIONS = {
    "DNA", "RNA", "PCR", "CT", "MRI", "FDA", "WHO", "USA", "COVID", "HIV", "ATP", "ADP", "AND", "THE"
}
GENE_RE = re.compile(r"\b[A-Z][A-Z0-9-]{1,10}\b")


class BiomedicalService:
    def __init__(self, llm: LLMClient, opentargets: OpenTargetsSource):
        self.llm = llm
        self.opentargets = opentargets

    async def extract_document(self, text: str, filename: str | None = None) -> BiomedicalExtractResponse:
        cleaned = " ".join(text.split())
        if self.llm.available:
            schema = {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "summary": {"type": "string"},
                    "genes": {"type": "array", "items": {"type": "string"}},
                    "suggested_diseases": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["summary", "genes", "suggested_diseases"],
            }
            result = await self.llm.json(
                "You are a biomedical research extraction system. Summarize the supplied document and extract only explicitly mentioned human gene symbols and explicitly mentioned diseases/conditions. Do not infer genes that are not written in the document.",
                cleaned[:100000],
                "biomedical_document",
                schema,
            )
            return BiomedicalExtractResponse(
                summary=result.get("summary", ""),
                genes=sorted(set(g.upper() for g in result.get("genes", []) if g)),
                suggested_diseases=sorted(set(result.get("suggested_diseases", []))),
            )

        genes = sorted({g for g in GENE_RE.findall(cleaned) if g not in COMMON_GENE_EXCLUSIONS})[:50]
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        summary = " ".join(sentences[:5])[:1800] or f"Processed {filename or 'document'}; no textual summary was available."
        return BiomedicalExtractResponse(summary=summary, genes=genes, suggested_diseases=[])

    # Retained as tested statistical utilities, but not presented as enrichment
    # until ChatAlchemy has a validated background universe for the selected source.
    @staticmethod
    def benjamini_hochberg(p_values: list[float]) -> list[float]:
        n = len(p_values)
        order = sorted(range(n), key=lambda i: p_values[i])
        adjusted = [1.0] * n
        prev = 1.0
        for rank_from_end, idx in enumerate(reversed(order), start=1):
            rank = n - rank_from_end + 1
            value = min(prev, p_values[idx] * n / rank)
            adjusted[idx] = min(1.0, value)
            prev = value
        return adjusted

    @staticmethod
    def hypergeom_tail(k: int, K: int, n: int, N: int) -> float:
        if any(x < 0 for x in [k, K, n, N]) or K > N or n > N:
            return 1.0
        denominator = math.comb(N, n)
        if denominator == 0:
            return 1.0
        return min(
            1.0,
            sum(
                math.comb(K, i) * math.comb(N - K, n - i)
                for i in range(k, min(K, n) + 1)
                if n - i <= N - K
            ) / denominator,
        )

    async def analyze(self, genes: list[str], query: str | None, paper_summary: str | None = None) -> dict[str, Any]:
        genes = sorted({gene.strip().upper() for gene in genes if gene.strip()})
        evidence = []

        if query:
            disease_evidence = await self.opentargets.disease_genes(query, max_results=50)
            evidence.extend(disease_evidence)
            symbols = {str(item.value).upper() for item in disease_evidence}
            genes = [gene for gene in genes if gene in symbols] if genes else list(symbols)

        gene_rows = []
        graph_nodes: dict[str, Any] = {}
        graph_edges: list[dict[str, Any]] = []
        disease_to_genes: dict[str, set[str]] = defaultdict(set)
        disease_to_scores: dict[str, list[float]] = defaultdict(list)

        for gene in genes[:50]:
            gene_evidence = await self.opentargets.gene_details(gene, max_results=10)
            evidence.extend(gene_evidence)
            identity = next((item for item in gene_evidence if item.predicate == "gene_identity"), None)
            associations = [item for item in gene_evidence if item.predicate == "gene_disease_association"]
            scores = [float(item.qualifiers.get("score") or 0) for item in associations]
            average_score = sum(scores) / len(scores) if scores else 0.0
            ensembl = identity.qualifiers.get("ensembl_id") if identity else None
            disease_text = ", ".join(
                f"{item.value} [{item.qualifiers.get('efo_id', '')}] [{float(item.qualifiers.get('score') or 0):.3f}]"
                for item in associations
            )
            gene_rows.append([
                gene,
                identity.value if identity else "",
                ensembl or "",
                f"{average_score:.3f}",
                disease_text or "No disease associations found",
            ])
            graph_nodes[f"gene:{gene}"] = {"data": {"id": f"gene:{gene}", "label": gene, "type": "gene"}}

            for association in associations:
                disease = str(association.value)
                disease_id = str(association.qualifiers.get("efo_id") or disease)
                score = float(association.qualifiers.get("score") or 0)
                disease_to_genes[disease].add(gene)
                disease_to_scores[disease].append(score)
                graph_nodes[f"disease:{disease_id}"] = {
                    "data": {"id": f"disease:{disease_id}", "label": disease, "type": "disease"}
                }
                graph_edges.append({
                    "data": {
                        "source": f"gene:{gene}",
                        "target": f"disease:{disease_id}",
                        "label": "associated",
                        "weight": max(1.0, score * 5),
                        "type": "disease-gene",
                    }
                })

            for drug in [item for item in gene_evidence if item.predicate == "known_drug"]:
                name = str(drug.value)
                chembl = str(drug.qualifiers.get("chembl_id") or name)
                graph_nodes[f"drug:{chembl}"] = {
                    "data": {"id": f"drug:{chembl}", "label": name, "type": "drug"}
                }
                graph_edges.append({
                    "data": {
                        "source": f"drug:{chembl}",
                        "target": f"gene:{gene}",
                        "label": "targets",
                        "weight": max(1, int(drug.qualifiers.get("phase") or drug.qualifiers.get("max_clinical_stage") or 1)),
                        "type": "drug-gene",
                    }
                })

        profiles = {gene: set() for gene in genes}
        for disease, disease_genes in disease_to_genes.items():
            for gene in disease_genes:
                profiles.setdefault(gene, set()).add(disease)

        parent = {gene: gene for gene in genes}

        def find(value: str) -> str:
            while parent[value] != value:
                parent[value] = parent[parent[value]]
                value = parent[value]
            return value

        def union(a: str, b: str) -> None:
            root_a, root_b = find(a), find(b)
            if root_a != root_b:
                parent[root_b] = root_a

        for index, gene_a in enumerate(genes):
            for gene_b in genes[index + 1:]:
                profile_a, profile_b = profiles.get(gene_a, set()), profiles.get(gene_b, set())
                if profile_a and profile_b and len(profile_a & profile_b) / len(profile_a | profile_b) >= 0.25:
                    union(gene_a, gene_b)

        cluster_map: dict[str, list[str]] = defaultdict(list)
        for gene in genes:
            cluster_map[find(gene)].append(gene)
        clusters = [
            {
                "id": index + 1,
                "genes": cluster_genes,
                "description": "Genes grouped heuristically by shared Open Targets disease-association profiles",
            }
            for index, cluster_genes in enumerate(cluster_map.values())
        ]

        disease_summary = []
        for disease, disease_genes in disease_to_genes.items():
            scores = disease_to_scores.get(disease, [])
            disease_summary.append({
                "term": disease,
                "genes": sorted(disease_genes),
                "supportCount": len(disease_genes),
                "meanAssociationScore": sum(scores) / len(scores) if scores else 0.0,
            })
        disease_summary.sort(key=lambda item: (-item["supportCount"], -item["meanAssociationScore"], item["term"]))

        explanation = f"Analyzed {len(genes)} gene(s) using live Open Targets evidence."
        if query:
            explanation += f" The gene set was restricted to retrieved associations with {query}."
        if paper_summary:
            explanation += " Results can be continued in research chat together with the uploaded paper context."

        return {
            "genes": genes,
            "paperSummary": paper_summary,
            "explanation": explanation,
            "tableData": {
                "headers": ["Gene Symbol", "Gene Name", "Ensembl ID", "Avg. Association Score", "Top Associated Diseases [EFO ID] [Score]"],
                "rows": gene_rows,
                "caption": f"Gene Associations for {query}" if query else "Gene Details",
            },
            "clusters": clusters,
            "diseaseEvidenceSummary": disease_summary[:25],
            "enrichmentResults": [],
            "networkData": list(graph_nodes.values()) + graph_edges,
            "evidence": [item.model_dump() for item in evidence],
        }
