from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import httpx

from chatalchemy.files import extract_document_text
from chatalchemy.llm import LLMClient
from chatalchemy.biomedical import BiomedicalService
from chatalchemy.sources.opentargets import OpenTargetsSource
from chatalchemy.sources.pubchem import PubChemSource

PDF_URL = "https://link.springer.com/content/pdf/10.1007/s13238-016-0353-7.pdf"
EXPECTED_SHA256 = "252803c27fcd7e11754c1f6330c5247168d1db2ccbf1b1dec94f33b614b5f131"
OUT = Path("benchmark/document-case-study-trpv1.json")


async def main() -> None:
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(PDF_URL)
        response.raise_for_status()
        pdf = response.content

    sha256 = hashlib.sha256(pdf).hexdigest()
    if sha256 != EXPECTED_SHA256:
        raise RuntimeError(f"Downloaded PDF checksum mismatch: {sha256}")

    text = extract_document_text("Example_Article.pdf", pdf)
    llm = LLMClient()
    if not llm.available:
        raise RuntimeError("OPENAI_API_KEY is required for the production document extractor")

    opentargets = OpenTargetsSource()
    pubchem = PubChemSource()
    service = BiomedicalService(llm, opentargets)

    extraction = await service.extract_document(text, "Example_Article.pdf")
    selected_genes = [g for g in extraction.genes if g == "TRPV1"]
    if not selected_genes:
        selected_genes = extraction.genes[:5]

    analysis = await service.analyze(selected_genes, None, extraction.summary)
    capsaicin = await pubchem.compound("capsaicin")

    payload = {
        "pdf": {
            "url": PDF_URL,
            "sha256": sha256,
            "bytes": len(pdf),
            "text_chars": len(text),
        },
        "extraction": extraction.model_dump(),
        "selected_genes": selected_genes,
        "analysis": analysis,
        "capsaicin": [item.model_dump() for item in capsaicin],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    print("CASE_STUDY_PDF_SHA256", sha256)
    print("CASE_STUDY_EXTRACTED_GENES", extraction.genes)
    print("CASE_STUDY_SUGGESTED_DISEASES", extraction.suggested_diseases)
    print("CASE_STUDY_SELECTED_GENES", selected_genes)
    print("CASE_STUDY_TABLE_ROWS", len(analysis.get("tableData", {}).get("rows", [])))
    print("CASE_STUDY_NETWORK_ELEMENTS", len(analysis.get("networkData", [])))
    print("CASE_STUDY_EVIDENCE_ITEMS", len(analysis.get("evidence", [])))
    if capsaicin:
        print("CASE_STUDY_CAPSAICIN", capsaicin[0].model_dump())

    await opentargets.close()
    await pubchem.close()


if __name__ == "__main__":
    asyncio.run(main())
