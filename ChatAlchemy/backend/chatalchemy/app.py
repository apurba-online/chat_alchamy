from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from io import BytesIO

import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

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

# Vercel Functions enforce a 4.5 MB request/response payload ceiling. Keep
# direct multipart uploads below that platform boundary so ChatAlchemy can
# return its own predictable validation response. Larger-file support should
# use direct-to-object-storage uploads rather than routing bytes through the
# Python Function.
MAX_DIRECT_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_DATA_UPLOAD_BYTES = MAX_DIRECT_UPLOAD_BYTES
MAX_DOCUMENT_UPLOAD_BYTES = MAX_DIRECT_UPLOAD_BYTES
MAX_API_CONCURRENCY = max(1, min(64, int(os.getenv("CHATALCHEMY_MAX_CONCURRENCY", "10"))))
OVERLOAD_ACQUIRE_TIMEOUT_SECONDS = max(
    0.05,
    min(5.0, float(os.getenv("CHATALCHEMY_OVERLOAD_WAIT_SECONDS", "1.0"))),
)
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")
BIOMEDICAL_ID_RE = re.compile(
    r"^(?:EFO|MONDO|OTAR|Orphanet|HP|NCIT|DOID)_[A-Za-z0-9]+$",
    re.IGNORECASE,
)

logger = logging.getLogger("chatalchemy.api")
if not logger.handlers:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
api_capacity = asyncio.Semaphore(MAX_API_CONCURRENCY)

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


def _request_id(request: Request) -> str:
    candidate = (request.headers.get("x-request-id") or "").strip()
    if REQUEST_ID_RE.fullmatch(candidate):
        return candidate
    return uuid.uuid4().hex


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
    expose_headers=["X-Request-ID", "Retry-After"],
)


@app.middleware("http")
async def operational_guard(request: Request, call_next):
    """Add request correlation and per-instance overload protection.

    This protects one serverless instance from excessive concurrent expensive
    source/model calls. It is intentionally not described as a global user/IP
    rate limiter; global abuse controls belong at Vercel Firewall/WAF or another
    shared edge/store layer.
    """
    request_id = _request_id(request)
    started = time.perf_counter()
    acquired = False
    status_code = 500
    try:
        if request.url.path.startswith("/api/") and request.url.path != "/api/health":
            try:
                await asyncio.wait_for(api_capacity.acquire(), timeout=OVERLOAD_ACQUIRE_TIMEOUT_SECONDS)
                acquired = True
            except TimeoutError:
                status_code = 503
                return JSONResponse(
                    status_code=503,
                    content={"detail": "ChatAlchemy is temporarily at capacity. Please retry shortly."},
                    headers={"Retry-After": "1", "X-Request-ID": request_id},
                )

        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        if acquired:
            api_capacity.release()
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "deployment_commit": os.getenv("VERCEL_GIT_COMMIT_SHA"),
                },
                sort_keys=True,
            )
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
        "direct_upload_limit_bytes": MAX_DIRECT_UPLOAD_BYTES,
        "instance_concurrency_limit": MAX_API_CONCURRENCY,
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
        raise HTTPException(status_code=413, detail="Document exceeds the 4 MB direct upload limit")
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
    try:
        return await biomedical.analyze(req.genes, req.query, req.paper_summary)
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        _translate_upstream_error(exc)


@app.get("/api/biomedical/disease")
@app.get("/api/biomedical/disease/{efo_id}")
async def biomedical_disease_details(efo_id: str):
    if engine is None:
        raise RuntimeError("Engine not initialized")
    if not BIOMEDICAL_ID_RE.fullmatch(efo_id):
        raise HTTPException(status_code=400, detail="Invalid Open Targets disease identifier")
    source = engine.sources["opentargets"]
    try:
        result = await source.disease_details(efo_id, max_results=8)
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        _translate_upstream_error(exc)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail="Open Targets could not return details for this disease record right now.",
        ) from exc
    if not result:
        raise HTTPException(status_code=404, detail="Disease record was not found in Open Targets")
    return result


@app.get("/api/biomedical/compound")
@app.get("/api/biomedical/compound/{name}")
async def biomedical_compound_details(name: str):
    if engine is None:
        raise RuntimeError("Engine not initialized")
    clean_name = name.strip()
    if not clean_name or len(clean_name) > 160:
        raise HTTPException(status_code=400, detail="Invalid compound name")
    source = engine.sources["pubchem"]
    try:
        evidence = await source.compound(clean_name)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=(
                    "No PubChem structure record was found for this candidate name. "
                    "The Open Targets drug record is still available."
                ),
            ) from exc
        _translate_upstream_error(exc)
    except httpx.RequestError as exc:
        _translate_upstream_error(exc)
    if not evidence:
        raise HTTPException(status_code=404, detail="Compound record was not found in PubChem")
    item = evidence[0]
    value = item.value if isinstance(item.value, dict) else {}
    return {
        "name": clean_name,
        "cid": value.get("cid"),
        "iupac": value.get("iupac_name"),
        "smiles": value.get("canonical_smiles"),
        "source": item.source,
        "source_url": item.source_url,
    }


@app.post("/api/data/parse")
async def data_parse(file: UploadFile = File(...)):
    filename = file.filename or "data"
    content = await file.read(MAX_DATA_UPLOAD_BYTES + 1)
    if len(content) > MAX_DATA_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Data file exceeds the 4 MB direct upload limit")
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
