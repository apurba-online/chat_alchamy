from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field

def utc_now()->datetime:return datetime.now(timezone.utc)
class Entity(BaseModel):
    text:str; type:str='unknown'; canonical_name:str|None=None; identifiers:dict[str,str]=Field(default_factory=dict)
class Operation(BaseModel):
    source:str; action:str; arguments:dict[str,Any]=Field(default_factory=dict)
class QueryPlan(BaseModel):
    question:str; intent:str; entities:list[Entity]=Field(default_factory=list); filters:dict[str,Any]=Field(default_factory=dict); operations:list[Operation]=Field(default_factory=list); final_operation:str='list'
class EvidenceItem(BaseModel):
    id:str; source:str; source_record_id:str|None=None; source_url:str|None=None; subject:str; predicate:str; value:Any; context:dict[str,Any]=Field(default_factory=dict); canonical_subject:str|None=None; identifiers:dict[str,str]=Field(default_factory=dict); retrieved_at:datetime=Field(default_factory=utc_now); confidence:float=1.0; raw:dict[str,Any]|None=None
class ConflictAssessment(BaseModel):
    evidence_ids:list[str]; relation:Literal['agreement','complementary','context_difference','conflict']; reason:str
class Claim(BaseModel):
    text:str; support_evidence_ids:list[str]=Field(default_factory=list); verified:bool=False
class SourceTrace(BaseModel):
    source:str; operation:str; success:bool; latency_ms:float; record_count:int=0; error:str|None=None
class QueryRequest(BaseModel):
    question:str; max_results:int=Field(default=20,ge=1,le=100); conversation:list[dict[str,str]]=Field(default_factory=list); user_evidence:list[dict[str,Any]]=Field(default_factory=list)
class QueryResponse(BaseModel):
    answer:str; plan:QueryPlan; evidence:list[EvidenceItem]; conflicts:list[ConflictAssessment]=Field(default_factory=list); claims:list[Claim]=Field(default_factory=list); supported_claim_rate:float=0.0; traces:list[SourceTrace]=Field(default_factory=list); warnings:list[str]=Field(default_factory=list); abstained:bool=False
class ChatRequest(BaseModel):
    messages:list[dict[str,str]]; max_results:int=Field(default=20,ge=1,le=100); uploaded_context:str|None=None
class ChatResponse(BaseModel):
    content:str; role:str='assistant'; evidence:list[EvidenceItem]=Field(default_factory=list); supported_claim_rate:float=0.0; warnings:list[str]=Field(default_factory=list)
class BiomedicalTextRequest(BaseModel):text:str
class SuggestionRequest(BaseModel):context:str
class LLMRequest(BaseModel):
    messages:list[dict[str,str]]; temperature:float=0.0; max_tokens:int|None=None; response_format:str|None=None
class GeneListRequest(BaseModel):genes:list[str]
