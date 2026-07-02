"""School-admin schemas (users, classes, subjects, links)."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    role: UserRole
    password: str | None = Field(default=None, min_length=8)  # auto-generated if omitted
    grade: int | None = None
    interests: str | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    grade: int | None = None
    interests: str | None = None


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: UserRole
    school_id: str | None
    is_active: bool
    grade: int | None = None

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


class EnrollmentCreate(BaseModel):
    student_id: str
    class_id: str


class ParentLinkCreate(BaseModel):
    parent_id: str
    student_id: str


class IdResponse(BaseModel):
    id: str
