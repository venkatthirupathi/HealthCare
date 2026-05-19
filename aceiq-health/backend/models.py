"""SQLAlchemy ORM models — SQLAlchemy 2.0 Mapped style."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None  # type: ignore[assignment]

from backend.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    """One ingested drug label (e.g. a single SPL XML file)."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_document_source_ext"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    drug_name: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, index=True
    )
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    chunks: Mapped[list[Chunk]] = relationship(
        "Chunk", back_populates="document", cascade="all, delete-orphan"
    )


_VECTOR_TYPE = Vector(384) if Vector is not None else Text


class Chunk(Base):
    """One section from a document, with its embedding vector."""

    __tablename__ = "chunks"
    __table_args__ = (
        Index(
            "ix_chunks_text_trgm",
            "text",
            postgresql_using="gin",
            postgresql_ops={"text": "gin_trgm_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    section: Mapped[str] = mapped_column(String(128), nullable=False)
    section_order: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[list]] = mapped_column(_VECTOR_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    document: Mapped[Document] = relationship("Document", back_populates="chunks")


class Job(Base):
    """Background ingest job record."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)


class QueryLog(Base):
    """Immutable audit record for every query (including refusals)."""

    __tablename__ = "query_logs"
    __table_args__ = (Index("ix_query_logs_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    redacted_question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    refused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    refusal_reason: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    model_used: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_used: Mapped[str] = mapped_column(String(32), nullable=False)
    retrieved_chunk_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    verifier_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_in: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)
