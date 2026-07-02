"""Chat, quizzes, attempts, and mastery progress."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum as SQLEnum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantScoped, UUIDPk, utcnow


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class QuizStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"


class ChatSession(Base, UUIDPk, TenantScoped):
    __tablename__ = "chat_sessions"

    student_id: Mapped[str] = mapped_column(String(36), index=True)
    class_id: Mapped[str] = mapped_column(String(36), index=True)
    subject_id: Mapped[str | None] = mapped_column(String(36), default=None)


class Message(Base, UUIDPk, TenantScoped):
    __tablename__ = "messages"

    session_id: Mapped[str] = mapped_column(String(36), index=True)
    role: Mapped[MessageRole] = mapped_column(SQLEnum(MessageRole, name="message_role"))
    content: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[list | None] = mapped_column(JSON, default=None)
    model_role_used: Mapped[str | None] = mapped_column(String(64), default=None)
    provider_used: Mapped[str | None] = mapped_column(String(32), default=None)


class Quiz(Base, UUIDPk, TenantScoped):
    __tablename__ = "quizzes"

    class_id: Mapped[str] = mapped_column(String(36), index=True)
    subject_id: Mapped[str | None] = mapped_column(String(36), default=None)
    topic: Mapped[str] = mapped_column(String(255))
    questions_json: Mapped[list] = mapped_column(JSON, default=list)
    created_by_teacher_id: Mapped[str | None] = mapped_column(String(36), default=None)
    status: Mapped[QuizStatus] = mapped_column(
        SQLEnum(QuizStatus, name="quiz_status"), default=QuizStatus.draft
    )


class QuizAttempt(Base, UUIDPk, TenantScoped):
    __tablename__ = "quiz_attempts"

    quiz_id: Mapped[str] = mapped_column(String(36), index=True)
    student_id: Mapped[str] = mapped_column(String(36), index=True)
    answers_json: Mapped[list] = mapped_column(JSON, default=list)
    score: Mapped[float | None] = mapped_column(Float, default=None)
    feedback_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProgressRecord(Base, UUIDPk, TenantScoped):
    __tablename__ = "progress_records"

    student_id: Mapped[str] = mapped_column(String(36), index=True)
    subject_id: Mapped[str | None] = mapped_column(String(36), index=True, default=None)
    topic: Mapped[str] = mapped_column(String(255), index=True)
    mastery_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    last_reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
