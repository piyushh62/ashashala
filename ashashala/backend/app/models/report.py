"""Reporting Agent output — one weekly/monthly narrative per student."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, JSON, Enum as SQLEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantScoped, UUIDPk


class ReportStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"
    sent = "sent"


class Report(Base, UUIDPk, TenantScoped):
    __tablename__ = "reports"

    student_id: Mapped[str] = mapped_column(String(36), index=True)
    period_start: Mapped[date] = mapped_column(Date, index=True)
    period_end: Mapped[date] = mapped_column(Date)
    mastery_snapshot_json: Mapped[list] = mapped_column(JSON, default=list)
    quiz_score_trend_json: Mapped[list] = mapped_column(JSON, default=list)
    teacher_notes: Mapped[str | None] = mapped_column(Text, default=None)
    narrative: Mapped[str] = mapped_column(Text)
    status: Mapped[ReportStatus] = mapped_column(
        SQLEnum(ReportStatus, name="report_status"), default=ReportStatus.draft
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
