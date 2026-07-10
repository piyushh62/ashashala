"""Timetable.topic — create/patch the topic field for timetable entries."""

import pytest

from app.db.tenant_filter import tenant_bypass
from app.models.structure import TeacherAssignment
from app.models.user import UserRole
from tests.conftest import login, make_school, make_user


async def _assign(db, *, teacher_id, school_id, class_id="c1", subject_id="s1"):
    with tenant_bypass():
        db.add(TeacherAssignment(teacher_id=teacher_id, class_id=class_id,
                                 subject_id=subject_id, school_id=school_id))
        await db.commit()


@pytest.mark.asyncio
async def test_create_timetable_with_topic(client, db):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="tt1@x.test")
    await _assign(db, teacher_id=teacher.id, school_id=school.id)
    headers = await login(client, "tt1@x.test")

    resp = await client.post("/api/v1/teacher/timetable", headers=headers, json={
        "class_id": "c1", "subject_id": "s1", "day_of_week": 1, "period_number": 2,
        "room": "R2", "topic": "Fractions"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["topic"] == "Fractions"


@pytest.mark.asyncio
async def test_patch_timetable_topic(client, db):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="tt2@x.test")
    await _assign(db, teacher_id=teacher.id, school_id=school.id)
    headers = await login(client, "tt2@x.test")

    created = await client.post("/api/v1/teacher/timetable", headers=headers, json={
        "class_id": "c1", "subject_id": "s1", "day_of_week": 0, "period_number": 1})
    entry_id = created.json()["id"]
    assert created.json()["topic"] is None

    patched = await client.patch(f"/api/v1/teacher/timetable/{entry_id}", headers=headers,
                                 json={"topic": "Algebra basics"})
    assert patched.status_code == 200, patched.text
    assert patched.json()["topic"] == "Algebra basics"

    listing = await client.get("/api/v1/teacher/timetable", headers=headers)
    assert any(e["id"] == entry_id and e["topic"] == "Algebra basics" for e in listing.json())


@pytest.mark.asyncio
async def test_patch_other_teachers_timetable_404(client, db):
    school = await make_school(db)
    t1 = await make_user(db, role=UserRole.teacher, school_id=school.id, email="tt3@x.test")
    await make_user(db, role=UserRole.teacher, school_id=school.id, email="tt4@x.test")
    await _assign(db, teacher_id=t1.id, school_id=school.id)
    headers1 = await login(client, "tt3@x.test")
    headers2 = await login(client, "tt4@x.test")

    created = await client.post("/api/v1/teacher/timetable", headers=headers1, json={
        "class_id": "c1", "subject_id": "s1", "day_of_week": 0, "period_number": 1})
    entry_id = created.json()["id"]

    resp = await client.patch(f"/api/v1/teacher/timetable/{entry_id}", headers=headers2,
                              json={"topic": "Hijack attempt"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_unknown_timetable_entry_404(client, db):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="tt5@x.test")
    await _assign(db, teacher_id=teacher.id, school_id=school.id)
    headers = await login(client, "tt5@x.test")

    resp = await client.patch("/api/v1/teacher/timetable/nope", headers=headers, json={"topic": "x"})
    assert resp.status_code == 404
