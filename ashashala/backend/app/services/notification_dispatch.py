"""Pluggable SMS/WhatsApp dispatch — polls pending `Notification` rows and
hands each to a `NotificationSender`. Only a log-only stub sender is wired up
today (no Twilio/WhatsApp Business API credentials); swapping in a real
provider later is a one-file change to `_SENDERS`.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import DispatchStatus, Notification, NotificationChannel
from app.models.user import User

logger = logging.getLogger(__name__)


class NotificationSender(Protocol):
    async def send(self, *, phone_number: str, title: str, body: str | None) -> tuple[bool, str | None]:
        """Return (success, error_message)."""
        ...


class LogSender:
    """Stub sender used for every channel today: logs what would be sent and
    reports success. No real provider call."""

    def __init__(self, channel_label: str) -> None:
        self._channel_label = channel_label

    async def send(self, *, phone_number: str, title: str, body: str | None) -> tuple[bool, str | None]:
        logger.info("Would send %s to %s: %s — %s", self._channel_label, phone_number, title, body or "")
        return True, None


_SENDERS: dict[NotificationChannel, NotificationSender] = {
    NotificationChannel.sms: LogSender("SMS"),
    NotificationChannel.whatsapp: LogSender("WhatsApp"),
}


async def dispatch_pending_notifications(db: AsyncSession, *, batch_size: int = 100) -> int:
    """Send every pending sms/whatsapp notification and commit the result.

    Returns the number of rows processed.
    """
    rows = (await db.execute(
        select(Notification).where(Notification.dispatch_status == DispatchStatus.pending).limit(batch_size)
    )).scalars().all()
    if not rows:
        return 0

    users = {u.id: u for u in (await db.execute(
        select(User).where(User.id.in_({r.user_id for r in rows}))
    )).scalars().all()}

    for row in rows:
        sender = _SENDERS.get(row.channel)
        user = users.get(row.user_id)
        if sender is None:
            row.dispatch_status = DispatchStatus.failed
            row.dispatch_error = f"No sender registered for channel '{row.channel.value}'"
        elif not user or not user.phone_number:
            row.dispatch_status = DispatchStatus.failed
            row.dispatch_error = "Recipient has no phone_number on file"
        else:
            success, error = await sender.send(phone_number=user.phone_number, title=row.title, body=row.body)
            if success:
                row.dispatch_status = DispatchStatus.sent
                row.dispatched_at = datetime.now(UTC)
            else:
                row.dispatch_status = DispatchStatus.failed
                row.dispatch_error = error
        db.add(row)

    await db.commit()
    return len(rows)
