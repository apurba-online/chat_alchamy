from __future__ import annotations

import os
from contextlib import asynccontextmanager
from io import BytesIO

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .biomedical import BiomedicalService
from .files import export_xlsx_bytes, extract_document_text, parse_tabular_bytes
from .llm import LLMClient, fallback_title
from .models import (
    BiomedicalAnalyzeRequest,
    BiomedicalExtractRequest,
    BiomedicalExtractResponse,
    ChatRequest,
    QueryRequest,
    QueryResponse,
    TablePayload,
    TitleRequest,
)
from .reasoning import ChatAlchemyEngine

MAX_DATA_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_DOCUMENT_UPLOAD_BYTES = 25 * 1024 * 1024
LIVE_SOURCE_LABELS = [
    "RxNorm/RxNav",
    "DailyMed",
    "Drugs@FDA/openFDA",
    "ClinicalTrials.gov",
    "ChEMBL",
    "Open Targets",
    "PubChem",
]

engine: ChatAlchemyEngine | None = None
biomedical: BiomedicalService | None = None
llm: LLMClient | None = None


def _translate_upstream_error(exc: httpx.HTTPError) -> None:
    request = getattr(exc, "request", None)
    request_url = str(request.url) if request is not None else ""
    status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None

    if "api.openai.com" in request_url and (
        isinstance(exc, httpx.RequestError)
        or status in {401, 403, 404, 408, 409, 429, 500, 502, 503, 504}
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "The conversational model is temporarily unavailable. "
                "Live structured biomedical evidence workflows remain available."
            ),
        ) from exc
    raise exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine, biomedical, llm
    llm = LLMClient()
    engine = ChatAlchemyEngine(llm=llm)
    biomedical = BiomedicalService(llm, engine.sources["opentargets"])
    yield
    if engine is not None:
        await engine.close()
    engine = None
    biomedical = None
    llm = None


app = FastAPI(
    title="ChatAlchemy",
    version="1.2.0",
    description="Evidence-first research workspace over live biomedical data sources.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://chat-alchemy.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "system": "ChatAlchemy-Live",
        "version": app.version,
        "environment": os.getenv("VERCEL_ENV") or "local",
        "deployment_commit": os.getenv("VERCEL_GIT_COMMIT_SHA"),
        "deployment_branch": os.getenv("VERCEL_GIT_COMMIT_REF"),
        "local_pharma_database": False,
        "server_llm_configured": bool(llm and llm.available),
        "model": llm.model if llm and llm.available else None,
        "research_use_only": True,
        "live_sources": LIVE_SOURCE_LABELS,
        "capabilities": [
            "live biomedical evidence retrieval",
            "deterministic cross-source joins",
            "claim-to-evidence link validation",
            "context-aware evidence relation analysis",
            "CSV/XLS/XLSX analysis",
            "PDF/TXT biomedical analysis",
            "gene-disease-drug evidence networks",
        ],
    }


@app.post("/api/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    if engine is None:
        raise RuntimeError("Engine not initialized")
    try:
        return await engine.answer(req.question, req.max_results, req.conversation, req.user_evidence)
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        _translate_upstream_error(exc)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if engine is None:
        raise RuntimeError("Engine not initialized")
    question = next((m.get("content", "") for m in reversed(req.messages) if m.get("role") == "user"), "")
    user_evidence = []
    if req.uploaded_context:
        user_evidence = [{"subject": "uploaded data", "predicate": "uploaded_context", "value": req.uploaded_context}]
    try:
        return (await engine.answer(question, conversation=req.messages, user_evidence=user_evidence)).model_dump()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        _translate_upstream_error(exc)


@app.post("/api/title")
async def title(req: TitleRequest):
    if llm and llm.available:
        try:
            text = await llm.text(
                "Generate a concise 2-4 word chat title. Return only the title, no punctuation.",
                req.text,
                max_output_tokens=30,
            )
            return {"title": text.strip()[:80] or fallback_title(req.text)}
        except Exception:
            pass
    return {"title": fallback_title(req.text)}


@app.post("/api/biomedical/extract", response_model=BiomedicalExtractResponse)
async def biomedical_extract(req: BiomedicalExtractRequest):
    if biomedical is None:
        raise RuntimeError("Biomedical service not initialized")
    try:
        return await biomedical.extract_document(req.text, req.filename)
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        _translate_upstream_error(exc)


@app.post("/api/biomedical/upload", response_model=BiomedicalExtractResponse)
async def biomedical_upload(file: UploadFile = File(...)):
    if biomedical is None:
        raise RuntimeError("Biomedical service not initialized")
    filename = file.filename or "document"
    content = await file.read(MAX_DOCUMENT_UPLOAD_BYTES + 1)
    if len(content) > MAX_DOCUMENT_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds the 25 MB upload limit")
    try:
        text = extract_document_text(filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not extract document text: {exc}") from exc
    if not text.strip():
        raise HTTPException(status_code=422, detail="No readable text was found in the uploaded document")
    try:
        return await biomedical.extract_document(text, filename)
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        _translate_upstream_error(exc)


@app.post("/api/biomedical/analyze")
async def biomedical_analyze(req: BiomedicalAnalyzeRequest):
    if biomedical is None:
        raise RuntimeError("Biomedical service not initialized")
    return await biomedical.analyze(req.genes, req.query, req.paper_summary)


@app.post("/api/data/parse")
async def data_parse(file: UploadFile = File(...)):
    filename = file.filename or "data"
    content = await file.read(MAX_DATA_UPLOAD_BYTES + 1)
    if len(content) > MAX_DATA_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Data file exceeds the 15 MB upload limit")
    try:
        rows = parse_tabular_bytes(filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse uploaded data: {exc}") from exc
    if not rows:
        raise HTTPException(status_code=422, detail="No valid rows were found in the uploaded data")
    return {"filename": filename, "rows": rows}


@app.post("/api/data/export_xlsx")
async def data_export_xlsx(table: TablePayload):
    try:
        payload = export_xlsx_bytes(table.headers, table.rows)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not create Excel export: {exc}") from exc
    headers = {"Content-Disposition": 'attachment; filename="chatalchemy-results.xlsx"'}
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
