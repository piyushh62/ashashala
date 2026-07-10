"""Per-user notifications.

`notify(...)` only adds the row (no independent commit) — every call site
already ends its request with `record_audit(...)`, which commits, so the
notification lands in the same transaction as the mutation it describes.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import DispatchStatus, Notification, NotificationChannel


async def notify(
    db: AsyncSession,
    *,
    user_id: str,
    school_id: str,
    type: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
    channel: NotificationChannel = NotificationChannel.in_app,
) -> None:
    # in_app rows are "sent" the instant they're persisted — delivery is just
    # being polled via GET /notifications. sms/whatsapp start pending and get
    # flipped by the APScheduler dispatch job (notification_dispatch.py).
    is_in_app = channel == NotificationChannel.in_app
    db.add(Notification(
        user_id=user_id, school_id=school_id, type=type,
        title=title, body=body, link=link, channel=channel,
        dispatch_status=DispatchStatus.sent if is_in_app else DispatchStatus.pending,
        dispatched_at=datetime.now(UTC) if is_in_app else None,
    ))
