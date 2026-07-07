"""User model — all five roles in one table."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPk


class UserRole(str, enum.Enum):
    super_admin = "super_admin"
    school_admin = "school_admin"
    teacher = "teacher"
    student = "student"
    parent = "parent"


class User(Base, UUIDPk):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole, name="user_role"))

    # NULL for super_admin. NOT TenantScoped — the tenant filter must not hide
    # users during login/onboarding; role routes scope users explicitly.
    school_id: Mapped[str | None] = mapped_column(String(36), index=True, default=None)

    interests: Mapped[str | None] = mapped_column(String(512), default=None)  # student personalisation
    grade: Mapped[int | None] = mapped_column(Integer, default=None)          # students
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Bumped to "now" to instantly invalidate every outstanding access token
    # and refresh token issued before this timestamp (password reset, admin
    # reset, deactivation, logout-all). NULL = no forced invalidation yet.
    tokens_valid_after: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
