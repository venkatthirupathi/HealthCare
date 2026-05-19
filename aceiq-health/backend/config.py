"""Application settings loaded from environment / .env file."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration in one place — loaded from .env or environment."""

    # Database
    database_url: str = "postgresql+psycopg://aceiq:aceiq@localhost:5432/aceiq"

    # LLM providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Model routing
    primary_model: str = "claude-sonnet-4-6"
    light_model: str = "claude-haiku-4-5-20251001"
    fallback_provider: str = "openai"
    fallback_model: str = "gpt-4o-mini"

    # Embeddings (local)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Retrieval
    top_k_retrieve: int = 8
    top_k_rerank: int = 3
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    use_reranker: bool = True

    # Safety
    enable_pii_redaction: bool = True
    enable_verifier: bool = True
    refuse_prescribing_queries: bool = True

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8501"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()
