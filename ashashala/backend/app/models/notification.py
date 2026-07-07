"""Notification — per-user inbox rows surfaced in the top-bar bell.

Created alongside existing mutations (teacher assignment, enrollment, parent
link, password reset, flagged-answer review, quiz approval) via
`app/services/notification_service.notify()`. Not pushed in real time (no
WebSocket/SSE infra for this) — the frontend polls.
"""

from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantScoped, UUIDPk


class Notification(Base, UUIDPk, TenantScoped):
    __tablename__ = "notifications"

    # created_at (ordering) and id come from UUIDPk.
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    type: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text, default=None)
    link: Mapped[str | None] = mapped_column(String(255), default=None)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
