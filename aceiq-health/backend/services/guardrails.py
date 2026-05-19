"""PII redaction and prescribing-intent detection.

Uses regex only — no LLM calls in this layer.
Why regex: auditability, determinism, zero latency, no per-query cost.
"""

from __future__ import annotations

import re

# ── PII patterns ─────────────────────────────────────────────────────────────

_PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("AADHAAR", re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b")),
    (
        "PHONE",
        re.compile(
            r"(?<!\d)(?:\+?\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}(?!\d)"
        ),
    ),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("MRN", re.compile(r"\bMRN[:\s#-]*\d{4,10}\b", re.IGNORECASE)),
    ("DOB", re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")),
]

# Keep the trigger word ("patient", "Mr", etc.) and redact only the name.
_NAME_PATTERN = re.compile(
    r"\b(patient|mr|mrs|ms|dr|doctor|name[d]?|called)"
    r"\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b",
    re.IGNORECASE,
)

# ── Prescribing-intent patterns ───────────────────────────────────────────────

_PRESCRIBING_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"\bwhat (?:should|do) (?:i|we) (?:prescribe|give|order|recommend)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bbest (?:drug|antibiotic|medication|treatment) for\b", re.IGNORECASE),
    re.compile(r"\b(?:can|should) i (?:start|give|switch|stop)\b", re.IGNORECASE),
    re.compile(r"\bdiagnose|diagnosis for\b", re.IGNORECASE),
    re.compile(r"\bmy patient (?:has|is|with)\b", re.IGNORECASE),
]

REFUSAL_MESSAGE = (
    "This appears to be a prescribing-decision question. AceIQ Health is a "
    "reference tool, not a clinical decision-support system. Try rephrasing as "
    "a label-lookup question, e.g. 'What does the metformin label say about "
    "renal dosing?'"
)

DISCLAIMER = (
    "Educational reference only; not clinical advice. "
    "Verify against primary sources before patient care."
)


def redact_pii(text: str) -> str:
    """Replace PII tokens with [REDACTED:LABEL] placeholders."""
    for label, pattern in _PII_PATTERNS:
        text = pattern.sub(f"[REDACTED:{label}]", text)

    # Keep the trigger word; replace the name itself.
    def _redact_name(m: re.Match) -> str:
        trigger = m.group(1)
        return f"{trigger} [REDACTED:NAME]"

    text = _NAME_PATTERN.sub(_redact_name, text)
    return text


def is_prescribing_intent(text: str) -> bool:
    """Return True if the text matches any prescribing-decision pattern."""
    return any(p.search(text) for p in _PRESCRIBING_PATTERNS)
