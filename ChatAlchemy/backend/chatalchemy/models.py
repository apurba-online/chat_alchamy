from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

EntityType = Literal["drug", "condition", "target", "gene", "trial", "compound", "unknown"]
Intent = Literal[
    "identity",
    "label",
    "approval",
    "trials",
    "target_drugs",
    "gene",
    "disease",
    "compound",
    "cross_source",
    "general",
    "unknown",
]

MAX_MESSAGE_CHARS = 12_000
MAX_CONVERSATION_CHARS = 80_000
MAX_USER_EVIDENCE_ITEM_BYTES = 25_000
MAX_USER_EVIDENCE_TOTAL_BYTES = 200_000
MAX_GENE_TEXT_CHARS = 128
MAX_DISEASE_TEXT_CHARS = 512


def _validate_messages(messages: list[dict[str, str]], *, total_limit: int = MAX_CONVERSATION_CHARS):
    total = 0
    for message in messages:
        role = str(message.get("role") or "")
        content = str(message.get("content") or "")
        if role and len(role) > 32:
            raise ValueError("message role is too long")
        if len(content) > MAX_MESSAGE_CHARS:
            raise ValueError(f"message content exceeds {MAX_MESSAGE_CHARS} characters")
        total += len(role) + len(content)
    if total > total_limit:
        raise ValueError(f"conversation exceeds {total_limit} characters")
    return messages


def _json_bytes(value: Any) -> int:
    return len(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8"))


class Entity(BaseModel):
    text: str
    type: EntityType
    canonical_name: str | None = None
    ids: dict[str, str] = Field(default_factory=dict)


class Operation(BaseModel):
    source: str
    action: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class QueryPlan(BaseModel):
    question: str
    intent: Intent
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
    evidence_type: Literal["structured", "derived", "user"] = "structured"

    @classmethod
    def build(
        cls,
        *,
        subject: str,
        predicate: str,
        value: Any,
        source: str,
        qualifiers: dict[str, Any] | None = None,
        source_record_id: str | None = None,
        source_url: str | None = None,
        source_version: str | None = None,
        evidence_type: Literal["structured", "derived", "user"] = "structured",
    ) -> "EvidenceItem":
        qualifiers = qualifiers or {}
        payload = json.dumps(
            {
                "subject": subject,
                "predicate": predicate,
                "value": value,
                "source": source,
                "qualifiers": qualifiers,
                "source_record_id": source_record_id,
            },
            sort_keys=True,
            default=str,
        )
        evidence_id = "ev_" + hashlib.sha1(payload.encode()).hexdigest()[:12]
        return cls(
            id=evidence_id,
            subject=subject,
            predicate=predicate,
            value=value,
            qualifiers=qualifiers,
            source=source,
            source_record_id=source_record_id,
            source_url=source_url,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            source_version=source_version,
            evidence_type=evidence_type,
        )


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


class TablePayload(BaseModel):
    headers: list[str]
    rows: list[list[Any]]
    caption: str | None = None


class ChartDataset(BaseModel):
    label: str
    data: list[float]


class ChartPayload(BaseModel):
    type: Literal["line", "bar", "pie"]
    labels: list[str]
    datasets: list[ChartDataset]
    title: str | None = None


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=8_000)
    max_results: int = Field(default=20, ge=1, le=100)
    conversation: list[dict[str, str]] = Field(default_factory=list, max_length=20)
    user_evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    debug: bool = False

    @field_validator("conversation")
    @classmethod
    def validate_conversation(cls, value):
        return _validate_messages(value)

    @field_validator("user_evidence")
    @classmethod
    def validate_user_evidence(cls, value):
        total = 0
        for item in value:
            size = _json_bytes(item)
            if size > MAX_USER_EVIDENCE_ITEM_BYTES:
                raise ValueError(f"user evidence item exceeds {MAX_USER_EVIDENCE_ITEM_BYTES} bytes")
            total += size
        if total > MAX_USER_EVIDENCE_TOTAL_BYTES:
            raise ValueError(f"user evidence exceeds {MAX_USER_EVIDENCE_TOTAL_BYTES} bytes")
        return value


class QueryResponse(BaseModel):
    answer: str
    plan: QueryPlan
    claims: list[Claim]
    evidence: list[EvidenceItem]
    conflicts: list[ConflictAssessment]
    traces: list[SourceTrace]
    supported_claim_rate: float
    warnings: list[str] = Field(default_factory=list)
    table: TablePayload | None = None
    chart: ChartPayload | None = None


class ChatRequest(BaseModel):
    messages: list[dict[str, str]] = Field(min_length=1, max_length=30)
    uploaded_context: str | None = Field(default=None, max_length=20_000)

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, value):
        return _validate_messages(value)


class TitleRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5_000)


class BiomedicalExtractRequest(BaseModel):
    text: str = Field(min_length=1, max_length=250_000)
    filename: str | None = Field(default=None, max_length=255)


class BiomedicalExtractResponse(BaseModel):
    summary: str
    genes: list[str]
    suggested_diseases: list[str]


class BiomedicalAnalyzeRequest(BaseModel):
    genes: list[str] = Field(default_factory=list, max_length=200)
    query: str | None = Field(default=None, max_length=8_000)
    suggested_diseases: list[str] = Field(default_factory=list, max_length=100)
    paper_summary: str | None = Field(default=None, max_length=100_000)

    @field_validator("genes")
    @classmethod
    def validate_genes(cls, value):
        for gene in value:
            if len(gene) > MAX_GENE_TEXT_CHARS:
                raise ValueError(f"gene text exceeds {MAX_GENE_TEXT_CHARS} characters")
        return value

    @field_validator("suggested_diseases")
    @classmethod
    def validate_diseases(cls, value):
        for disease in value:
            if len(disease) > MAX_DISEASE_TEXT_CHARS:
                raise ValueError(f"disease text exceeds {MAX_DISEASE_TEXT_CHARS} characters")
        return value
