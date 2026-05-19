"""LLM provider chain with automatic fallback.

Priority: Anthropic (primary) → OpenAI (fallback) → retrieval-only (no crash).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypedDict

from backend.config import get_settings

if TYPE_CHECKING:
    from backend.services.retrieval import ChunkResult

logger = logging.getLogger(__name__)

# ── Prompt templates (verbatim from project brief) ───────────────────────────

_SYSTEM_PROMPT = """\
You are AceIQ Health, a clinical reference assistant for medical students
and junior doctors. You answer questions using ONLY the drug-label and
clinical evidence excerpts provided to you.

Rules — non-negotiable:
1. Answer strictly from the provided excerpts. If the excerpts do not
contain the answer, say so explicitly. Do not use outside knowledge.
2. Cite the section name (in square brackets) for every clinical claim
you make. Example: "Metformin is contraindicated in patients with
eGFR <30 mL/min/1.73m² [Contraindications]."
3. Never provide individualized prescribing advice. If asked "what
should I prescribe for patient X," redirect to the label excerpts and
remind the user to consult appropriate clinical judgement.
4. Use precise clinical language. Do not soften factual
contraindications or warnings to be reassuring.
5. Keep answers concise — typically 3–6 sentences. Bullet points are fine
for lists of adverse reactions or contraindications.
6. End every answer with: "Source: drug labels and provided excerpts only.\""""


class LLMResult(TypedDict):
    answer: str
    model_used: str
    provider_used: str
    tokens_in: int
    tokens_out: int


def _format_user_message(question: str, chunks: list[ChunkResult]) -> str:
    """Build the templated user message from retrieved chunks."""
    excerpts = []
    for i, chunk in enumerate(chunks, 1):
        drug = chunk.drug_name or "unknown"
        excerpts.append(
            f"[Excerpt {i} — drug: {drug}, section: {chunk.section}]\n{chunk.text}"
        )

    return (
        "Drug-label excerpts:\n\n"
        + "\n\n".join(excerpts)
        + "\n\n---\nQuestion: "
        + question
        + "\n\nAnswer using only the excerpts above. Cite section names in [brackets].\n"
        "If the answer is not in the excerpts, say \"The provided excerpts do not\n"
        'address this question."'
    )


def _retrieval_only_answer(chunks: list[ChunkResult]) -> LLMResult:
    """Concatenate chunks as a plain-text answer when no LLM is available."""
    if not chunks:
        body = "The provided excerpts do not address this question."
    else:
        parts = [f"[{c.section}] {c.text}" for c in chunks]
        body = "\n\n".join(parts)

    return LLMResult(
        answer=body + "\n\nSource: drug labels and provided excerpts only.",
        model_used="retrieval-only",
        provider_used="none",
        tokens_in=0,
        tokens_out=0,
    )


def generate_answer(question: str, chunks: list[ChunkResult]) -> LLMResult:
    """Generate an answer via the provider chain, degrading gracefully."""
    settings = get_settings()
    user_msg = _format_user_message(question, chunks)

    # 1. Anthropic primary
    if settings.anthropic_api_key:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            resp = client.messages.create(
                model=settings.primary_model,
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            return LLMResult(
                answer=resp.content[0].text,
                model_used=settings.primary_model,
                provider_used="anthropic",
                tokens_in=resp.usage.input_tokens,
                tokens_out=resp.usage.output_tokens,
            )
        except Exception as exc:
            logger.warning("Anthropic call failed: %s", exc)

    # 2. OpenAI fallback
    if settings.openai_api_key:
        try:
            import openai

            client = openai.OpenAI(api_key=settings.openai_api_key)
            resp = client.chat.completions.create(
                model=settings.fallback_model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=1024,
            )
            return LLMResult(
                answer=resp.choices[0].message.content or "",
                model_used=settings.fallback_model,
                provider_used="openai",
                tokens_in=resp.usage.prompt_tokens if resp.usage else 0,
                tokens_out=resp.usage.completion_tokens if resp.usage else 0,
            )
        except Exception as exc:
            logger.warning("OpenAI call failed: %s", exc)

    # 3. Retrieval-only — no LLM available
    logger.warning("No LLM available — returning retrieval-only answer")
    return _retrieval_only_answer(chunks)
