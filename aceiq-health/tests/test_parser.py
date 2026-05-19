"""Tests for SPL XML parser."""
from __future__ import annotations

import pytest

from backend.services.parser import ParsedLabel, parse_spl_xml

METFORMIN_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<document>
  <title>Metformin Hydrochloride Tablets</title>
  <name>Metformin</name>
  <section code="34070-3" displayName="Contraindications">
    <text>Metformin is contraindicated when eGFR is below 30 mL/min.</text>
  </section>
  <section code="34068-7" displayName="Dosage and Administration">
    <text>Starting dose is 500 mg twice daily.</text>
  </section>
</document>"""


def test_parse_returns_correct_title():
    label = parse_spl_xml(METFORMIN_SAMPLE, "metformin")
    assert label.title == "Metformin Hydrochloride Tablets"


def test_parse_returns_drug_name():
    label = parse_spl_xml(METFORMIN_SAMPLE, "metformin")
    assert label.drug_name == "Metformin"


def test_parse_external_id():
    label = parse_spl_xml(METFORMIN_SAMPLE, "metformin")
    assert label.external_id == "metformin"


def test_parse_section_count():
    label = parse_spl_xml(METFORMIN_SAMPLE, "metformin")
    assert len(label.sections) == 2


def test_parse_section_display_names():
    label = parse_spl_xml(METFORMIN_SAMPLE, "metformin")
    names = [s.display_name for s in label.sections]
    assert "Contraindications" in names
    assert "Dosage and Administration" in names


def test_parse_section_text():
    label = parse_spl_xml(METFORMIN_SAMPLE, "metformin")
    contraindications = next(
        s for s in label.sections if s.display_name == "Contraindications"
    )
    assert "eGFR" in contraindications.text
    assert "30" in contraindications.text


def test_parse_empty_section_skipped():
    xml = b"""<document>
      <title>Test</title>
      <name>Drug</name>
      <section code="1" displayName="Empty"><text></text></section>
      <section code="2" displayName="Full"><text>Some content here.</text></section>
    </document>"""
    label = parse_spl_xml(xml, "test")
    assert len(label.sections) == 1
    assert label.sections[0].display_name == "Full"


def test_parse_string_input():
    label = parse_spl_xml(METFORMIN_SAMPLE.decode(), "metformin")
    assert isinstance(label, ParsedLabel)
    assert label.drug_name == "Metformin"
