"""Teacher-authored Assignments — a due-dated task backed by an
auto-generated Quiz Master quiz (Assignment Builder, master doc §16.5).

Distinct from `TeacherAssignment` (structure.py — the teacher/class/subject
staffing join table); this `Assignment` is student-facing homework.
"""

from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import Date, Enum as SQLEnum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantScoped, UUIDPk


class AssignmentStatus(str, enum.Enum):
    draft = "draft"
    published = "published"


class Assignment(Base, UUIDPk, TenantScoped):
    __tablename__ = "assignments"

    teacher_id: Mapped[str] = mapped_column(String(36), index=True)
    class_id: Mapped[str] = mapped_column(String(36), index=True)
    subject_id: Mapped[str | None] = mapped_column(String(36), default=None)
    topic: Mapped[str] = mapped_column(String(255))
    # The Quiz Master-generated quiz backing this assignment; submission count
    # is derived at read time from QuizAttempt rows, not stored.
    quiz_id: Mapped[str | None] = mapped_column(String(36), default=None)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[AssignmentStatus] = mapped_column(
        SQLEnum(AssignmentStatus, name="assignment_status"), default=AssignmentStatus.draft
    )
