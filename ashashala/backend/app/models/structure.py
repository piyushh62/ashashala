"""Classes, subjects, and the join tables that connect users to them."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantScoped, UUIDPk


class ClassSection(Base, UUIDPk, TenantScoped):
    __tablename__ = "class_sections"

    name: Mapped[str] = mapped_column(String(128))          # e.g. "6-A"
    grade_level: Mapped[int] = mapped_column(Integer)


class Subject(Base, UUIDPk, TenantScoped):
    __tablename__ = "subjects"

    name: Mapped[str] = mapped_column(String(128))


class TeacherAssignment(Base, UUIDPk, TenantScoped):
    __tablename__ = "teacher_assignments"

    teacher_id: Mapped[str] = mapped_column(String(36), index=True)
    class_id: Mapped[str] = mapped_column(String(36), index=True)
    subject_id: Mapped[str] = mapped_column(String(36), index=True)
    # NULL = active. Non-null records when a mid-year departure/reassignment
    # took effect; it's audit metadata, not a future-scheduled trigger.
    end_date: Mapped[date | None] = mapped_column(Date, default=None)


class Enrollment(Base, UUIDPk, TenantScoped):
    __tablename__ = "enrollments"

    student_id: Mapped[str] = mapped_column(String(36), index=True)
    class_id: Mapped[str] = mapped_column(String(36), index=True)
    # NULL = active. Non-null records when a mid-year class transfer took
    # effect; it's audit metadata, not a future-scheduled trigger.
    end_date: Mapped[date | None] = mapped_column(Date, default=None)


class ParentStudentLink(Base, UUIDPk, TenantScoped):
    __tablename__ = "parent_student_links"

    parent_id: Mapped[str] = mapped_column(String(36), index=True)
    student_id: Mapped[str] = mapped_column(String(36), index=True)
    # Consent captured at link time (compliance).
    consent_given_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
