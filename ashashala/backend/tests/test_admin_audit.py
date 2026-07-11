"""Cross-tenant audit viewer (#8, master doc) — GET /admin/audit. Unlike the
school-scoped GET /school/audit, this route is Super Admin-only and unfiltered
by default since `AuditLog` isn't `TenantScoped` (see app/models/audit.py)."""

import pytest

from app.db.tenant_filter import tenant_bypass
from app.models.user import UserRole
from app.services.audit_service import record_audit
from tests.conftest import login, make_school, make_user


async def _seed(db):
    school_a = await make_school(db, name="School A")
    school_b = await make_school(db, name="School B")
    super_admin = await make_user(db, role=UserRole.super_admin, school_id=None, email="super_aud@x.test")
    school_admin = await make_user(db, role=UserRole.school_admin, school_id=school_a.id, email="sadmin_aud@x.test")

    with tenant_bypass():
        await record_audit(db, action="SCHOOL_CREATE", actor=super_admin, school_id=school_a.id,
                           target_type="school", target_id=school_a.id)
        await record_audit(db, action="SCHOOL_CREATE", actor=super_admin, school_id=school_b.id,
                           target_type="school", target_id=school_b.id)
        await record_audit(db, action="USER_UPDATE", actor=school_admin, school_id=school_a.id,
                           target_type="user", target_id=school_admin.id)
        await db.commit()
    return school_a, school_b, super_admin, school_admin


@pytest.mark.asyncio
async def test_audit_viewer_sees_all_schools_unfiltered(client, db):
    school_a, school_b, super_admin, school_admin = await _seed(db)
    headers = await login(client, "super_aud@x.test")

    resp = await client.get("/api/v1/admin/audit", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    actions = {item["action"] for item in body["items"]}
    assert "SCHOOL_CREATE" in actions
    assert "USER_UPDATE" in actions
    school_ids = {item["school_id"] for item in body["items"]}
    assert school_a.id in school_ids
    assert school_b.id in school_ids


@pytest.mark.asyncio
async def test_audit_viewer_filters_by_school_id(client, db):
    school_a, school_b, super_admin, school_admin = await _seed(db)
    headers = await login(client, "super_aud@x.test")

    resp = await client.get(f"/api/v1/admin/audit?school_id={school_a.id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert all(item["school_id"] == school_a.id for item in body["items"])


@pytest.mark.asyncio
async def test_audit_viewer_filters_by_action(client, db):
    school_a, school_b, super_admin, school_admin = await _seed(db)
    headers = await login(client, "super_aud@x.test")

    resp = await client.get("/api/v1/admin/audit?action=USER_UPDATE", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["action"] == "USER_UPDATE"


@pytest.mark.asyncio
async def test_audit_viewer_date_range_filter_excludes_out_of_range(client, db):
    school_a, school_b, super_admin, school_admin = await _seed(db)
    headers = await login(client, "super_aud@x.test")

    resp = await client.get("/api/v1/admin/audit?date_from=2099-01-01", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    resp2 = await client.get("/api/v1/admin/audit?date_to=2099-01-01", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["total"] >= 3


@pytest.mark.asyncio
async def test_audit_viewer_rejects_school_admin(client, db):
    school_a, school_b, super_admin, school_admin = await _seed(db)
    headers = await login(client, "sadmin_aud@x.test")

    resp = await client.get("/api/v1/admin/audit", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_viewer_pagination(client, db):
    school_a, school_b, super_admin, school_admin = await _seed(db)
    headers = await login(client, "super_aud@x.test")

    resp = await client.get("/api/v1/admin/audit?limit=2&offset=0", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 3
    assert len(body["items"]) == 2
    assert body["limit"] == 2
    assert body["offset"] == 0
