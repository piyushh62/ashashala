"""School-admin schemas (users, classes, subjects, links)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.auth.password import validate_password_complexity
from app.models.user import UserRole


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    role: UserRole
    password: str | None = Field(default=None, min_length=8)  # auto-generated if omitted
    grade: int | None = None
    interests: str | None = None

    @field_validator("password")
    @classmethod
    def _check_password_complexity(cls, v: str | None) -> str | None:
        return validate_password_complexity(v) if v is not None else v


class UserUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    grade: int | None = None
    interests: str | None = None
    phone_number: str | None = None


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: UserRole
    school_id: str | None
    is_active: bool
    grade: int | None = None
    phone_number: str | None = None

    model_config = {"from_attributes": True}


class UserCreatedResponse(BaseModel):
    user: UserOut
    temp_password: str | None = None


class ClassCreate(BaseModel):
    name: str
    grade_level: int


class ClassOut(BaseModel):
    id: str
    name: str
    grade_level: int

    model_config = {"from_attributes": True}


class SubjectCreate(BaseModel):
    name: str


class SubjectOut(BaseModel):
    id: str
    name: str

    model_config = {"from_attributes": True}


class TeacherAssignmentCreate(BaseModel):
    teacher_id: str
    class_id: str
    subject_id: str


class TeacherAssignmentOut(BaseModel):
    id: str
    teacher_id: str
    teacher_name: str
    class_id: str
    class_name: str
    subject_id: str
    subject_name: str
    end_date: date | None = None


class TeacherAssignmentUpdate(BaseModel):
    end_date: date | None = None


class EnrollmentCreate(BaseModel):
    student_id: str
    class_id: str


class EnrollmentOut(BaseModel):
    id: str
    student_id: str
    student_name: str
    class_id: str
    class_name: str
    end_date: date | None = None


class EnrollmentUpdate(BaseModel):
    end_date: date | None = None


class ParentLinkCreate(BaseModel):
    parent_id: str
    student_id: str


class ParentLinkOut(BaseModel):
    id: str
    parent_id: str
    parent_name: str
    student_id: str
    student_name: str


class IdResponse(BaseModel):
    id: str


class TempPasswordResponse(BaseModel):
    temp_password: str


class AtRiskStudentOut(BaseModel):
    student_id: str
    student_name: str
    avg_mastery: float


class ClassMasteryOut(BaseModel):
    class_id: str
    class_name: str
    avg_mastery: float
    student_count: int
