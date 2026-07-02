"""Timetable CRUD — teacher creates regular + exam timetable for an assigned class."""

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
async def test_teacher_creates_timetable(client, db):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="t@x.test")
    await _assign(db, teacher_id=teacher.id, school_id=school.id)
    headers = await login(client, "t@x.test")

    resp = await client.post("/api/v1/teacher/timetable", headers=headers, json={
        "class_id": "c1", "subject_id": "s1", "day_of_week": 0, "period_number": 1, "room": "R1"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["period_number"] == 1


@pytest.mark.asyncio
async def test_teacher_creates_exam_timetable(client, db):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="t2@x.test")
    await _assign(db, teacher_id=teacher.id, school_id=school.id)
    headers = await login(client, "t2@x.test")

    resp = await client.post("/api/v1/teacher/exam-timetable", headers=headers, json={
        "class_id": "c1", "subject_id": "s1", "exam_name": "Midterm", "exam_date": "2026-09-01"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["exam_name"] == "Midterm"


@pytest.mark.asyncio
async def test_teacher_unassigned_class_forbidden(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.teacher, school_id=school.id, email="t3@x.test")
    headers = await login(client, "t3@x.test")
    resp = await client.post("/api/v1/teacher/timetable", headers=headers, json={
        "class_id": "cX", "subject_id": "sX", "day_of_week": 0, "period_number": 1})
    assert resp.status_code == 403
