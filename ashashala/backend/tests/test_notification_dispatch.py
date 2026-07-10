"""Notification dispatch pipeline — pluggable sms/whatsapp sender (log-only
stub for now) and the `dispatch_pending_notifications` job APScheduler polls.
"""

import pytest
from sqlalchemy import select

from app.models.notification import DispatchStatus, Notification, NotificationChannel
from app.models.user import UserRole
from app.services.notification_dispatch import dispatch_pending_notifications
from app.services.notification_service import notify
from tests.conftest import make_school, make_user


@pytest.mark.asyncio
async def test_in_app_notification_is_immediately_sent(db):
    """Regression guard: the 7 pre-existing call sites don't pass `channel`,
    so they must keep behaving exactly like before this phase."""
    school = await make_school(db)
    user = await make_user(db, role=UserRole.student, school_id=school.id, email="n1@x.test")

    await notify(db, user_id=user.id, school_id=school.id, type="test", title="Hi")
    await db.commit()

    row = (await db.execute(select(Notification).where(Notification.user_id == user.id))).scalar_one()
    assert row.channel == NotificationChannel.in_app
    assert row.dispatch_status == DispatchStatus.sent
    assert row.dispatched_at is not None


@pytest.mark.asyncio
async def test_sms_notification_starts_pending(db):
    school = await make_school(db)
    user = await make_user(db, role=UserRole.student, school_id=school.id, email="n2@x.test",
                           phone_number="+911234567890")

    await notify(db, user_id=user.id, school_id=school.id, type="test", title="Hi",
                channel=NotificationChannel.sms)
    await db.commit()

    row = (await db.execute(select(Notification).where(Notification.user_id == user.id))).scalar_one()
    assert row.channel == NotificationChannel.sms
    assert row.dispatch_status == DispatchStatus.pending
    assert row.dispatched_at is None


@pytest.mark.asyncio
async def test_dispatch_sends_pending_sms_with_phone_number(db, caplog):
    school = await make_school(db)
    user = await make_user(db, role=UserRole.student, school_id=school.id, email="n3@x.test",
                           phone_number="+911234567890")
    await notify(db, user_id=user.id, school_id=school.id, type="test", title="Quiz ready",
                body="Your quiz is ready", channel=NotificationChannel.sms)
    await db.commit()

    with caplog.at_level("INFO"):
        count = await dispatch_pending_notifications(db)
    assert count == 1
    assert any("Would send SMS" in r.message for r in caplog.records)

    row = (await db.execute(select(Notification).where(Notification.user_id == user.id))).scalar_one()
    assert row.dispatch_status == DispatchStatus.sent
    assert row.dispatched_at is not None
    assert row.dispatch_error is None


@pytest.mark.asyncio
async def test_dispatch_sends_pending_whatsapp_with_phone_number(db, caplog):
    school = await make_school(db)
    user = await make_user(db, role=UserRole.student, school_id=school.id, email="n4@x.test",
                           phone_number="+911234567890")
    await notify(db, user_id=user.id, school_id=school.id, type="test", title="Quiz ready",
                channel=NotificationChannel.whatsapp)
    await db.commit()

    with caplog.at_level("INFO"):
        count = await dispatch_pending_notifications(db)
    assert count == 1
    assert any("Would send WhatsApp" in r.message for r in caplog.records)

    row = (await db.execute(select(Notification).where(Notification.user_id == user.id))).scalar_one()
    assert row.dispatch_status == DispatchStatus.sent


@pytest.mark.asyncio
async def test_dispatch_fails_when_recipient_has_no_phone_number(db):
    school = await make_school(db)
    user = await make_user(db, role=UserRole.student, school_id=school.id, email="n5@x.test")
    await notify(db, user_id=user.id, school_id=school.id, type="test", title="Quiz ready",
                channel=NotificationChannel.sms)
    await db.commit()

    count = await dispatch_pending_notifications(db)
    assert count == 1

    row = (await db.execute(select(Notification).where(Notification.user_id == user.id))).scalar_one()
    assert row.dispatch_status == DispatchStatus.failed
    assert row.dispatch_error == "Recipient has no phone_number on file"


@pytest.mark.asyncio
async def test_dispatch_with_nothing_pending_is_noop(db):
    count = await dispatch_pending_notifications(db)
    assert count == 0
