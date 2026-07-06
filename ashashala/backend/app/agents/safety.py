"""Safety layer for the tutor agent.

Three defenses, in order of cost:

1. Harmful-content keyword block (deterministic, free) — hard-refuses questions
   about violence, self-harm, weapons, etc. regardless of subject.
2. Subject recognition — the coarse topic guard. Fine-grained "is this on
   topic?" nuance is delegated to the tutor prompt (PROJECT_PROMPT §7.7), which
   refuses off-subject questions and redirects to the teacher.
3. NVIDIA NeMo-Guard jailbreak classifier (optional, config-gated) — takes a
   pre-computed embedding of the message and scores prompt-injection attempts.

Gemini's built-in safety (BLOCK_ONLY_HIGH) still runs free on every Gemini
generation inside gemini_client — this module is defense-in-depth on top of it.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.core.exceptions import ForbiddenError

logger = logging.getLogger(__name__)


# Genuinely harmful topics — a hard block, independent of the class subject.
HARMFUL_KEYWORDS = {
    "violence", "drugs", "alcohol", "gambling", "weapons", "hate",
    "suicide", "self-harm", "self harm", "terrorism", "illegal", "hacking",
    "bomb", "kill", "murder", "how to make a bomb",
}

# Recognized academic subjects (Latin-script names). Indic-script subject names
# are school-defined localized labels and are trusted via _has_indic_script()
# instead of being enumerated here.
ALLOWED_SUBJECTS = {
    "mathematics", "math", "maths", "science", "physics", "chemistry", "biology",
    "english", "hindi", "gujarati", "marathi", "tamil", "telugu",
    "bengali", "kannada", "malayalam", "punjabi", "urdu", "sanskrit",
    "history", "geography", "civics", "economics", "computer science",
    "social studies", "social science", "environmental science", "evs",
    "general knowledge", "moral science", "art", "music",
}

# Indic Unicode blocks start at U+0900 (Devanagari) and run through the South
# and South-East Asian scripts. A subject name containing any such character is
# a localized label a teacher created — treat it as a legitimate subject.
_INDIC_START = 0x0900


def _has_indic_script(text: str) -> bool:
    return any(ord(ch) >= _INDIC_START for ch in text if ch.isalpha())


def _contains_harmful(text: str) -> str | None:
    lowered = text.lower()
    for kw in HARMFUL_KEYWORDS:
        if kw in lowered:
            return kw
    return None


def _is_recognized_subject(subject: str) -> bool:
    if not subject:
        return False
    if subject.strip().lower() in ALLOWED_SUBJECTS:
        return True
    return _has_indic_script(subject)


async def check_topic_relevance(question: str, subject: str) -> bool:
    """Coarse guard: True if the question is safe and the subject is a real
    academic subject. Harmful content or an unrecognized subject → False.

    Deterministic and network-free — the nuanced "is this actually about the
    subject?" judgement is handled by the tutor prompt, not here.
    """
    if _contains_harmful(question):
        return False
    return _is_recognized_subject(subject)


async def gemini_safety_check(text: str) -> tuple[bool, str | None]:
    """Explicit harmful-content pre-check.

    Returns (is_safe, reason). Gemini's model-level safety filter runs
    automatically inside gemini_client on every generation; this catches
    obviously harmful input *before* we spend a generation call on it.
    """
    kw = _contains_harmful(text)
    if kw:
        return False, f"harmful_content:{kw}"
    return True, None


async def check_jailbreak(text: str, *, school_id: str | None = None) -> tuple[bool, str | None]:
    """NVIDIA NeMo-Guard jailbreak / prompt-injection detection.

    The classifier consumes a pre-computed embedding of the message (not raw
    text — PROJECT_PROMPT §7). Config-gated because it spends an embedding + a
    classifier call per message against the rate-limited free tier; off by
    default. Fails open (safe) on any error so a classifier outage never blocks
    a legitimate student.
    """
    if not getattr(settings, "ENABLE_JAILBREAK_DETECTION", False):
        return True, None

    try:
        from app.services.nvidia_client import get_nvidia_client
        from app.services.rag.embedder import embed_texts

        vectors, _ = await embed_texts([text], "en", school_id=school_id)
        client = get_nvidia_client()
        blocked = await client.jailbreak_score(vectors[0])
        if blocked:
            return False, "jailbreak_detected"
        return True, None
    except Exception as e:  # noqa: BLE001 — fail open, never block on classifier error
        logger.warning("Jailbreak check unavailable, allowing message: %s", e)
        return True, None


async def safety_wrapper(question: str, subject: str, *, school_id: str | None = None) -> None:
    """Run the safety pipeline before the tutor answers. Raises ForbiddenError
    (→ HTTP 403) with a student-friendly message when a check fails."""
    safe, reason = await gemini_safety_check(question)
    if not safe:
        logger.info("Blocked harmful question (%s)", reason)
        raise ForbiddenError(
            "I can't help with that. Let's keep to your class subjects — "
            "ask your teacher if you're unsure what to study."
        )

    if not await check_topic_relevance(question, subject):
        raise ForbiddenError(
            "I can only help with questions related to your class subjects. "
            "Please ask your teacher about other topics."
        )

    ok, jb_reason = await check_jailbreak(question, school_id=school_id)
    if not ok:
        logger.warning("Blocked jailbreak attempt (%s)", jb_reason)
        raise ForbiddenError(
            "That request looks like it's trying to work around your tutor's "
            "rules. Let's get back to your class material."
        )
