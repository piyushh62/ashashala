"""Audit — state-changing actions and sensitive reads produce audit rows."""

import pytest
from sqlalchemy import select

from app.db.tenant_filter import tenant_bypass
from app.models.audit import AuditLog
from app.models.structure import ParentStudentLink
from app.models.user import UserRole
from tests.conftest import login, make_school, make_user


async def _audit_actions(db) -> list[str]:
    with tenant_bypass():
        rows = (await db.execute(select(AuditLog))).scalars().all()
    return [r.action for r in rows]


@pytest.mark.asyncio
async def test_login_success_is_audited(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="adm@x.test")
    await login(client, "adm@x.test")
    assert "LOGIN_SUCCESS" in await _audit_actions(db)


@pytest.mark.asyncio
async def test_login_failure_is_audited(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="adm2@x.test")
    resp = await client.post("/api/v1/auth/login", json={"email": "adm2@x.test", "password": "wrong"})
    assert resp.status_code == 401
    assert "LOGIN_FAILURE" in await _audit_actions(db)


@pytest.mark.asyncio
async def test_class_create_is_audited(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="adm3@x.test")
    headers = await login(client, "adm3@x.test")
    await client.post("/api/v1/school/classes", headers=headers, json={"name": "7-B", "grade_level": 7})
    assert "CLASS_CREATE" in await _audit_actions(db)


@pytest.mark.asyncio
async def test_parent_view_child_is_audited(client, db):
    school = await make_school(db)
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="p@x.test")
    child = await make_user(db, role=UserRole.student, school_id=school.id, email="c@x.test")
    with tenant_bypass():
        db.add(ParentStudentLink(parent_id=parent.id, student_id=child.id, school_id=school.id))
        await db.commit()
    headers = await login(client, "p@x.test")
    await client.get(f"/api/v1/parent/children/{child.id}/dashboard", headers=headers)
    assert "PARENT_VIEW_CHILD" in await _audit_actions(db)
