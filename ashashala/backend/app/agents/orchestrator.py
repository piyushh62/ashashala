"""Orchestrator — classifies a student turn into an intent.

Cheap by design: a keyword fast-path handles the obvious cases with zero LLM
cost; only ambiguous turns fall through to a fast_chat classify call. Intent
drives routing to Tutor / QuizMaster / Evaluator.
"""

from __future__ import annotations

import logging

from app.services.llm_router import chat as llm_chat

logger = logging.getLogger(__name__)

_VALID = {"explain", "quiz", "grade", "progress"}

# Keyword fast-path (English + common Indic transliteration-agnostic markers).
_QUIZ_HINTS = ("quiz", "test me", "practice", "give me questions", "mcq")
_GRADE_HINTS = ("grade my", "check my answer", "is my answer", "evaluate my")
_PROGRESS_HINTS = ("my progress", "my mastery", "how am i doing", "my score")


def _keyword_intent(message: str) -> str | None:
    m = message.lower()
    if any(h in m for h in _GRADE_HINTS):
        return "grade"
    if any(h in m for h in _QUIZ_HINTS):
        return "quiz"
    if any(h in m for h in _PROGRESS_HINTS):
        return "progress"
    return None


async def classify_intent(
    message: str,
    *,
    school_id: str | None = None,
    lang_hint: str = "en",
) -> str:
    """Return one of: explain | quiz | grade | progress (defaults to explain)."""
    kw = _keyword_intent(message)
    if kw is not None:
        return kw

    prompt = (
        "Classify the student's message into exactly one intent word from this "
        "list: explain, quiz, grade, progress. Reply with ONLY the word.\n\n"
        f"Message: {message}"
    )
    try:
        raw = await llm_chat(
            messages=[{"role": "user", "content": prompt}],
            task="classify",
            lang_hint=lang_hint,
            school_id=school_id,
        )
        word = (raw or "").strip().lower().split()[0] if raw else ""
        return word if word in _VALID else "explain"
    except Exception as e:  # noqa: BLE001 — classification must never break the turn
        logger.warning("intent classify failed, defaulting to explain: %s", e)
        return "explain"
