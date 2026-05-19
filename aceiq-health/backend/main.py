"""FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.db import create_tables
from backend.routes import documents, health, jobs, query

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="AceIQ Health",
        description=(
            "AI-native drug reference assistant for medical students and junior doctors. "
            "Answers grounded, cited questions about drug labels in 2–3 seconds."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(jobs.router)
    app.include_router(query.router)

    @app.on_event("startup")
    def on_startup() -> None:
        logger.info("Creating DB tables if not present…")
        create_tables()
        logger.info(
            "AceIQ Health started — env=%s anthropic=%s openai=%s",
            settings.app_env,
            bool(settings.anthropic_api_key),
            bool(settings.openai_api_key),
        )

    return app


app = create_app()
