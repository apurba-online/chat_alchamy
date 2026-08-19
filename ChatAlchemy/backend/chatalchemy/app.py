from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import QueryRequest, QueryResponse, ChatRequest, ChatResponse, BiomedicalTextRequest, SuggestionRequest, LLMRequest, GeneListRequest
from .reasoning.engine import ReasoningEngine
from .generation.server_llm import ServerLLM
from .sources.gprofiler import GProfilerSource

app = FastAPI(title="ChatAlchemy-Live", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])
engine = ReasoningEngine(); llm = ServerLLM(); gprofiler = GProfilerSource()

@app.get("/api/health")
async def health():
    return {"status": "ok", "system": "ChatAlchemy-Live", "local_pharma_database": False, "evidence_state": True, "server_llm_configured": llm.available}

@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    return await engine.answer(request.question, request.max_results, request.user_evidence)

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.messages: raise HTTPException(400, "messages cannot be empty")
    last_user = next((m.get("content", "") for m in reversed(request.messages) if m.get("role") == "user"), "")
    grounded = await engine.answer(last_user, request.max_results)
    if grounded.evidence:
        source_lines=[]; seen=set()
        for e in grounded.evidence:
            key=(e.source,e.source_record_id)
            if key in seen: continue
            seen.add(key)
            if e.source_url: source_lines.append(f"- {e.source}: {e.source_url}")
        content = grounded.answer + ("\n\n### Sources\n" + "\n".join(source_lines[:12]) if source_lines else "")
        return ChatResponse(content=content, evidence=grounded.evidence, supported_claim_rate=grounded.supported_claim_rate, warnings=grounded.warnings)
    if not llm.available:
        return ChatResponse(content="I could not build a supported live-source answer for this question, and the server-side language model is not configured.", warnings=grounded.warnings)
    base_system = "You are ChatAlchemy, a biomedical and pharmaceutical research assistant. Use user-provided context when present. Never pretend that general model knowledge came from a live database. Be concise and use markdown when useful."
    supplied_context = "\n\n".join(m.get("content", "") for m in request.messages if m.get("role") == "system")
    system = base_system + (f"\n\nUSER DATA CONTEXT:\n{supplied_context}" if supplied_context else "")
    conversational = [m for m in request.messages[-12:] if m.get("role") in {"user", "assistant"}]
    return ChatResponse(content=await llm.complete(conversational, system=system, temperature=0.1), warnings=grounded.warnings)

@app.post("/api/llm")
async def llm_proxy(request: LLMRequest):
    if not llm.available: raise HTTPException(503, "Server-side language model is not configured")
    system_parts = [m.get("content", "") for m in request.messages if m.get("role") == "system"]; conversational = [m for m in request.messages if m.get("role") in {"user", "assistant"}]
    return {"content": await llm.complete(conversational, system="\n\n".join(system_parts) or "You are a biomedical research assistant.", temperature=request.temperature)}

@app.post("/api/biomedical/enrichment")
async def biomedical_enrichment(request: GeneListRequest):
    genes = sorted({g.strip().upper() for g in request.genes if g.strip()})
    if not genes: return {"results": []}
    results, latency = await gprofiler.enrich(genes); return {"results": results, "source": "g:Profiler", "latency_ms": latency}

@app.post("/api/biomedical/extract")
async def biomedical_extract(request: BiomedicalTextRequest):
    if not llm.available: raise HTTPException(503, "Server-side language model is not configured")
    return await llm.extract_biomedical_entities(request.text)

@app.post("/api/biomedical/suggestions")
async def biomedical_suggestions(request: SuggestionRequest):
    if not llm.available: return {"questions": []}
    return {"questions": await llm.suggest_questions(request.context)}
