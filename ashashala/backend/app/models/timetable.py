"""Regular (weekly) and exam timetables."""

from __future__ import annotations

from datetime import date, time

from sqlalchemy import Date, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantScoped, UUIDPk


class Timetable(Base, UUIDPk, TenantScoped):
    __tablename__ = "timetables"

    teacher_id: Mapped[str] = mapped_column(String(36), index=True)
    class_id: Mapped[str] = mapped_column(String(36), index=True)
    subject_id: Mapped[str] = mapped_column(String(36), index=True)
    day_of_week: Mapped[int] = mapped_column(Integer)   # 0=Mon .. 5=Sat
    period_number: Mapped[int] = mapped_column(Integer)
    room: Mapped[str | None] = mapped_column(String(64), default=None)
    topic: Mapped[str | None] = mapped_column(String(255), default=None)


class ExamTimetable(Base, UUIDPk, TenantScoped):
    __tablename__ = "exam_timetables"

    class_id: Mapped[str] = mapped_column(String(36), index=True)
    subject_id: Mapped[str] = mapped_column(String(36), index=True)
    exam_name: Mapped[str] = mapped_column(String(255))
    exam_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time | None] = mapped_column(Time, default=None)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    syllabus_ref: Mapped[str | None] = mapped_column(String(512), default=None)
