"""Parent access — sees own linked child, blocked from others."""

import pytest

from app.db.tenant_filter import tenant_bypass
from app.models.structure import ParentStudentLink
from app.models.user import UserRole
from tests.conftest import login, make_school, make_user


async def _link(db, *, parent_id, student_id, school_id):
    with tenant_bypass():
        db.add(ParentStudentLink(parent_id=parent_id, student_id=student_id, school_id=school_id))
        await db.commit()


@pytest.mark.asyncio
async def test_parent_sees_own_child(client, db):
    school = await make_school(db)
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="p@x.test")
    child = await make_user(db, role=UserRole.student, school_id=school.id, email="c@x.test", name="Child One")
    await _link(db, parent_id=parent.id, student_id=child.id, school_id=school.id)
    headers = await login(client, "p@x.test")

    resp = await client.get(f"/api/v1/parent/children/{child.id}/dashboard", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["student"]["name"] == "Child One"


@pytest.mark.asyncio
async def test_parent_cannot_see_unlinked_child_403(client, db):
    school = await make_school(db)
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="p2@x.test")
    other = await make_user(db, role=UserRole.student, school_id=school.id, email="other@x.test")
    # No link created.
    headers = await login(client, "p2@x.test")

    resp = await client.get(f"/api/v1/parent/children/{other.id}/dashboard", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_parent_cross_tenant_child_404(client, db):
    school_a = await make_school(db, name="A")
    school_b = await make_school(db, name="B")
    parent = await make_user(db, role=UserRole.parent, school_id=school_a.id, email="p3@x.test")
    foreign = await make_user(db, role=UserRole.student, school_id=school_b.id, email="foreign@x.test")
    headers = await login(client, "p3@x.test")

    resp = await client.get(f"/api/v1/parent/children/{foreign.id}/dashboard", headers=headers)
    assert resp.status_code == 404
