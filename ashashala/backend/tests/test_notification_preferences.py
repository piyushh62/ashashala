"""Notification channel preferences — get-or-create defaults, partial PATCH,
and the Communication Agent's channel-selection helper."""

import pytest

from app.models.notification import NotificationChannel
from app.models.user import UserRole
from app.services.notification_preference_service import get_enabled_channels
from tests.conftest import login, make_school, make_user


@pytest.mark.asyncio
async def test_get_creates_default_row(client, db):
    school = await make_school(db)
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="np1@x.test")
    headers = await login(client, "np1@x.test")

    resp = await client.get("/api/v1/parent/notification-preferences", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {"in_app_enabled": True, "sms_enabled": False, "whatsapp_enabled": False, "email_enabled": False}


@pytest.mark.asyncio
async def test_patch_updates_specific_channels(client, db):
    school = await make_school(db)
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="np2@x.test")
    headers = await login(client, "np2@x.test")

    await client.get("/api/v1/parent/notification-preferences", headers=headers)
    resp = await client.patch("/api/v1/parent/notification-preferences", headers=headers,
                              json={"sms_enabled": True})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sms_enabled"] is True
    assert body["in_app_enabled"] is True
    assert body["whatsapp_enabled"] is False


@pytest.mark.asyncio
async def test_get_enabled_channels_reflects_stored_prefs(client, db):
    school = await make_school(db)
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="np3@x.test")
    headers = await login(client, "np3@x.test")
    await client.patch("/api/v1/parent/notification-preferences", headers=headers,
                       json={"whatsapp_enabled": True, "in_app_enabled": False})

    channels = await get_enabled_channels(db, user_id=parent.id, school_id=school.id)
    assert set(channels) == {NotificationChannel.whatsapp}


@pytest.mark.asyncio
async def test_get_enabled_channels_defaults_to_in_app_without_row(db):
    school = await make_school(db)
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="np4@x.test")

    channels = await get_enabled_channels(db, user_id=parent.id, school_id=school.id)
    assert channels == [NotificationChannel.in_app]
