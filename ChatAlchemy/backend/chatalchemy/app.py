from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .biomedical import BiomedicalService
from .llm import LLMClient,fallback_title
from .models import BiomedicalAnalyzeRequest,BiomedicalExtractRequest,BiomedicalExtractResponse,ChatRequest,QueryRequest,QueryResponse,TitleRequest
from .reasoning import ChatAlchemyEngine
engine=None;biomedical=None;llm=None
@asynccontextmanager
async def lifespan(app:FastAPI):
    global engine,biomedical,llm
    llm=LLMClient();engine=ChatAlchemyEngine(llm=llm);biomedical=BiomedicalService(llm,engine.sources["opentargets"]);yield
    if engine:await engine.close()
    engine=None;biomedical=None;llm=None
app=FastAPI(title="ChatAlchemy",version="1.0.0",description="Provenance-preserving reasoning over live biomedical evidence.",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173","http://127.0.0.1:5173","https://chat-alchemy.vercel.app"],allow_credentials=False,allow_methods=["GET","POST","OPTIONS"],allow_headers=["*"])
@app.get("/api/health")
async def health():return {"status":"ok","system":"ChatAlchemy-Live","local_pharma_database":False,"server_llm_configured":bool(llm and llm.available)}
@app.post("/api/query",response_model=QueryResponse)
async def query(req:QueryRequest):
    if engine is None:raise RuntimeError("Engine not initialized")
    return await engine.answer(req.question,req.max_results,req.conversation,req.user_evidence)
@app.post("/api/chat")
async def chat(req:ChatRequest):
    if engine is None:raise RuntimeError("Engine not initialized")
    question=next((m.get("content","") for m in reversed(req.messages) if m.get("role")=="user"),"");user_evidence=[]
    if req.uploaded_context:user_evidence=[{"subject":"uploaded data","predicate":"uploaded_context","value":req.uploaded_context}]
    return (await engine.answer(question,conversation=req.messages,user_evidence=user_evidence)).model_dump()
@app.post("/api/title")
async def title(req:TitleRequest):
    if llm and llm.available:
        try:
            text=await llm.text("Generate a concise 2-4 word chat title. Return only the title, no punctuation.",req.text,max_output_tokens=30);return {"title":text.strip()[:80] or fallback_title(req.text)}
        except Exception:pass
    return {"title":fallback_title(req.text)}
@app.post("/api/biomedical/extract",response_model=BiomedicalExtractResponse)
async def biomedical_extract(req:BiomedicalExtractRequest):
    if biomedical is None:raise RuntimeError("Biomedical service not initialized")
    return await biomedical.extract_document(req.text,req.filename)
@app.post("/api/biomedical/analyze")
async def biomedical_analyze(req:BiomedicalAnalyzeRequest):
    if biomedical is None:raise RuntimeError("Biomedical service not initialized")
    return await biomedical.analyze(req.genes,req.query,req.paper_summary)
