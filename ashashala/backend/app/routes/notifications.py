"""Notification inbox — available to every authenticated role."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.deps import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationListOut, NotificationOut

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListOut)
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListOut:
    stmt = select(Notification).where(Notification.user_id == me.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    unread_count = (await db.execute(
        select(func.count()).select_from(Notification)
        .where(Notification.user_id == me.id, Notification.is_read.is_(False))
    )).scalar_one()

    return NotificationListOut(
        items=[NotificationOut.model_validate(r) for r in rows],
        unread_count=unread_count,
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: str,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationOut:
    row = await db.get(Notification, notification_id)
    if row is None or row.user_id != me.id:
        raise NotFoundError("Notification", notification_id)
    row.is_read = True
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return NotificationOut.model_validate(row)


@router.post("/read-all")
async def mark_all_read(
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = (await db.execute(
        select(Notification).where(Notification.user_id == me.id, Notification.is_read.is_(False))
    )).scalars().all()
    for row in rows:
        row.is_read = True
        db.add(row)
    await db.commit()
    return {"status": "ok", "count": len(rows)}
