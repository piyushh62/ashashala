"""Reporting Agent schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.report import ReportStatus


class ReportOut(BaseModel):
    id: str
    student_id: str
    period_start: date
    period_end: date
    mastery_snapshot_json: list
    quiz_score_trend_json: list
    teacher_notes: str | None
    narrative: str
    status: ReportStatus
    sent_at: datetime | None

    model_config = {"from_attributes": True}


class ReportPatch(BaseModel):
    teacher_notes: str = Field(min_length=1, max_length=2000)
