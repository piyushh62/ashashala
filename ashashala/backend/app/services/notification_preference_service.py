"""Per-user notification channel preferences — read by the Communication
Agent to decide which channels to notify() through."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationChannel
from app.models.notification_preference import NotificationPreference

_CHANNEL_FIELDS: dict[NotificationChannel, str] = {
    NotificationChannel.in_app: "in_app_enabled",
    NotificationChannel.sms: "sms_enabled",
    NotificationChannel.whatsapp: "whatsapp_enabled",
    NotificationChannel.email: "email_enabled",
}


async def get_or_create_preference(
    db: AsyncSession, *, user_id: str, school_id: str
) -> NotificationPreference:
    pref = (await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )).scalar_one_or_none()
    if pref is None:
        pref = NotificationPreference(user_id=user_id, school_id=school_id)
        db.add(pref)
        await db.flush()
    return pref


async def get_enabled_channels(
    db: AsyncSession, *, user_id: str, school_id: str
) -> list[NotificationChannel]:
    pref = (await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )).scalar_one_or_none()
    if pref is None:
        return [NotificationChannel.in_app]
    enabled = [ch for ch, field in _CHANNEL_FIELDS.items() if getattr(pref, field)]
    return enabled or [NotificationChannel.in_app]
