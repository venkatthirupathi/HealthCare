"""SQLAlchemy engine, session factory, and declarative base."""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import get_settings


def _build_engine():
    settings = get_settings()
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    # Register pgvector types with the connection pool so vector columns work.
    try:
        from pgvector.sqlalchemy import Vector  # noqa: F401

        @event.listens_for(engine, "connect")
        def _set_search_path(dbapi_conn, connection_record):  # noqa: ARG001
            with dbapi_conn.cursor() as cur:
                cur.execute("SET search_path TO public")

    except ImportError:
        pass

    return engine


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def get_db():
    """FastAPI dependency that yields a DB session and closes it on exit."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create all tables if they don't exist. Called at app startup."""
    # Import models so their metadata is registered before create_all.
    import backend.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
