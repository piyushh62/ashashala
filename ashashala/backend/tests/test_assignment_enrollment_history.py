"""Enrollment/TeacherAssignment.end_date — mid-year transfer history.

`end_date IS NULL` = active. PATCH sets it, list endpoints default to
active-only (with `include_ended=true` to see history), and an ended
TeacherAssignment/Enrollment must stop granting access via the JWT claims on
the affected user's next login.
"""

import pytest
from jose import jwt

from app.core.config import settings
from app.models.user import UserRole
from tests.conftest import login, make_school, make_user


def _decode(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


@pytest.mark.asyncio
async def test_patch_teacher_assignment_sets_end_date_and_filters_list(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="adm_h1@x.test")
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="t_h1@x.test")
    headers = await login(client, "adm_h1@x.test")

    cls = (await client.post("/api/v1/school/classes", headers=headers,
                             json={"name": "8-A", "grade_level": 8})).json()
    subj = (await client.post("/api/v1/school/subjects", headers=headers,
                              json={"name": "Math"})).json()
    assign = await client.post("/api/v1/school/teacher-assignments", headers=headers, json={
        "teacher_id": teacher.id, "class_id": cls["id"], "subject_id": subj["id"]})
    assert assign.status_code == 200, assign.text
    assignment_id = assign.json()["id"]

    patched = await client.patch(f"/api/v1/school/teacher-assignments/{assignment_id}", headers=headers,
                                 json={"end_date": "2026-01-01"})
    assert patched.status_code == 200, patched.text
    assert patched.json()["id"] == assignment_id

    default_list = await client.get("/api/v1/school/teacher-assignments", headers=headers)
    assert default_list.status_code == 200
    assert all(a["id"] != assignment_id for a in default_list.json()["items"])

    full_list = await client.get("/api/v1/school/teacher-assignments?include_ended=true", headers=headers)
    ended = [a for a in full_list.json()["items"] if a["id"] == assignment_id]
    assert len(ended) == 1
    assert ended[0]["end_date"] == "2026-01-01"


@pytest.mark.asyncio
async def test_patch_enrollment_sets_end_date_and_filters_list(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="adm_h2@x.test")
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="s_h2@x.test")
    headers = await login(client, "adm_h2@x.test")

    cls = (await client.post("/api/v1/school/classes", headers=headers,
                             json={"name": "9-A", "grade_level": 9})).json()
    enroll = await client.post("/api/v1/school/enrollments", headers=headers, json={
        "student_id": student.id, "class_id": cls["id"]})
    assert enroll.status_code == 200, enroll.text
    enrollment_id = enroll.json()["id"]

    patched = await client.patch(f"/api/v1/school/enrollments/{enrollment_id}", headers=headers,
                                 json={"end_date": "2026-02-15"})
    assert patched.status_code == 200, patched.text

    default_list = await client.get("/api/v1/school/enrollments", headers=headers)
    assert all(e["id"] != enrollment_id for e in default_list.json()["items"])

    full_list = await client.get("/api/v1/school/enrollments?include_ended=true", headers=headers)
    ended = [e for e in full_list.json()["items"] if e["id"] == enrollment_id]
    assert len(ended) == 1
    assert ended[0]["end_date"] == "2026-02-15"


@pytest.mark.asyncio
async def test_ended_teacher_assignment_drops_from_jwt_claims(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="adm_h3@x.test")
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="t_h3@x.test")
    admin_headers = await login(client, "adm_h3@x.test")

    cls = (await client.post("/api/v1/school/classes", headers=admin_headers,
                             json={"name": "7-A", "grade_level": 7})).json()
    subj = (await client.post("/api/v1/school/subjects", headers=admin_headers,
                              json={"name": "Science"})).json()
    assign = await client.post("/api/v1/school/teacher-assignments", headers=admin_headers, json={
        "teacher_id": teacher.id, "class_id": cls["id"], "subject_id": subj["id"]})
    assignment_id = assign.json()["id"]

    teacher_headers = await login(client, "t_h3@x.test")
    claims = _decode(teacher_headers["Authorization"].split(" ")[1])
    assert cls["id"] in claims["class_ids"]

    ended = await client.patch(f"/api/v1/school/teacher-assignments/{assignment_id}", headers=admin_headers,
                               json={"end_date": "2026-07-10"})
    assert ended.status_code == 200, ended.text

    teacher_headers2 = await login(client, "t_h3@x.test")
    claims2 = _decode(teacher_headers2["Authorization"].split(" ")[1])
    assert cls["id"] not in claims2["class_ids"]


@pytest.mark.asyncio
async def test_ended_enrollment_drops_from_jwt_claims(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="adm_h4@x.test")
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="s_h4@x.test")
    admin_headers = await login(client, "adm_h4@x.test")

    cls = (await client.post("/api/v1/school/classes", headers=admin_headers,
                             json={"name": "10-A", "grade_level": 10})).json()
    enroll = await client.post("/api/v1/school/enrollments", headers=admin_headers, json={
        "student_id": student.id, "class_id": cls["id"]})
    enrollment_id = enroll.json()["id"]

    student_headers = await login(client, "s_h4@x.test")
    claims = _decode(student_headers["Authorization"].split(" ")[1])
    assert cls["id"] in claims["class_ids"]

    ended = await client.patch(f"/api/v1/school/enrollments/{enrollment_id}", headers=admin_headers,
                               json={"end_date": "2026-07-10"})
    assert ended.status_code == 200, ended.text

    student_headers2 = await login(client, "s_h4@x.test")
    claims2 = _decode(student_headers2["Authorization"].split(" ")[1])
    assert cls["id"] not in claims2["class_ids"]


@pytest.mark.asyncio
async def test_patch_unknown_teacher_assignment_404(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="adm_h5@x.test")
    headers = await login(client, "adm_h5@x.test")

    resp = await client.patch("/api/v1/school/teacher-assignments/nope", headers=headers,
                              json={"end_date": "2026-01-01"})
    assert resp.status_code == 404
