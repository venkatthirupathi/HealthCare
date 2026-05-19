"""Ingest pipeline: parse → chunk → embed → persist in Postgres."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.models import Chunk, Document, Job
from backend.services.chunker import chunk_label
from backend.services.embeddings import embed_texts
from backend.services.parser import parse_spl_xml

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def run_ingest(
    job_id: uuid.UUID,
    xml_content: bytes,
    filename: str,
    session_factory,
) -> None:
    """Full ingest pipeline, executed in a background task.

    Idempotent: re-ingesting the same external_id replaces the existing chunks.
    """
    with session_factory() as db:
        _run(job_id, xml_content, filename, db)


def _run(
    job_id: uuid.UUID,
    xml_content: bytes,
    filename: str,
    db: Session,
) -> None:
    job = db.get(Job, job_id)
    if job is None:
        logger.error("Job %s not found", job_id)
        return

    try:
        job.status = "running"
        job.updated_at = _now()
        db.commit()

        external_id = Path(filename).stem
        label = parse_spl_xml(xml_content, external_id)

        # Check for existing document — ingest is idempotent
        existing = db.execute(
            select(Document).where(
                Document.source == "upload",
                Document.external_id == external_id,
            )
        ).scalar_one_or_none()

        if existing:
            db.execute(delete(Chunk).where(Chunk.document_id == existing.id))
            doc = existing
            doc.title = label.title
            doc.drug_name = label.drug_name
            doc.meta = {"section_count": len(label.sections)}
        else:
            doc = Document(
                source="upload",
                external_id=external_id,
                title=label.title,
                drug_name=label.drug_name,
                meta={"section_count": len(label.sections)},
            )
            db.add(doc)
            db.flush()  # materialize doc.id

        # Chunk & embed
        chunks_data = chunk_label(label)
        texts = [c.text for c in chunks_data]
        embeddings = embed_texts(texts) if texts else []

        for chunk_data, embedding in zip(chunks_data, embeddings):
            db.add(
                Chunk(
                    document_id=doc.id,
                    section=chunk_data.section,
                    section_order=chunk_data.section_order,
                    text=chunk_data.text,
                    embedding=embedding,
                )
            )

        db.commit()

        job.status = "done"
        job.result = {
            "document_id": str(doc.id),
            "chunk_count": len(chunks_data),
            "drug_name": label.drug_name,
        }
        job.updated_at = _now()
        db.commit()

        logger.info(
            "Ingest complete: %s → %d chunks (job=%s)",
            filename,
            len(chunks_data),
            job_id,
        )

    except Exception as exc:
        logger.exception("Ingest failed for job %s: %s", job_id, exc)
        db.rollback()
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error = str(exc)
            job.updated_at = _now()
            db.commit()
        raise
