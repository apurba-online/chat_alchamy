from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from pathlib import Path

import httpx

from chatalchemy.files import extract_document_text

PDF_URL = "https://link.springer.com/content/pdf/10.1007/s13238-016-0353-7.pdf"
PRODUCTION = "https://chat-alchemy.vercel.app"
EXPECTED_SHA256 = "252803c27fcd7e11754c1f6330c5247168d1db2ccbf1b1dec94f33b614b5f131"
OUT = Path("benchmark/document-case-study-trpv1.json")


def elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


async def main() -> None:
    timings: dict[str, float] = {}
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        started = time.perf_counter()
        response = await client.get(PDF_URL)
        response.raise_for_status()
        pdf = response.content
        timings["download_pdf_ms"] = elapsed_ms(started)

        sha256 = hashlib.sha256(pdf).hexdigest()
        if sha256 != EXPECTED_SHA256:
            raise RuntimeError(f"Downloaded PDF checksum mismatch: {sha256}")

        # This is the same PDF the user attached in ChatGPT; the checksum above
        # was computed from /mnt/data/Example_Article.pdf before this run.
        text = extract_document_text("Example_Article.pdf", pdf)
        normalized = " ".join(text.split())
        document_audit = {
            "title_present": "Understand spiciness: mechanism of TRPV1 channel activation by capsaicin".lower() in normalized.lower(),
            "trpv1_present": bool(re.search(r"\bTRPV1\b", normalized)),
            "capsaicin_present": bool(re.search(r"\bcapsaicin\b", normalized, re.I)),
            "pain_present": bool(re.search(r"\bpain\b", normalized, re.I)),
            "doi_present": "10.1007/s13238-016-0353-7" in normalized,
        }

        started = time.perf_counter()
        upload = await client.post(
            f"{PRODUCTION}/api/biomedical/upload",
            files={"file": ("Example_Article.pdf", pdf, "application/pdf")},
        )
        timings["production_document_upload_ms"] = elapsed_ms(started)
        upload.raise_for_status()
        extraction = upload.json()

        genes = [str(g).upper() for g in extraction.get("genes") or []]
        if "TRPV1" not in genes:
            raise RuntimeError(f"Production extractor did not return TRPV1: {genes}")

        # Reproduce Document Lab's automatic behavior: after upload it analyzes
        # every unique gene extracted from the document.
        started = time.perf_counter()
        analyze = await client.post(
            f"{PRODUCTION}/api/biomedical/analyze",
            json={
                "genes": genes,
                "query": None,
                "suggested_diseases": extraction.get("suggested_diseases") or [],
                "paper_summary": extraction.get("summary"),
            },
        )
        timings["production_live_analysis_ms"] = elapsed_ms(started)
        analyze.raise_for_status()
        analysis = analyze.json()

        started = time.perf_counter()
        capsaicin_response = await client.get(
            f"{PRODUCTION}/api/biomedical/compound",
            params={"name": "capsaicin"},
        )
        timings["production_capsaicin_lookup_ms"] = elapsed_ms(started)
        capsaicin_response.raise_for_status()
        capsaicin = capsaicin_response.json()

        disease_items = [
            item for item in analysis.get("evidence") or []
            if item.get("predicate") == "gene_disease_association"
            and (item.get("qualifiers") or {}).get("efo_id")
        ]
        disease_items.sort(
            key=lambda item: float((item.get("qualifiers") or {}).get("score") or 0),
            reverse=True,
        )
        disease_details: list[dict] = []
        seen: set[str] = set()
        for item in disease_items:
            disease_id = str((item.get("qualifiers") or {}).get("efo_id") or "")
            if not disease_id or disease_id in seen:
                continue
            seen.add(disease_id)
            detail_response = await client.get(
                f"{PRODUCTION}/api/biomedical/disease",
                params={"efo_id": disease_id},
            )
            disease_details.append({
                "id": disease_id,
                "association": item,
                "status": detail_response.status_code,
                "detail": detail_response.json() if detail_response.headers.get("content-type", "").startswith("application/json") else detail_response.text[:500],
            })
            if len(disease_details) >= 3:
                break

        payload = {
            "case_study_schema": "ChatAlchemyDocumentCaseStudy/v1",
            "production_base": PRODUCTION,
            "pdf": {
                "url": PDF_URL,
                "sha256": sha256,
                "bytes": len(pdf),
                "text_chars": len(text),
            },
            "document_audit": document_audit,
            "timings_ms": timings,
            "extraction": extraction,
            "analysis": analysis,
            "top_disease_details": disease_details,
            "capsaicin": capsaicin,
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")

    print("CASE_STUDY_PDF_SHA256", sha256)
    print("CASE_STUDY_DOCUMENT_AUDIT", document_audit)
    print("CASE_STUDY_EXTRACTED_GENES", extraction.get("genes"))
    print("CASE_STUDY_SUGGESTED_DISEASES", extraction.get("suggested_diseases"))
    print("CASE_STUDY_TABLE_ROWS", len((analysis.get("tableData") or {}).get("rows") or []))
    print("CASE_STUDY_NETWORK_ELEMENTS", len(analysis.get("networkData") or []))
    print("CASE_STUDY_EVIDENCE_ITEMS", len(analysis.get("evidence") or []))
    print("CASE_STUDY_TOP_DISEASE_IDS", [item["id"] for item in disease_details])
    print("CASE_STUDY_CAPSAICIN", capsaicin)
    print("CASE_STUDY_TIMINGS_MS", timings)


if __name__ == "__main__":
    asyncio.run(main())
