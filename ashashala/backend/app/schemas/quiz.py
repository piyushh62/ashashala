"""Quiz + attempt schemas (Phase 4)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QuizStartRequest(BaseModel):
    class_id: str
    subject_id: str | None = None


class QuizQuestionOut(BaseModel):
    index: int
    type: str
    question: str
    difficulty: str | None = None
    xp: int | None = None
    options: list[str] | None = None   # MCQ only


class QuizOut(BaseModel):
    id: str
    topic: str
    status: str
    class_id: str
    subject_id: str | None = None
    questions: list[QuizQuestionOut]


class QuizSubmitRequest(BaseModel):
    # answers[i] aligns to question index i: an int (MCQ option) or str (short).
    answers: list = Field(default_factory=list)


class PerQuestionFeedback(BaseModel):
    index: int
    type: str
    score: float
    xp_awarded: int
    feedback: str
    flagged: bool = False


class QuizSubmitResponse(BaseModel):
    quiz_id: str
    attempt_id: str
    attempt_score: float
    total_xp: int
    feedback_summary: str
    per_question: list[PerQuestionFeedback]
    mastery_update: dict | None = None
