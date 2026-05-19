"""POST /api/v1/query — the core RAG query endpoint."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.db import get_db
from backend.models import QueryLog
from backend.schemas import Citation, QueryRequest, QueryResponse
from backend.services.guardrails import (
    DISCLAIMER,
    REFUSAL_MESSAGE,
    is_prescribing_intent,
    redact_pii,
)
from backend.services.llm import generate_answer
from backend.services.retrieval import retrieve
from backend.services.verifier import verify_answer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


def _build_citations(chunks) -> list[Citation]:
    return [
        Citation(
            chunk_id=str(c.id),
            document_id=str(c.document_id),
            drug_name=c.drug_name,
            section=c.section,
            source=c.source,
            external_id=c.external_id,
            excerpt=c.text[:500],
        )
        for c in chunks
    ]


def _log_query(
    db: Session,
    *,
    question: str,
    redacted_question: str,
    answer: str,
    refused: bool,
    refusal_reason: str | None,
    model_used: str,
    provider_used: str,
    chunk_ids: list[str],
    verifier_score: float | None,
    latency_ms: int,
    tokens_in: int,
    tokens_out: int,
) -> None:
    log = QueryLog(
        id=uuid.uuid4(),
        question=question,
        redacted_question=redacted_question,
        answer=answer,
        refused=refused,
        refusal_reason=refusal_reason,
        model_used=model_used,
        provider_used=provider_used,
        retrieved_chunk_ids=chunk_ids,
        verifier_score=verifier_score,
        latency_ms=latency_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )
    db.add(log)
    try:
        db.commit()
    except Exception as exc:
        logger.warning("Failed to write query log: %s", exc)
        db.rollback()


@router.post("/query", response_model=QueryResponse)
def query(
    request: QueryRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> QueryResponse:
    """Run the full RAG pipeline: guardrails → retrieval → generation → verification."""
    t0 = time.perf_counter()

    # Step 1: PII redaction
    redacted = (
        redact_pii(request.question)
        if settings.enable_pii_redaction
        else request.question
    )

    # Step 2: Intent detection — refuse prescribing questions
    if settings.refuse_prescribing_queries and is_prescribing_intent(redacted):
        latency_ms = int((time.perf_counter() - t0) * 1000)
        _log_query(
            db,
            question=request.question,
            redacted_question=redacted,
            answer=REFUSAL_MESSAGE,
            refused=True,
            refusal_reason="prescribing_intent",
            model_used="refusal",
            provider_used="guardrail",
            chunk_ids=[],
            verifier_score=None,
            latency_ms=latency_ms,
            tokens_in=0,
            tokens_out=0,
        )
        return QueryResponse(
            answer=REFUSAL_MESSAGE,
            refused=True,
            refusal_reason="prescribing_intent",
            citations=[],
            model_used="refusal",
            provider_used="guardrail",
            verifier_score=None,
            latency_ms=latency_ms,
            disclaimer=DISCLAIMER,
        )

    # Step 3: Retrieval
    drug_filter: list[str] | None = (
        request.filters.get("drugs") if request.filters else None
    )
    chunks = retrieve(redacted, db, drug_filter=drug_filter)

    # Step 4: LLM generation
    llm_result = generate_answer(redacted, chunks)

    # Step 5: Grounding verification
    verifier_score: float | None = None
    if llm_result["provider_used"] != "none":
        verifier_score = verify_answer(llm_result["answer"], chunks)

    latency_ms = int((time.perf_counter() - t0) * 1000)

    _log_query(
        db,
        question=request.question,
        redacted_question=redacted,
        answer=llm_result["answer"],
        refused=False,
        refusal_reason=None,
        model_used=llm_result["model_used"],
        provider_used=llm_result["provider_used"],
        chunk_ids=[str(c.id) for c in chunks],
        verifier_score=verifier_score,
        latency_ms=latency_ms,
        tokens_in=llm_result["tokens_in"],
        tokens_out=llm_result["tokens_out"],
    )

    return QueryResponse(
        answer=llm_result["answer"],
        refused=False,
        refusal_reason=None,
        citations=_build_citations(chunks),
        model_used=llm_result["model_used"],
        provider_used=llm_result["provider_used"],
        verifier_score=verifier_score,
        latency_ms=latency_ms,
        disclaimer=DISCLAIMER,
    )
