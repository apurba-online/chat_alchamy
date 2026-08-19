from __future__ import annotations
import re
from io import BytesIO
from fastapi import FastAPI, HTTPException, UploadFile, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from .models import QueryRequest, QueryResponse, ChatRequest, BiomedicalTextRequest, SuggestionRequest, LLMRequest, GeneListRequest
from .reasoning.engine import ReasoningEngine
from .generation.server_llm import ServerLLM
from .sources.gprofiler import GProfilerSource
from .files import parse_tabular_bytes, export_xlsx_bytes, extract_document_text
from .biomedical_service import BiomedicalService

app=FastAPI(title='ChatAlchemy-Live',version='2.1.0')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_credentials=False,allow_methods=['GET','POST'],allow_headers=['*'])
engine=ReasoningEngine();llm=ServerLLM();gprofiler=GProfilerSource();biomedical=BiomedicalService()

@app.get('/api/health')
async def health():
    return {'status':'ok','system':'ChatAlchemy-Live','local_pharma_database':False,'evidence_state':True,'server_llm_configured':llm.available,'publication_harness':True}

async def _standalone_question(question:str,conversation:list[dict[str,str]])->str:
    if not conversation or not llm.available:return question
    low=question.lower();ambiguous=any(x in low for x in [' those ',' them',' ones',' these ',' that ',' it ','same ','only ']) or len(question.split())<5
    if not ambiguous:return question
    try:
        context='\n'.join(f"{m.get('role')}: {m.get('content','')}" for m in conversation[-8:])
        out=await llm.complete([{'role':'user','content':f"Conversation:\n{context}\n\nLatest question: {question}"}],system='Rewrite the latest question as one standalone biomedical query. Preserve all constraints from the conversation. Return only the rewritten question.',temperature=0)
        return out.strip() or question
    except Exception:return question

@app.post('/api/query',response_model=QueryResponse)
async def query(request:QueryRequest):
    return await engine.answer(await _standalone_question(request.question,request.conversation),request.max_results,request.user_evidence)

@app.post('/api/chat')
async def chat(request:ChatRequest):
    if not request.messages:raise HTTPException(400,'messages cannot be empty')
    last_user=next((m.get('content','') for m in reversed(request.messages) if m.get('role')=='user'),'')
    grounded=await engine.answer(last_user,request.max_results)
    if grounded.evidence:return grounded.model_dump(mode='json')
    if not llm.available:return {'answer':'I could not build a supported live-source answer for this question, and the server-side language model is not configured.','supported_claim_rate':0.0,'warnings':grounded.warnings,'evidence':[],'table':None,'chart':None,'plan':{'intent':'general'}}
    context='\n\n'.join(m.get('content','') for m in request.messages if m.get('role')=='system')
    if request.uploaded_context:context=(context+'\n\n'+request.uploaded_context).strip()
    system='You are ChatAlchemy, a biomedical and pharmaceutical research assistant. Use supplied user-data context when present. Never imply general model knowledge came from a live database. Be concise and use markdown.'+(f'\n\nUSER DATA CONTEXT:\n{context}' if context else '')
    conversational=[m for m in request.messages[-12:] if m.get('role') in {'user','assistant'}]
    answer=await llm.complete(conversational,system=system,temperature=0.1)
    return {'answer':answer,'supported_claim_rate':0.0,'warnings':grounded.warnings,'evidence':[],'table':None,'chart':None,'plan':{'intent':'general'}}

@app.post('/api/title')
async def title(payload:dict=Body(...)):
    text=str(payload.get('text') or '').strip()
    if not text:return {'title':'New Chat'}
    if llm.available:
        try:
            out=await llm.complete([{'role':'user','content':text[:1200]}],system='Return only a concise 2-4 word research chat title with no punctuation.',temperature=0.2);clean=re.sub(r'[^A-Za-z0-9 -]','',out).strip();return {'title':' '.join(clean.split()[:4]) or 'New Chat'}
        except Exception:pass
    return {'title':' '.join(re.findall(r'[A-Za-z0-9-]+',text)[:4]) or 'New Chat'}

@app.post('/api/llm')
async def llm_proxy(request:LLMRequest):
    if not llm.available:raise HTTPException(503,'Server-side language model is not configured')
    system='\n\n'.join(m.get('content','') for m in request.messages if m.get('role')=='system') or 'You are a biomedical research assistant.';conv=[m for m in request.messages if m.get('role') in {'user','assistant'}]
    return {'content':await llm.complete(conv,system=system,temperature=request.temperature)}

async def _extract(text:str):
    if llm.available:
        data=await llm.extract_biomedical_entities(text);return {'summary':data.get('summary',''),'genes':sorted({str(x).upper() for x in data.get('genes',[]) if x}),'suggested_diseases':sorted({str(x) for x in (data.get('suggested_diseases') or data.get('diseases') or []) if x})}
    clean=' '.join(text.split());genes=sorted({g for g in re.findall(r'\b[A-Z][A-Z0-9-]{1,10}\b',clean) if g not in {'DNA','RNA','PCR','FDA','WHO','USA','AND','THE'}})[:50]
    return {'summary':' '.join(re.split(r'(?<=[.!?])\s+',clean)[:5])[:1800],'genes':genes,'suggested_diseases':[]}

@app.post('/api/biomedical/extract')
async def biomedical_extract(request:BiomedicalTextRequest):return await _extract(request.text)

@app.post('/api/biomedical/upload')
async def biomedical_upload(file:UploadFile=File(...)):
    content=await file.read()
    try:text=extract_document_text(file.filename or 'document',content)
    except ValueError as exc:raise HTTPException(400,str(exc))
    if not text:raise HTTPException(400,'No readable text was extracted from the document')
    return await _extract(text)

@app.post('/api/biomedical/analyze')
async def biomedical_analyze(payload:dict=Body(...)):
    try:return await biomedical.analyze(payload.get('genes') or [],payload.get('query'),payload.get('suggested_diseases') or [],payload.get('paper_summary'))
    except Exception as exc:raise HTTPException(502,f'Biomedical live-source analysis failed: {exc}')

@app.post('/api/biomedical/enrichment')
async def biomedical_enrichment(request:GeneListRequest):
    genes=sorted({g.strip().upper() for g in request.genes if g.strip()})
    if not genes:return {'results':[]}
    results,latency=await gprofiler.enrich(genes);return {'results':results,'source':'g:Profiler','latency_ms':latency}

@app.post('/api/biomedical/suggestions')
async def biomedical_suggestions(request:SuggestionRequest):return {'questions':await llm.suggest_questions(request.context) if llm.available else []}

@app.post('/api/data/parse')
async def data_parse(file:UploadFile=File(...)):
    content=await file.read()
    try:rows=parse_tabular_bytes(file.filename or 'data.csv',content)
    except ValueError as exc:raise HTTPException(400,str(exc))
    return {'filename':file.filename or 'data','rows':rows}

@app.post('/api/data/export_xlsx')
async def data_export(payload:dict=Body(...)):
    headers=[str(x) for x in payload.get('headers') or []];rows=payload.get('rows') or []
    if not headers:raise HTTPException(400,'headers are required')
    data=export_xlsx_bytes(headers,rows)
    return StreamingResponse(BytesIO(data),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename="chatalchemy-results.xlsx"'})
