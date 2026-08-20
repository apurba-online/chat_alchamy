import pytest
from pydantic import ValidationError

from chatalchemy.models import (
    MAX_MESSAGE_CHARS,
    MAX_USER_EVIDENCE_ITEM_BYTES,
    BiomedicalAnalyzeRequest,
    ChatRequest,
    QueryRequest,
)


def test_query_conversation_rejects_oversized_message_content():
    with pytest.raises(ValidationError, match="message content exceeds"):
        QueryRequest(
            question="What is aspirin?",
            conversation=[{"role": "user", "content": "x" * (MAX_MESSAGE_CHARS + 1)}],
        )


def test_chat_messages_reject_oversized_message_content():
    with pytest.raises(ValidationError, match="message content exceeds"):
        ChatRequest(messages=[{"role": "user", "content": "x" * (MAX_MESSAGE_CHARS + 1)}])


def test_user_evidence_rejects_one_oversized_item():
    with pytest.raises(ValidationError, match="user evidence item exceeds"):
        QueryRequest(
            question="Combine this with FDA evidence",
            user_evidence=[{"subject": "candidate", "predicate": "note", "value": "x" * (MAX_USER_EVIDENCE_ITEM_BYTES + 1)}],
        )


def test_normal_public_payload_remains_valid():
    request = QueryRequest(
        question="Which uploaded candidates have FDA records?",
        conversation=[{"role": "user", "content": "Please check my list."}],
        user_evidence=[{"subject": "osimertinib", "predicate": "candidate_drug", "value": "osimertinib"}],
    )
    assert request.question.startswith("Which uploaded")
    assert request.user_evidence[0]["subject"] == "osimertinib"


def test_biomedical_entity_text_is_bounded():
    with pytest.raises(ValidationError, match="gene text exceeds"):
        BiomedicalAnalyzeRequest(genes=["G" * 129])
    with pytest.raises(ValidationError, match="disease text exceeds"):
        BiomedicalAnalyzeRequest(suggested_diseases=["d" * 513])
