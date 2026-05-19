"""Tests for section chunker."""

from __future__ import annotations

from backend.services.chunker import chunk_label
from backend.services.parser import ParsedLabel, ParsedSection


def _make_label(sections: list[tuple[str, str, str]]) -> ParsedLabel:
    return ParsedLabel(
        title="Test Drug Label",
        drug_name="TestDrug",
        external_id="test",
        sections=[
            ParsedSection(code=code, display_name=name, text=text)
            for code, name, text in sections
        ],
    )


def test_chunk_count_matches_sections():
    label = _make_label(
        [
            ("1", "Indications", "Used for type 2 diabetes."),
            ("2", "Contraindications", "Do not use if eGFR < 30."),
            ("3", "Dosage", "500 mg twice daily."),
        ]
    )
    chunks = chunk_label(label)
    assert len(chunks) == 3


def test_chunk_section_names_preserved():
    label = _make_label(
        [
            ("1", "Contraindications", "Contraindicated in renal failure."),
        ]
    )
    chunks = chunk_label(label)
    assert chunks[0].section == "Contraindications"


def test_chunk_text_preserved():
    text = "Starting dose is 500 mg twice daily."
    label = _make_label([("1", "Dosage", text)])
    chunks = chunk_label(label)
    assert chunks[0].text == text


def test_chunk_section_order():
    label = _make_label(
        [
            ("1", "First", "First section text."),
            ("2", "Second", "Second section text."),
            ("3", "Third", "Third section text."),
        ]
    )
    chunks = chunk_label(label)
    orders = [c.section_order for c in chunks]
    assert orders == sorted(orders)


def test_empty_section_text_skipped():
    label = _make_label(
        [
            ("1", "Empty", ""),
            ("2", "Full", "Contains real text."),
        ]
    )
    chunks = chunk_label(label)
    assert len(chunks) == 1
    assert chunks[0].section == "Full"


def test_whitespace_only_section_skipped():
    label = _make_label(
        [
            ("1", "Whitespace", "   \n  \t  "),
            ("2", "Real", "Actual content."),
        ]
    )
    chunks = chunk_label(label)
    assert len(chunks) == 1
