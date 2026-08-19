from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class Entity(BaseModel):
    text: str
    type: Literal["drug", "condition", "target", "trial", "unknown"]
    canonical_name: str | None = None
    ids: dict[str, str] = Field(default_factory=dict)


class Operation(BaseModel):
    source: str
    action: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class QueryPlan(BaseModel):
    question: str
    intent: Literal["identity", "label", "approval", "trials", "target_drugs", "cross_source", "unknown"]
    entities: list[Entity] = Field(default_factory=list)
    operations: list[Operation] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    final_operation: str = "synthesize"


class EvidenceItem(BaseModel):
    id: str
    subject: str
    predicate: str
    value: Any
    qualifiers: dict[str, Any] = Field(default_factory=dict)
    source: str
    source_record_id: str | None = None
    source_url: str | None = None
    retrieved_at: str
    source_version: str | None = None
    evidence_type: Literal["structured", "derived"] = "structured"

    @classmethod
    def build(cls, *, subject: str, predicate: str, value: Any, source: str, qualifiers: dict[str, Any] | None = None, source_record_id: str | None = None, source_url: str | None = None, source_version: str | None = None, evidence_type: Literal["structured", "derived"] = "structured") -> "EvidenceItem":
        qualifiers = qualifiers or {}
        payload = json.dumps({"subject": subject, "predicate": predicate, "value": value, "source": source, "qualifiers": qualifiers, "source_record_id": source_record_id}, sort_keys=True, default=str)
        eid = "ev_" + hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
        return cls(id=eid, subject=subject, predicate=predicate, value=value, qualifiers=qualifiers, source=source, source_record_id=source_record_id, source_url=source_url, retrieved_at=datetime.now(timezone.utc).isoformat(), source_version=source_version, evidence_type=evidence_type)


class ConflictAssessment(BaseModel):
    evidence_a: str
    evidence_b: str
    relation: Literal["agreement", "complementary", "context_difference", "conflict"]
    reason: str


class Claim(BaseModel):
    text: str
    support_ids: list[str] = Field(default_factory=list)
    supported: bool = False


class SourceTrace(BaseModel):
    source: str
    operation: str
    ok: bool
    latency_ms: float
    result_count: int = 0
    error: str | None = None


class QueryRequest(BaseModel):
    question: str = Field(min_length=3)
    max_results: int = Field(default=20, ge=1, le=100)
    debug: bool = False


class QueryResponse(BaseModel):
    answer: str
    plan: QueryPlan
    claims: list[Claim]
    evidence: list[EvidenceItem]
    conflicts: list[ConflictAssessment]
    traces: list[SourceTrace]
    supported_claim_rate: float
    warnings: list[str] = Field(default_factory=list)
