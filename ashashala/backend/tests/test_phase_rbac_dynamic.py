"""Dynamic RBAC (Phase 1) — permission resolution matches the legacy guard
matrix, school role/creation-rights management, and the generalized Agent
Action approval queue."""

import pytest

from app.core.permissions import (
    PARENT_PORTAL,
    PLATFORM_ADMIN,
    ROLE_MANAGE,
    SCHOOL_ADMIN,
    STUDENT_PORTAL,
    TEACHER_PORTAL,
)
from app.db.tenant_filter import tenant_bypass
from app.models.user import UserRole
from app.services.rbac_service import propose_agent_action
from tests.conftest import login, make_school, make_user


@pytest.mark.asyncio
async def test_permissions_match_legacy_guards_for_each_system_role(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.super_admin, school_id=None, email="super@x.test")
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="sadmin@x.test")
    await make_user(db, role=UserRole.teacher, school_id=school.id, email="teach@x.test")
    await make_user(db, role=UserRole.student, school_id=school.id, email="stud@x.test")
    await make_user(db, role=UserRole.parent, school_id=school.id, email="par@x.test")

    expectations = {
        "super@x.test": PLATFORM_ADMIN,
        "sadmin@x.test": SCHOOL_ADMIN,
        "teach@x.test": TEACHER_PORTAL,
        "stud@x.test": STUDENT_PORTAL,
        "par@x.test": PARENT_PORTAL,
    }
    for email, expected_permission in expectations.items():
        headers = await login(client, email)
        resp = await client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 200, resp.text
        assert expected_permission in resp.json()["permissions"], (email, resp.json())


@pytest.mark.asyncio
async def test_school_admin_permissions_include_role_manage(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="adm@x.test")
    headers = await login(client, "adm@x.test")
    resp = await client.get("/api/v1/auth/me", headers=headers)
    assert ROLE_MANAGE in resp.json()["permissions"]


@pytest.mark.asyncio
async def test_school_creation_auto_provisions_roles_and_default_creation_rights(client, db):
    await make_user(db, role=UserRole.super_admin, school_id=None, email="super2@x.test")
    admin_headers = await login(client, "super2@x.test")

    resp = await client.post("/api/v1/admin/schools", headers=admin_headers, json={"name": "New School"})
    assert resp.status_code == 200, resp.text
    school_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/admin/schools/{school_id}/admins", headers=admin_headers,
                             json={"name": "Admin", "email": "newadm@x.test"})
    assert resp.status_code == 200, resp.text
    temp_password = resp.json()["temp_password"]

    sa_headers = await login(client, "newadm@x.test", temp_password)
    roles_resp = await client.get("/api/v1/school/roles", headers=sa_headers)
    assert roles_resp.status_code == 200, roles_resp.text
    roles = roles_resp.json()
    assert {r["name"] for r in roles} == {"School Admin", "Teacher", "Student", "Parent"}
    assert all(not r["is_custom"] for r in roles)

    school_admin_role = next(r for r in roles if r["name"] == "School Admin")
    teacher_role = next(r for r in roles if r["name"] == "Teacher")

    cr_resp = await client.get(f"/api/v1/school/roles/{school_admin_role['id']}/creation-rights", headers=sa_headers)
    assert cr_resp.status_code == 200, cr_resp.text
    assert set(cr_resp.json()["creatable_template_names"]) == {"Teacher", "Student", "Parent"}

    cr_resp = await client.get(f"/api/v1/school/roles/{teacher_role['id']}/creation-rights", headers=sa_headers)
    assert cr_resp.json()["creatable_template_names"] == []


