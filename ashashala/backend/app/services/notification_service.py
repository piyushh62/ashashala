"""Per-user notifications.

`notify(...)` only adds the row (no independent commit) — every call site
already ends its request with `record_audit(...)`, which commits, so the
notification lands in the same transaction as the mutation it describes.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def notify(
    db: AsyncSession,
    *,
    user_id: str,
    school_id: str,
    type: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
) -> None:
    db.add(Notification(
        user_id=user_id, school_id=school_id, type=type,
        title=title, body=body, link=link,
    ))
