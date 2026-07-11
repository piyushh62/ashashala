"""Teacher-absence tracking — feeds the Staffing Agent's substitute
suggestions (master doc §5.2: "Teacher marked absent -> Suggests substitute
from available teachers -> Admin approves")."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantScoped, UUIDPk


class TeacherAbsence(Base, UUIDPk, TenantScoped):
    __tablename__ = "teacher_absences"

    teacher_id: Mapped[str] = mapped_column(String(36), index=True)
    absence_date: Mapped[date] = mapped_column(Date, index=True)
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    marked_by_user_id: Mapped[str | None] = mapped_column(String(36), default=None)
