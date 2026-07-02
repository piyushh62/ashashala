"""RBAC — role guards enforce the permission matrix."""

import pytest

from app.models.user import UserRole
from tests.conftest import login, make_school, make_user


@pytest.mark.asyncio
async def test_unauthenticated_is_401(client):
    resp = await client.get("/api/v1/school/users")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_student_cannot_access_school_admin_route(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.student, school_id=school.id, email="stu@x.test")
    headers = await login(client, "stu@x.test")
    resp = await client.get("/api/v1/school/users", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_can_create_class(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="adm@x.test")
    headers = await login(client, "adm@x.test")
    resp = await client.post("/api/v1/school/classes", headers=headers,
                             json={"name": "6-A", "grade_level": 6})
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "6-A"


@pytest.mark.asyncio
async def test_teacher_cannot_create_school(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.teacher, school_id=school.id, email="t@x.test")
    headers = await login(client, "t@x.test")
    resp = await client.post("/api/v1/admin/schools", headers=headers, json={"name": "X"})
    assert resp.status_code == 403
