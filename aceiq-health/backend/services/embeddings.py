"""Lazy-loaded sentence-transformers embedding wrapper."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.config import get_settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_embedding_model: SentenceTransformer | None = None
_reranker_model = None


def get_embedding_model() -> SentenceTransformer:
    """Return the singleton embedding model, downloading on first call."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        settings = get_settings()
        logger.info("Loading embedding model: %s", settings.embedding_model)
        _embedding_model = SentenceTransformer(settings.embedding_model)
    return _embedding_model


def get_reranker():
    """Return the singleton cross-encoder, downloading on first call."""
    global _reranker_model
    if _reranker_model is None:
        from sentence_transformers import CrossEncoder

        settings = get_settings()
        logger.info("Loading reranker: %s", settings.reranker_model)
        _reranker_model = CrossEncoder(settings.reranker_model)
    return _reranker_model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts; returns normalized float vectors."""
    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([text])[0]


def rerank(query: str, chunks: list, top_k: int) -> list:
    """Re-rank chunks with a cross-encoder; returns top_k in score order."""
    if not chunks:
        return chunks
    reranker = get_reranker()
    pairs = [(query, c.text) for c in chunks]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
    return [c for _, c in ranked[:top_k]]
