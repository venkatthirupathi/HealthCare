"""Post-hoc grounding verifier: scores how well the answer is supported by chunks."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Optional

from backend.config import get_settings

if TYPE_CHECKING:
    from backend.services.retrieval import ChunkResult

logger = logging.getLogger(__name__)

_VERIFIER_SYSTEM = """\
You are a strict fact-checker. You are given:
  (A) drug-label EXCERPTS
  (B) an ANSWER generated from those excerpts

Score the ANSWER on grounding from 0.0 to 1.0:
  - 1.0 = every clinical claim in the ANSWER is directly supported by
    the EXCERPTS
  - 0.5 = roughly half is supported, the rest is plausible-but-unsupported
  - 0.0 = the ANSWER contains specific claims contradicted by or absent
    from EXCERPTS

Respond with ONLY a JSON object:
  {"score": 0.0-1.0, "unsupported": ["..."], "reason": "<one sentence>"}
No prose, no markdown, no code fences."""


def _build_verifier_prompt(answer: str, chunks: list[ChunkResult]) -> str:
    excerpts = "\n\n".join(f"[{c.section}] {c.text}" for c in chunks)
    return f"EXCERPTS:\n{excerpts}\n\nANSWER:\n{answer}"


def _parse_score(raw: str) -> Optional[float]:
    try:
        data = json.loads(raw.strip())
        score = float(data.get("score", 0))
        return max(0.0, min(1.0, score))
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Failed to parse verifier JSON: %s | raw=%r", exc, raw[:200])
        return None


def verify_answer(
    answer: str,
    chunks: list[ChunkResult],
) -> Optional[float]:
    """Score answer grounding 0–1. Returns None if no LLM provider available."""
    settings = get_settings()

    if not settings.enable_verifier or not chunks:
        return None

    user_msg = _build_verifier_prompt(answer, chunks)

    # Try Anthropic light model first
    if settings.anthropic_api_key:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            response = client.messages.create(
                model=settings.light_model,
                max_tokens=256,
                system=_VERIFIER_SYSTEM,
                messages=[{"role": "user", "content": user_msg}],
            )
            return _parse_score(response.content[0].text)
        except Exception as exc:
            logger.warning("Verifier Anthropic call failed: %s", exc)

    # OpenAI fallback
    if settings.openai_api_key:
        try:
            import openai

            client = openai.OpenAI(api_key=settings.openai_api_key)
            response = client.chat.completions.create(
                model=settings.fallback_model,
                messages=[
                    {"role": "system", "content": _VERIFIER_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=256,
            )
            return _parse_score(response.choices[0].message.content or "")
        except Exception as exc:
            logger.warning("Verifier OpenAI call failed: %s", exc)

    return None
