"""Immutable audit log (Section 5)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPk, utcnow


class AuditLog(Base, UUIDPk):
    __tablename__ = "audit_logs"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), index=True, default=None)
    actor_role: Mapped[str | None] = mapped_column(String(32), default=None)
    # NULL for super-admin platform actions. Not TenantScoped: the school-admin
    # audit viewer filters explicitly; super-admin reads across schools.
    school_id: Mapped[str | None] = mapped_column(String(36), index=True, default=None)

    action: Mapped[str] = mapped_column(String(64), index=True)
    target_type: Mapped[str | None] = mapped_column(String(64), default=None)
    # Wide enough to hold an email (LOGIN_FAILURE target) — max email is 320 chars.
    target_id: Mapped[str | None] = mapped_column(String(320), default=None)

    ip: Mapped[str | None] = mapped_column(String(64), default=None)
    user_agent: Mapped[str | None] = mapped_column(String(512), default=None)
    request_id: Mapped[str | None] = mapped_column(String(64), default=None)
    payload_hash: Mapped[str | None] = mapped_column(String(64), default=None)

    status: Mapped[str] = mapped_column(String(16), default="success")  # success|failure
    error_msg: Mapped[str | None] = mapped_column(Text, default=None)
