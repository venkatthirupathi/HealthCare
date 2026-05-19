"""Pydantic v2 request/response schemas for all API endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Query ───────────────────────────────────────────────────────────────────


class QueryRequest(BaseModel):
    """Incoming question with optional drug filter."""

    question: str = Field(..., min_length=1, max_length=2000)
    filters: Optional[dict[str, Any]] = None


class Citation(BaseModel):
    """Source evidence for a single claim in the answer."""

    chunk_id: str
    document_id: str
    drug_name: Optional[str]
    section: str
    source: str
    external_id: str
    excerpt: str


class QueryResponse(BaseModel):
    """Full response returned by POST /api/v1/query."""

    answer: str
    refused: bool
    refusal_reason: Optional[str] = None
    citations: list[Citation]
    model_used: str
    provider_used: str
    verifier_score: Optional[float] = None
    latency_ms: int
    disclaimer: str


# ── Documents ────────────────────────────────────────────────────────────────


class DocumentSummary(BaseModel):
    """Light-weight document representation returned by GET /api/v1/documents."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    external_id: str
    title: str
    drug_name: Optional[str]
    created_at: datetime


# ── Jobs ─────────────────────────────────────────────────────────────────────


class JobResponse(BaseModel):
    """Job status returned by GET /api/v1/jobs/{job_id}."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ── Health ───────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """System health snapshot."""

    status: str
    app_env: str
    has_anthropic: bool
    has_openai: bool
    document_count: int
    chunk_count: int
