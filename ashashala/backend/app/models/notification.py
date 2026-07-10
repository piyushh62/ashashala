"""Notification — per-user inbox rows surfaced in the top-bar bell.

Created alongside existing mutations (teacher assignment, enrollment, parent
link, password reset, flagged-answer review, quiz approval) via
`app/services/notification_service.notify()`. Not pushed in real time (no
WebSocket/SSE infra for this) — the frontend polls.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantScoped, UUIDPk


class NotificationChannel(str, enum.Enum):
    in_app = "in_app"
    sms = "sms"
    whatsapp = "whatsapp"
    email = "email"


class DispatchStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class Notification(Base, UUIDPk, TenantScoped):
    __tablename__ = "notifications"

    # created_at (ordering) and id come from UUIDPk.
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    type: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text, default=None)
    link: Mapped[str | None] = mapped_column(String(255), default=None)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    channel: Mapped[NotificationChannel] = mapped_column(
        SQLEnum(NotificationChannel, name="notification_channel"),
        default=NotificationChannel.in_app,
    )
    # in_app rows are "sent" the instant they're persisted (delivery = being
    # polled via GET /notifications); only sms/whatsapp start pending and get
    # flipped by the APScheduler dispatch job (app/services/notification_dispatch.py).
    dispatch_status: Mapped[DispatchStatus] = mapped_column(
        SQLEnum(DispatchStatus, name="notification_dispatch_status"),
        default=DispatchStatus.sent,
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    dispatch_error: Mapped[str | None] = mapped_column(String(512), default=None)
