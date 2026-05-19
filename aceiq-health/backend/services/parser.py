"""Parse FDA SPL XML files into a structured ParsedLabel."""

from __future__ import annotations

from dataclasses import dataclass, field

from lxml import etree


@dataclass
class ParsedSection:
    """A single section from the drug label."""

    code: str
    display_name: str
    text: str


@dataclass
class ParsedLabel:
    """Complete parsed representation of one SPL XML document."""

    title: str
    drug_name: str
    external_id: str
    sections: list[ParsedSection] = field(default_factory=list)


def parse_spl_xml(xml_content: bytes | str, external_id: str) -> ParsedLabel:
    """Parse raw SPL XML bytes into a ParsedLabel.

    Why: lxml gives us fast, namespace-aware parsing; the displayName attribute
    on <section> elements maps directly to the chunk section label used downstream.
    """
    if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8")

    root = etree.fromstring(xml_content)  # noqa: S320 — local data only

    title = (root.findtext("title") or "").strip()
    drug_name = (root.findtext("name") or "").strip()

    sections: list[ParsedSection] = []
    for section_el in root.findall("section"):
        code = section_el.get("code", "")
        display_name = section_el.get("displayName", "")
        text_el = section_el.find("text")
        text = (text_el.text or "").strip() if text_el is not None else ""
        if text:
            sections.append(
                ParsedSection(code=code, display_name=display_name, text=text)
            )

    return ParsedLabel(
        title=title,
        drug_name=drug_name,
        external_id=external_id,
        sections=sections,
    )
