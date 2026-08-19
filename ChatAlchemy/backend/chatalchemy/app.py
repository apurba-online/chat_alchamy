from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .models import QueryRequest, QueryResponse
from .reasoning import ChatAlchemyEngine

engine: ChatAlchemyEngine | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = ChatAlchemyEngine()
    yield
    await engine.close()
    engine = None

app = FastAPI(title="ChatAlchemy-Live API", version="0.1.0", description="Query-time reasoning over live pharmaceutical APIs without a local pharmaceutical database.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "ok", "system": "ChatAlchemy-Live", "local_pharma_database": False}

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    if engine is None:
        raise RuntimeError("Engine not initialized")
    return await engine.answer(request.question, max_results=request.max_results)
