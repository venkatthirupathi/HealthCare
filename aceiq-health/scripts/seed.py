"""Load all sample XML files into the database."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure project root is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, select, text

from backend.config import get_settings
from backend.db import Base, SessionLocal, create_tables, engine
from backend.models import Chunk, Document
from backend.services.chunker import chunk_label
from backend.services.embeddings import embed_texts
from backend.services.parser import parse_spl_xml

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("seed")

SAMPLE_DIR = ROOT / "sample_data"
SOURCE = "dailymed"


def seed_document(xml_path: Path, db) -> tuple[int, int]:
    """Parse, chunk, embed, and persist one XML file. Returns (doc_count, chunk_count)."""
    external_id = xml_path.stem
    logger.info("Processing %s …", xml_path.name)

    xml_content = xml_path.read_bytes()
    label = parse_spl_xml(xml_content, external_id)

    # Idempotent: delete existing chunks and re-ingest
    existing = db.execute(
        select(Document).where(
            Document.source == SOURCE,
            Document.external_id == external_id,
        )
    ).scalar_one_or_none()

    if existing:
        logger.info("  Replacing existing document for %s", external_id)
        db.execute(delete(Chunk).where(Chunk.document_id == existing.id))
        doc = existing
        doc.title = label.title
        doc.drug_name = label.drug_name
        doc.meta = {"section_count": len(label.sections)}
    else:
        doc = Document(
            source=SOURCE,
            external_id=external_id,
            title=label.title,
            drug_name=label.drug_name,
            meta={"section_count": len(label.sections)},
        )
        db.add(doc)
        db.flush()

    chunks_data = chunk_label(label)
    texts = [c.text for c in chunks_data]

    logger.info("  Embedding %d chunks for %s …", len(texts), label.drug_name)
    embeddings = embed_texts(texts)

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
    logger.info(
        "  ✓ %s: %d sections → %d chunks", label.drug_name, len(label.sections), len(chunks_data)
    )
    return 1, len(chunks_data)


def main() -> None:
    settings = get_settings()
    logger.info("Connecting to: %s", settings.database_url)

    create_tables()

    xml_files = sorted(SAMPLE_DIR.glob("*.xml"))
    if not xml_files:
        logger.error("No XML files found in %s", SAMPLE_DIR)
        sys.exit(1)

    total_docs = 0
    total_chunks = 0

    with SessionLocal() as db:
        for xml_path in xml_files:
            d, c = seed_document(xml_path, db)
            total_docs += d
            total_chunks += c

        # Build IVFFlat index if it doesn't exist (needs at least 1 row)
        try:
            db.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_ivfflat "
                "ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists=1)"
            ))
            db.commit()
            logger.info("IVFFlat index created/verified")
        except Exception as exc:
            logger.warning("Could not create IVFFlat index: %s", exc)
            db.rollback()

    logger.info(
        "\n✅  Seed complete: %d documents, %d chunks total", total_docs, total_chunks
    )


if __name__ == "__main__":
    main()
