"""Document endpoints: list ingested docs and upload new ones."""
from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import SessionLocal, get_db
from backend.models import Document, Job
from backend.jobs.ingest import run_ingest
from backend.schemas import DocumentSummary, JobResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


@router.get("/documents", response_model=list[DocumentSummary])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentSummary]:
    """Return all ingested documents ordered by creation date."""
    docs = db.execute(
        select(Document).order_by(Document.created_at.desc())
    ).scalars().all()
    return [DocumentSummary.model_validate(d) for d in docs]


@router.post("/documents/upload", response_model=JobResponse, status_code=202)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Upload an XML drug label; starts async ingest job. Poll /jobs/{id}."""
    if not file.filename or not file.filename.lower().endswith(".xml"):
        raise HTTPException(status_code=400, detail="Only .xml files are accepted")

    xml_content = file.file.read()

    job = Job(
        id=uuid.uuid4(),
        kind="ingest_spl",
        status="queued",
        payload={"filename": file.filename, "size": len(xml_content)},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        run_ingest,
        job.id,
        xml_content,
        file.filename,
        SessionLocal,
    )

    return JobResponse.model_validate(job)
