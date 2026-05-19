"""Hybrid retrieval: vector search + trigram search → RRF → cross-encoder rerank."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.services.embeddings import embed_query, rerank

logger = logging.getLogger(__name__)


@dataclass
class ChunkResult:
    """Flat view of a chunk joined with its document metadata."""

    id: UUID
    document_id: UUID
    section: str
    section_order: int
    text: str
    drug_name: Optional[str]
    title: str
    source: str
    external_id: str


_VECTOR_SQL = text("""
    SELECT
        c.id, c.document_id, c.section, c.section_order, c.text,
        d.drug_name, d.title, d.source, d.external_id
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE c.embedding IS NOT NULL
    ORDER BY c.embedding <=> cast(:vec AS vector)
    LIMIT :lim
""")

_VECTOR_SQL_DRUG = text("""
    SELECT
        c.id, c.document_id, c.section, c.section_order, c.text,
        d.drug_name, d.title, d.source, d.external_id
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE c.embedding IS NOT NULL
      AND LOWER(d.drug_name) = ANY(:drugs)
    ORDER BY c.embedding <=> cast(:vec AS vector)
    LIMIT :lim
""")

_TRGM_SQL = text("""
    SELECT
        c.id, c.document_id, c.section, c.section_order, c.text,
        d.drug_name, d.title, d.source, d.external_id,
        similarity(c.text, :query) AS sim
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    ORDER BY sim DESC
    LIMIT :lim
""")

_TRGM_SQL_DRUG = text("""
    SELECT
        c.id, c.document_id, c.section, c.section_order, c.text,
        d.drug_name, d.title, d.source, d.external_id,
        similarity(c.text, :query) AS sim
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE LOWER(d.drug_name) = ANY(:drugs)
    ORDER BY sim DESC
    LIMIT :lim
""")


def _row_to_chunk(row) -> ChunkResult:
    return ChunkResult(
        id=row.id,
        document_id=row.document_id,
        section=row.section,
        section_order=row.section_order,
        text=row.text,
        drug_name=row.drug_name,
        title=row.title,
        source=row.source,
        external_id=row.external_id,
    )


def _vec_str(vec: list[float]) -> str:
    """Format a float list as a pgvector literal string."""
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


def _rrf_fuse(
    list_a: list[ChunkResult], list_b: list[ChunkResult], k: int = 60
) -> list[ChunkResult]:
    """Reciprocal Rank Fusion: combine two ranked lists into one."""
    scores: dict[str, float] = {}
    items: dict[str, ChunkResult] = {}

    for rank, item in enumerate(list_a, 1):
        key = str(item.id)
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
        items[key] = item

    for rank, item in enumerate(list_b, 1):
        key = str(item.id)
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
        items[key] = item

    sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [items[k] for k in sorted_keys]


def retrieve(
    question: str,
    db: Session,
    top_k: int | None = None,
    drug_filter: list[str] | None = None,
    use_reranker: bool | None = None,
) -> list[ChunkResult]:
    """Run hybrid retrieval and return top-N re-ranked chunks.

    Pipeline: embed query → vector top-K + trigram top-K → RRF → cross-encoder.
    """
    settings = get_settings()
    if top_k is None:
        top_k = settings.top_k_retrieve
    if use_reranker is None:
        use_reranker = settings.use_reranker

    query_vec = embed_query(question)
    vec_str = _vec_str(query_vec)

    drug_list = [d.lower() for d in drug_filter] if drug_filter else None

    try:
        # Vector search
        if drug_list:
            vec_rows = db.execute(
                _VECTOR_SQL_DRUG, {"vec": vec_str, "lim": top_k, "drugs": drug_list}
            ).fetchall()
        else:
            vec_rows = db.execute(
                _VECTOR_SQL, {"vec": vec_str, "lim": top_k}
            ).fetchall()

        vector_results = [_row_to_chunk(r) for r in vec_rows]

        # Trigram search
        if drug_list:
            trgm_rows = db.execute(
                _TRGM_SQL_DRUG, {"query": question, "lim": top_k, "drugs": drug_list}
            ).fetchall()
        else:
            trgm_rows = db.execute(
                _TRGM_SQL, {"query": question, "lim": top_k}
            ).fetchall()

        trigram_results = [_row_to_chunk(r) for r in trgm_rows]

    except Exception as exc:
        logger.warning("Retrieval DB error: %s — falling back to empty results", exc)
        return []

    # RRF fusion
    fused = _rrf_fuse(vector_results, trigram_results)
    candidates = fused[: max(top_k, settings.top_k_rerank)]

    # Cross-encoder rerank
    if use_reranker and candidates:
        try:
            candidates = rerank(question, candidates, settings.top_k_rerank)
        except Exception as exc:
            logger.warning("Reranker failed: %s — using RRF order", exc)
            candidates = candidates[: settings.top_k_rerank]
    else:
        candidates = candidates[: settings.top_k_rerank]

    return candidates
