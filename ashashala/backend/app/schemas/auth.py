"""Auth request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.auth.password import validate_password_complexity


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr
    new_password: str = Field(min_length=8)

    _validate_complexity = field_validator("new_password")(validate_password_complexity)


class MeResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    school_id: str | None = None
    grade: int | None = None
    interests: str | None = None
