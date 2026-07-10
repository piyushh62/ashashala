"""Per-user notification channel opt-in — read by the Communication Agent to
decide which channels to notify() through."""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantScoped, UUIDPk


class NotificationPreference(Base, UUIDPk, TenantScoped):
    __tablename__ = "notification_preferences"

    user_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