@pytest.mark.asyncio
async def test_teacher_blocked_by_default_then_allowed_after_creation_rights_toggle(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="adm3@x.test")
    await make_user(db, role=UserRole.teacher, school_id=school.id, email="teach3@x.test")
    admin_headers = await login(client, "adm3@x.test")
    teacher_headers = await login(client, "teach3@x.test")

    resp = await client.post("/api/v1/teacher/students", headers=teacher_headers,
                             json={"name": "S1", "email": "s1@x.test"})
    assert resp.status_code == 403, resp.text

    roles_resp = await client.get("/api/v1/school/roles", headers=admin_headers)
    teacher_role = next(r for r in roles_resp.json() if r["name"] == "Teacher")

    toggle_resp = await client.patch(
        f"/api/v1/school/roles/{teacher_role['id']}/creation-rights", headers=admin_headers,
        json={"creatable_template_names": ["Student"]},
    )
    assert toggle_resp.status_code == 200, toggle_resp.text
    assert toggle_resp.json()["creatable_template_names"] == ["Student"]

    resp = await client.post("/api/v1/teacher/students", headers=teacher_headers,
                             json={"name": "S1", "email": "s1@x.test"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["user"]["role"] == "student"

    # Parent creation still blocked -- only Student was granted.
    resp = await client.post("/api/v1/teacher/parents", headers=teacher_headers,
                             json={"name": "P1", "email": "p1@x.test", "student_id": resp.json()["user"]["id"]})
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_custom_role_crud(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="adm4@x.test")
    headers = await login(client, "adm4@x.test")

    create_resp = await client.post("/api/v1/school/roles", headers=headers,
                                    json={"name": "Librarian", "permissions": [TEACHER_PORTAL]})
    assert create_resp.status_code == 200, create_resp.text
    role = create_resp.json()
    assert role["is_custom"] is True
    assert role["permissions"] == [TEACHER_PORTAL]

    update_resp = await client.patch(f"/api/v1/school/roles/{role['id']}", headers=headers,
                                     json={"permissions": [STUDENT_PORTAL]})
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["permissions"] == [STUDENT_PORTAL]

    delete_resp = await client.delete(f"/api/v1/school/roles/{role['id']}", headers=headers)
    assert delete_resp.status_code == 200, delete_resp.text

    roles_resp = await client.get("/api/v1/school/roles", headers=headers)
    school_admin_role = next(r for r in roles_resp.json() if r["name"] == "School Admin")
    forbidden_delete = await client.delete(f"/api/v1/school/roles/{school_admin_role['id']}", headers=headers)
    assert forbidden_delete.status_code == 422


@pytest.mark.asyncio
async def test_admin_role_template_crud(client, db):
    await make_user(db, role=UserRole.super_admin, school_id=None, email="super5@x.test")
    headers = await login(client, "super5@x.test")

    perms_resp = await client.get("/api/v1/admin/permissions", headers=headers)
    assert perms_resp.status_code == 200, perms_resp.text
    assert len(perms_resp.json()) > 0

    create_resp = await client.post("/api/v1/admin/role-templates", headers=headers,
                                    json={"name": "Librarian", "description": "desc", "permissions": [TEACHER_PORTAL]})
    assert create_resp.status_code == 200, create_resp.text
    template = create_resp.json()
    assert template["is_system"] is False

    update_resp = await client.patch(f"/api/v1/admin/role-templates/{template['id']}", headers=headers,
                                     json={"permissions": [STUDENT_PORTAL]})
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["permissions"] == [STUDENT_PORTAL]

    delete_resp = await client.delete(f"/api/v1/admin/role-templates/{template['id']}", headers=headers)
    assert delete_resp.status_code == 200, delete_resp.text

    templates_resp = await client.get("/api/v1/admin/role-templates", headers=headers)
    system_template = next(t for t in templates_resp.json() if t["name"] == "Teacher")
    forbidden = await client.delete(f"/api/v1/admin/role-templates/{system_template['id']}", headers=headers)
    assert forbidden.status_code == 422


@pytest.mark.asyncio
async def test_agent_action_propose_approve_reject_flow(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.teacher, school_id=school.id, email="teach6@x.test")
    headers = await login(client, "teach6@x.test")

    with tenant_bypass():
        action = await propose_agent_action(db, school_id=school.id, agent_name="scheduler",
                                            action_type="reschedule_class",
                                            payload={"class_id": "c1"}, confidence=0.9)
        await db.commit()
    action_id = action.id

    list_resp = await client.get("/api/v1/agent-actions", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    assert any(a["id"] == action_id for a in list_resp.json()["items"])

    approve_resp = await client.post(f"/api/v1/agent-actions/{action_id}/approve", headers=headers,
                                     json={"note": "looks good"})
    assert approve_resp.status_code == 200, approve_resp.text
    assert approve_resp.json()["status"] == "approved"

    # Already-resolved actions can't be reviewed again.
    reject_resp = await client.post(f"/api/v1/agent-actions/{action_id}/reject", headers=headers)
    assert reject_resp.status_code == 422, reject_resp.text


@pytest.mark.asyncio
async def test_agent_action_scoped_to_own_school(client, db):
    school_a = await make_school(db, name="A")
    school_b = await make_school(db, name="B")
    await make_user(db, role=UserRole.teacher, school_id=school_b.id, email="teach7@x.test")
    headers = await login(client, "teach7@x.test")

    with tenant_bypass():
        action = await propose_agent_action(db, school_id=school_a.id, agent_name="scheduler",
                                            action_type="reschedule_class", payload={})
        await db.commit()

    list_resp = await client.get("/api/v1/agent-actions", headers=headers)
    assert all(a["id"] != action.id for a in list_resp.json()["items"])

    approve_resp = await client.post(f"/api/v1/agent-actions/{action.id}/approve", headers=headers)
    assert approve_resp.status_code == 404
