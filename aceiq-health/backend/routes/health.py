"""GET /health — system status check."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from backend.config import Settings, get_settings
from backend.db import get_db
from backend.models import Chunk, Document
from backend.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Return live system health including DB counts and provider availability."""
    try:
        doc_count = db.execute(select(func.count()).select_from(Document)).scalar_one()
        chunk_count = db.execute(select(func.count()).select_from(Chunk)).scalar_one()
    except Exception:
        doc_count = -1
        chunk_count = -1

    return HealthResponse(
        status="ok",
        app_env=settings.app_env,
        has_anthropic=bool(settings.anthropic_api_key),
        has_openai=bool(settings.openai_api_key),
        document_count=doc_count,
        chunk_count=chunk_count,
    )
