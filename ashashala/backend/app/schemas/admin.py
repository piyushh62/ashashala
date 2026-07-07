"""Super-admin schemas (schools + platform)."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class SchoolCreate(BaseModel):
    name: str
    address: str | None = None
    timezone: str = "Asia/Kolkata"
    features_json: dict | None = None


class SchoolUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    is_active: bool | None = None
    features_json: dict | None = None


class SchoolOut(BaseModel):
    id: str
    name: str
    address: str | None
    is_active: bool
    features_json: dict
    timezone: str

    model_config = {"from_attributes": True}


class SchoolAdminCreate(BaseModel):
    name: str
    email: EmailStr


class TempPasswordResponse(BaseModel):
    user_id: str
    email: EmailStr
    temp_password: str


class TokenTrendDay(BaseModel):
    day: str
    tokens: int
    calls: int


class PlatformDashboard(BaseModel):
    active_schools: int
    total_users: int
    tokens_today_by_school: dict[str, int]
    error_rate: float
    tokens_by_day: list[TokenTrendDay] = Field(default_factory=list)


class SchoolDashboardOut(BaseModel):
    school_id: str
    teachers: int
    students: int
    classes: int
    avg_mastery: float
