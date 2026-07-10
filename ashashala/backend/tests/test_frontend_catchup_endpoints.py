"""Two small read-only endpoints added to support frontend catch-up pages:
GET /teacher/exam-timetable (list, scoped to the teacher's assigned classes) and
GET /parent/children/{id}/teachers (for the parent message-compose picker)."""

import pytest

from app.db.tenant_filter import tenant_bypass
from app.models.structure import Enrollment, ParentStudentLink, Subject, TeacherAssignment
from app.models.user import UserRole
from tests.conftest import login, make_school, make_user


async def _assign(db, *, teacher_id, school_id, class_id="c1", subject_id="s1"):
    with tenant_bypass():
        db.add(Subject(id=subject_id, school_id=school_id, name="Maths"))
        db.add(TeacherAssignment(teacher_id=teacher_id, class_id=class_id,
                                 subject_id=subject_id, school_id=school_id))
        await db.commit()


@pytest.mark.asyncio
async def test_teacher_list_exam_timetable_scoped_to_assigned_classes(client, db):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="et1@x.test")
    await _assign(db, teacher_id=teacher.id, school_id=school.id, class_id="c1", subject_id="s1")
    headers = await login(client, "et1@x.test")

    create = await client.post("/api/v1/teacher/exam-timetable", headers=headers, json={
        "class_id": "c1", "subject_id": "s1", "exam_name": "Midterm", "exam_date": "2026-09-01"})
    assert create.status_code == 200, create.text

    resp = await client.get("/api/v1/teacher/exam-timetable", headers=headers)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["exam_name"] == "Midterm"

    filtered = await client.get("/api/v1/teacher/exam-timetable?class_id=c1", headers=headers)
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    forbidden = await client.get("/api/v1/teacher/exam-timetable?class_id=other-class", headers=headers)
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_teacher_list_exam_timetable_empty_when_unassigned(client, db):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="et2@x.test")
    headers = await login(client, "et2@x.test")

    resp = await client.get("/api/v1/teacher/exam-timetable", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_parent_child_teachers_lists_assigned_teachers(client, db):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="ct1@x.test", name="Ms. Rao")
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="cs1@x.test", grade=6)
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="cp1@x.test")
    await _assign(db, teacher_id=teacher.id, school_id=school.id, class_id="c1", subject_id="s1")
    with tenant_bypass():
        db.add(Enrollment(school_id=school.id, student_id=student.id, class_id="c1"))
        db.add(ParentStudentLink(parent_id=parent.id, student_id=student.id, school_id=school.id))
        await db.commit()
    headers = await login(client, "cp1@x.test")

    resp = await client.get(f"/api/v1/parent/children/{student.id}/teachers", headers=headers)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["teacher_id"] == teacher.id
    assert rows[0]["teacher_name"] == "Ms. Rao"
    assert rows[0]["subject_name"] == "Maths"


@pytest.mark.asyncio
async def test_parent_child_teachers_404_for_unlinked_child(client, db):
    school = await make_school(db)
    other_school = await make_school(db, name="Other School")
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="cp2@x.test")
    stranger = await make_user(db, role=UserRole.student, school_id=other_school.id, email="cs2@x.test", grade=6)
    headers = await login(client, "cp2@x.test")

    resp = await client.get(f"/api/v1/parent/children/{stranger.id}/teachers", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_parent_child_teachers_empty_when_no_class_assignment(client, db):
    school = await make_school(db)
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="cs3@x.test", grade=6)
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="cp3@x.test")
    with tenant_bypass():
        db.add(ParentStudentLink(parent_id=parent.id, student_id=student.id, school_id=school.id))
        await db.commit()
    headers = await login(client, "cp3@x.test")

    resp = await client.get(f"/api/v1/parent/children/{student.id}/teachers", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []
