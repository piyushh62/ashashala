"""Teacher schemas (materials, timetables)."""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.auth.password import validate_password_complexity
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
    topic: str | None = None


class TimetableOut(BaseModel):
    id: str
    teacher_id: str
    class_id: str
    subject_id: str
    day_of_week: int
    period_number: int
    room: str | None
    topic: str | None = None

    model_config = {"from_attributes": True}


class TimetableUpdate(BaseModel):
    topic: str | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    period_number: int | None = Field(default=None, ge=1)
    room: str | None = None


class TimetableAiSuggestRequest(BaseModel):
    class_id: str
    subject_id: str
    periods_per_week: int = Field(ge=1, le=10)


class TimetableSlotOut(BaseModel):
    day_of_week: int
    period_number: int
    room: str | None = None


class TimetableOptionOut(BaseModel):
    option_id: str
    strategy: str
    rationale: str
    slots: list[TimetableSlotOut]


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


class FlaggedAnswerOut(BaseModel):
    id: str
    quiz_attempt_id: str
    quiz_id: str
    student_id: str
    question_text: str
    student_answer: str
    expected_answer: str | None = None
    ai_score: float | None = None
    ai_confidence: float | None = None
    flag_reason: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FlaggedAnswerOverride(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    feedback: str | None = None


class QuizApproval(BaseModel):
    approved: bool
    feedback: str | None = None


class StudentCreate(BaseModel):
    """Body for teacher-initiated student creation (POST /teacher/students).

    Only reachable when the teacher's role has been granted `user:create_student`
    via `RoleCreationRight` — see app/services/rbac_service.py::can_create_role.
    """

    name: str
    email: EmailStr
    password: str | None = Field(default=None, min_length=8)  # auto-generated if omitted
    grade: int | None = None
    interests: str | None = None

    @field_validator("password")
    @classmethod
    def _check_password_complexity(cls, v: str | None) -> str | None:
        return validate_password_complexity(v) if v is not None else v


class ParentCreate(BaseModel):
    """Body for teacher-initiated parent creation + link (POST /teacher/parents)."""

    name: str
    email: EmailStr
    student_id: str
    password: str | None = Field(default=None, min_length=8)

    @field_validator("password")
    @classmethod
    def _check_password_complexity(cls, v: str | None) -> str | None:
        return validate_password_complexity(v) if v is not None else v
