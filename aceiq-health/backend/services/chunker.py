"""Convert a ParsedLabel into a flat list of chunks ready for embedding."""

from __future__ import annotations

from dataclasses import dataclass

from backend.services.parser import ParsedLabel


@dataclass
class ChunkData:
    """One text chunk to be embedded and stored."""

    section: str
    section_order: int
    text: str


def chunk_label(label: ParsedLabel) -> list[ChunkData]:
    """Convert each section of a ParsedLabel into one ChunkData.

    Why one-section-per-chunk: the sample data sections are already short
    (< 500 tokens each), so sub-section splitting would fragment context
    without improving precision. Re-evaluate if average section length
    exceeds 400 tokens in future corpora.
    """
    chunks: list[ChunkData] = []
    for i, section in enumerate(label.sections):
        text = section.text.strip()
        if not text:
            continue
        chunks.append(
            ChunkData(
                section=section.display_name,
                section_order=i,
                text=text,
            )
        )
    return chunks
