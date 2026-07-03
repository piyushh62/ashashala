"""FlaggedAnswer — the teacher review queue.

The Evaluator (Phase 4) writes a row here whenever a short-answer grade is
low-confidence (score < 0.4 AND confidence < 0.7). Teachers review the queue
and can override the grade, which resolves the row.
"""

from __future__ import annotations

import enum

from sqlalchemy import Enum as SQLEnum, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantScoped, UUIDPk


class FlagStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"


class FlaggedAnswer(Base, UUIDPk, TenantScoped):
    __tablename__ = "flagged_answers"

    quiz_attempt_id: Mapped[str] = mapped_column(String(36), index=True)
    quiz_id: Mapped[str] = mapped_column(String(36), index=True)
    student_id: Mapped[str] = mapped_column(String(36), index=True)
    class_id: Mapped[str | None] = mapped_column(String(36), index=True, default=None)

    question_text: Mapped[str] = mapped_column(Text)
    student_answer: Mapped[str] = mapped_column(Text)
    expected_answer: Mapped[str | None] = mapped_column(Text, default=None)

    ai_score: Mapped[float | None] = mapped_column(Float, default=None)
    ai_confidence: Mapped[float | None] = mapped_column(Float, default=None)
    flag_reason: Mapped[str] = mapped_column(String(255), default="low_confidence")

    status: Mapped[FlagStatus] = mapped_column(
        SQLEnum(FlagStatus, name="flag_status"), default=FlagStatus.open
    )
    override_score: Mapped[float | None] = mapped_column(Float, default=None)
    override_feedback: Mapped[str | None] = mapped_column(Text, default=None)
    resolved_by_teacher_id: Mapped[str | None] = mapped_column(String(36), default=None)
