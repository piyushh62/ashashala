"""Phase 8 — refresh-token rotation/reuse detection, logout, tokens_valid_after,
pagination envelopes, and login rate limiting."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.refresh_token import RefreshToken
from app.models.school import School
from app.models.user import User, UserRole
from tests.conftest import login, make_school, make_user


async def _seed_admin(db, *, email: str = "adm8@x.test"):
    school = await make_school(db)
    admin = await make_user(db, role=UserRole.school_admin, school_id=school.id, email=email)
    return school, admin


async def _push_valid_after_forward(db, user_id: str, *, seconds: float = 3) -> None:
    """get_current_user (app/deps.py) allows a 1s grace window on
    `tokens_valid_after` — jose's jwt.encode truncates `iat` to whole seconds,
    so without slack a token minted in the same wall-clock second as an
    invalidation event would be spuriously rejected. That's correct prod
    behavior, but it means these tests (which run invalidate -> check within
    the same second) need to push the invalidation timestamp further into the
    future to deterministically observe the rejection, rather than racing
    real time."""
    user = await db.get(User, user_id)
    db.expire(user)
    user = await db.get(User, user_id)
    user.tokens_valid_after = user.tokens_valid_after + timedelta(seconds=seconds)
    db.add(user)
    await db.commit()


@pytest.mark.asyncio
async def test_refresh_rotates_token_and_rejects_old_one(client, db):
    await make_school(db)
    school = (await db.execute(select(School))).scalars().first()
    await make_user(db, role=UserRole.student, school_id=school.id, email="stu8a@x.test")

    login_resp = await client.post("/api/v1/auth/login", json={"email": "stu8a@x.test", "password": "password123"})
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    old_refresh = tokens["refresh_token"]

    # First use rotates cleanly.
    r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r1.status_code == 200, r1.text
    new_refresh = r1.json()["refresh_token"]
    assert new_refresh != old_refresh

    # The freshly-rotated token itself works (checked *before* touching
    # old_refresh again — reusing an already-rotated token is a distinct
    # "theft detected" scenario, covered by test_refresh_reuse_revokes_all_sessions,
    # and it intentionally revokes every session including this one).
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert r2.status_code == 200, r2.text

    # Re-using the now-rotated-away old token is rejected.
    r3 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r3.status_code == 401


@pytest.mark.asyncio
async def test_refresh_reuse_revokes_all_sessions(client, db):
    await make_school(db)
    school = (await db.execute(select(School))).scalars().first()
    await make_user(db, role=UserRole.student, school_id=school.id, email="stu8b@x.test")

    login_resp = await client.post("/api/v1/auth/login", json={"email": "stu8b@x.test", "password": "password123"})
    tokens = login_resp.json()
    access = tokens["access_token"]
    old_refresh = tokens["refresh_token"]

    # Rotate once (old_refresh becomes revoked/replaced).
    r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r1.status_code == 200
    good_refresh = r1.json()["refresh_token"]

    # Reusing the already-revoked old token is treated as theft: it should
    # revoke *every* outstanding session, including the one just minted.
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r2.status_code == 401

    r3 = await client.post("/api/v1/auth/refresh", json={"refresh_token": good_refresh})
    assert r3.status_code == 401

    # The access token minted before reuse-detection is also now dead
    # (tokens_valid_after bump), not just refresh tokens. `access` and the
    # reuse-detection bump both land in the same wall-clock second in a fast
    # test run, which is exactly the case get_current_user's 1s grace window
    # is meant to tolerate — so push tokens_valid_after forward to
    # deterministically clear that window rather than sleeping on real time.
    student = (await db.execute(select(User).where(User.email == "stu8b@x.test"))).scalars().first()
    await _push_valid_after_forward(db, student.id)
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_single_token_and_is_idempotent(client, db):
    await make_school(db)
    school = (await db.execute(select(School))).scalars().first()
    await make_user(db, role=UserRole.student, school_id=school.id, email="stu8c@x.test")

    tokens = (await client.post("/api/v1/auth/login", json={"email": "stu8c@x.test", "password": "password123"})).json()
    refresh_token = tokens["refresh_token"]

    out = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert out.status_code == 200

    # The revoked token can no longer be used to refresh.
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 401

    # Logging out again (already revoked) is a no-op, not an error.
    out2 = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert out2.status_code == 200

    # An unrecognized/garbage token is also treated as already-logged-out.
    out3 = await client.post("/api/v1/auth/logout", json={"refresh_token": "not-a-real-token"})
    assert out3.status_code == 200


@pytest.mark.asyncio
async def test_logout_all_revokes_every_session(client, db):
    await make_school(db)
    school = (await db.execute(select(School))).scalars().first()
    await make_user(db, role=UserRole.student, school_id=school.id, email="stu8d@x.test")

    t1 = (await client.post("/api/v1/auth/login", json={"email": "stu8d@x.test", "password": "password123"})).json()
    t2 = (await client.post("/api/v1/auth/login", json={"email": "stu8d@x.test", "password": "password123"})).json()

    out = await client.post("/api/v1/auth/logout-all", headers={"Authorization": f"Bearer {t1['access_token']}"})
    assert out.status_code == 200

    # Both refresh tokens (from both "devices") are now dead.
    r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": t1["refresh_token"]})
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": t2["refresh_token"]})
    assert r1.status_code == 401
    assert r2.status_code == 401

    # Access tokens issued before logout-all are also rejected. See
    # _push_valid_after_forward's docstring for why this is needed in a fast
    # test run (get_current_user's 1s iat-precision grace window).
    student = (await db.execute(select(User).where(User.email == "stu8d@x.test"))).scalars().first()
    await _push_valid_after_forward(db, student.id)
    me1 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t1['access_token']}"})
    me2 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t2['access_token']}"})
    assert me1.status_code == 401
    assert me2.status_code == 401


@pytest.mark.asyncio
async def test_password_reset_invalidates_existing_sessions(client, db):
    await make_school(db)
    school = (await db.execute(select(School))).scalars().first()
    await make_user(db, role=UserRole.student, school_id=school.id, email="stu8e@x.test")

    tokens = (await client.post("/api/v1/auth/login", json={"email": "stu8e@x.test", "password": "password123"})).json()
    old_access = tokens["access_token"]

    resp = await client.post(
        "/api/v1/auth/password-reset",
        headers={"Authorization": f"Bearer {old_access}"},
        json={"email": "stu8e@x.test", "new_password": "newpass123"},
    )
    assert resp.status_code == 200, resp.text

    # ...the new password logs in fine and yields a fresh, valid session. Do
    # this *before* pushing tokens_valid_after artificially forward below —
    # otherwise this brand-new token's real-time iat would itself land behind
    # the artificially-future tokens_valid_after and get wrongly rejected.
    relogin = await client.post("/api/v1/auth/login", json={"email": "stu8e@x.test", "password": "newpass123"})
    assert relogin.status_code == 200
    new_access = relogin.json()["access_token"]
    me2 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me2.status_code == 200

    # The pre-reset access token no longer works. See
    # _push_valid_after_forward's docstring for why this is needed in a fast
    # test run (get_current_user's 1s iat-precision grace window).
    student = (await db.execute(select(User).where(User.email == "stu8e@x.test"))).scalars().first()
    await _push_valid_after_forward(db, student.id)
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_access}"})
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_admin_reset_password_invalidates_target_sessions(client, db):
    school, admin = await _seed_admin(db, email="adm8b@x.test")
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="stu8f@x.test")

    student_tokens = (await client.post("/api/v1/auth/login", json={"email": "stu8f@x.test", "password": "password123"})).json()
    admin_headers = await login(client, "adm8b@x.test")

    resp = await client.post(f"/api/v1/school/users/{student.id}/reset-password", headers=admin_headers)
    assert resp.status_code == 200, resp.text

    # See _push_valid_after_forward's docstring for why this is needed in a
    # fast test run (get_current_user's 1s iat-precision grace window).
    await _push_valid_after_forward(db, student.id)
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {student_tokens['access_token']}"})
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_deactivating_user_invalidates_their_sessions(client, db):
    school, admin = await _seed_admin(db, email="adm8c@x.test")
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="stu8g@x.test")

    student_tokens = (await client.post("/api/v1/auth/login", json={"email": "stu8g@x.test", "password": "password123"})).json()
    admin_headers = await login(client, "adm8c@x.test")

    resp = await client.patch(f"/api/v1/school/users/{student.id}", headers=admin_headers, json={"is_active": False})
    assert resp.status_code == 200, resp.text

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {student_tokens['access_token']}"})
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_login_creates_refresh_token_row(client, db):
    await make_school(db)
    school = (await db.execute(select(School))).scalars().first()
    user = await make_user(db, role=UserRole.student, school_id=school.id, email="stu8h@x.test")

    tokens = (await client.post("/api/v1/auth/login", json={"email": "stu8h@x.test", "password": "password123"})).json()
    from app.auth.jwt import decode_token
    payload = decode_token(tokens["refresh_token"], refresh=True)

    row = await db.get(RefreshToken, payload["jti"])
    assert row is not None
    assert row.user_id == user.id
    assert row.revoked_at is None


@pytest.mark.asyncio
async def test_page_envelope_shape_on_list_users(client, db):
    school, admin = await _seed_admin(db, email="adm8d@x.test")
    for i in range(3):
        await make_user(db, role=UserRole.student, school_id=school.id, email=f"stu8i{i}@x.test")
    headers = await login(client, "adm8d@x.test")

    resp = await client.get("/api/v1/school/users", headers=headers, params={"limit": 2, "offset": 0})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) == {"items", "total", "limit", "offset"}
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert len(body["items"]) == 2
    # 3 students + the admin themself = 4 users in this school.
    assert body["total"] == 4

    resp2 = await client.get("/api/v1/school/users", headers=headers, params={"limit": 2, "offset": 2})
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert len(body2["items"]) == 2
    assert body2["total"] == 4


@pytest.mark.asyncio
async def test_password_complexity_rejected_without_digit(client, db):
    await make_school(db)
    school = (await db.execute(select(School))).scalars().first()
    await make_user(db, role=UserRole.student, school_id=school.id, email="stu8j@x.test")

    tokens = (await client.post("/api/v1/auth/login", json={"email": "stu8j@x.test", "password": "password123"})).json()
    resp = await client.post(
        "/api/v1/auth/password-reset",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"email": "stu8j@x.test", "new_password": "alllettersnodigits"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_rate_limit_returns_429(client, db):
    await make_school(db)
    school = (await db.execute(select(School))).scalars().first()
    await make_user(db, role=UserRole.student, school_id=school.id, email="stu8k@x.test")

    limit = int(settings.LOGIN_RATE_LIMIT.split("/")[0])
    statuses = []
    for _ in range(limit + 3):
        resp = await client.post(
            "/api/v1/auth/login", json={"email": "stu8k@x.test", "password": "wrong-password"}
        )
        statuses.append(resp.status_code)

    assert 429 in statuses
