"""DPDP consent-confirmation gate on parent-student linking — a School Admin
must explicitly confirm guardian consent before POST /school/parent-links
will create the link."""

import pytest

from app.models.user import UserRole
from tests.conftest import login, make_school, make_user


@pytest.mark.asyncio
async def test_link_parent_rejects_missing_consent_confirmation(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="admdpdp1@x.test")
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="pardpdp1@x.test")
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="studpdp1@x.test", grade=6)
    headers = await login(client, "admdpdp1@x.test")

    resp = await client.post("/api/v1/school/parent-links", headers=headers,
                              json={"parent_id": parent.id, "student_id": student.id})
    assert resp.status_code == 422

    resp = await client.post("/api/v1/school/parent-links", headers=headers,
                              json={"parent_id": parent.id, "student_id": student.id,
                                    "consent_confirmed": False})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_link_parent_succeeds_with_consent_confirmed(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="admdpdp2@x.test")
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="pardpdp2@x.test")
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="studpdp2@x.test", grade=6)
    headers = await login(client, "admdpdp2@x.test")

    resp = await client.post("/api/v1/school/parent-links", headers=headers,
                              json={"parent_id": parent.id, "student_id": student.id,
                                    "consent_confirmed": True})
    assert resp.status_code == 200
    assert "id" in resp.json()
