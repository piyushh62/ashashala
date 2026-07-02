"""Teacher schemas (materials, timetables)."""

from __future__ import annotations

from datetime import date, time

from pydantic import BaseModel, Field

from app.models.document import DocStatus, SourceType


class MaterialUrlCreate(BaseModel):
    class_id: str
    subject_id: str | None = None
    url: str


class MaterialYoutubeCreate(BaseModel):
    class_id: str
    subject_id: str | None = None
    url: str


class DocumentOut(BaseModel):
    id: str
    filename: str
    source_type: SourceType
    source_ref: str | None
    storage_url: str | None
    status: DocStatus
    class_id: str
    subject_id: str | None

    model_config = {"from_attributes": True}


class TimetableCreate(BaseModel):
    class_id: str
    subject_id: str
    day_of_week: int = Field(ge=0, le=6)
    period_number: int = Field(ge=1)
    room: str | None = None


class TimetableOut(BaseModel):
    id: str
    teacher_id: str
    class_id: str
    subject_id: str
    day_of_week: int
    period_number: int
    room: str | None

    model_config = {"from_attributes": True}


class ExamTimetableCreate(BaseModel):
    class_id: str
    subject_id: str
    exam_name: str
    exam_date: date
    start_time: time | None = None
    duration_minutes: int | None = None
    syllabus_ref: str | None = None


class ExamTimetableOut(BaseModel):
    id: str
    class_id: str
    subject_id: str
    exam_name: str
    exam_date: date
    start_time: time | None
    duration_minutes: int | None
    syllabus_ref: str | None

    model_config = {"from_attributes": True}
