"""Shared typed state for the LangGraph agent pipeline (Section 7.1).

One SessionState flows through: safety_in -> orchestrator ->
{tutor | quiz_master | evaluator} -> safety_out -> progress -> END.
"""

from __future__ import annotations

from typing import Literal, TypedDict


class SessionState(TypedDict, total=False):
    student_id: str
    school_id: str
    class_id: str
    subject_id: str | None
    message: str
    input_mode: Literal["text", "voice"]
    lang_detected: str          # ISO 639-1 — e.g. "en", "gu", "hi"
    intent: Literal["explain", "quiz", "grade", "progress", "unknown"]
    retrieved_chunks: list[dict]   # {text, source_type, source_ref, page_or_ts, score}
    answer: str | None
    citations: list[dict]          # {source_type, source_ref, page_or_ts, r2_url}
    quiz: dict | None
    grade: dict | None             # {score, feedback, missed_concepts, confidence}
    mastery_updates: list[dict]
    model_role_used: str           # "fast_chat" | "reasoning" | "multilingual_indic"
    provider_used: Literal["gemini", "nvidia"]
    safety_blocked: bool
    safety_reason: str | None
    errors: list[str]


def new_state(
    *,
    student_id: str,
    school_id: str,
    class_id: str,
    message: str,
    subject_id: str | None = None,
    input_mode: Literal["text", "voice"] = "text",
) -> SessionState:
    """Initialise a SessionState with safe defaults for a fresh turn."""
    return SessionState(
        student_id=student_id,
        school_id=school_id,
        class_id=class_id,
        subject_id=subject_id,
        message=message,
        input_mode=input_mode,
        lang_detected="en",
        intent="unknown",
        retrieved_chunks=[],
        answer=None,
        citations=[],
        quiz=None,
        grade=None,
        mastery_updates=[],
        model_role_used="fast_chat",
        provider_used="gemini",
        safety_blocked=False,
        safety_reason=None,
        errors=[],
    )
