"""Parent<->teacher message thread: both sides can post/read, only for a
student the teacher is assigned to / the parent is linked to, and unread
messages from the other party are marked read on view."""

import pytest

from app.db.tenant_filter import tenant_bypass
from app.models.structure import Enrollment, ParentStudentLink, TeacherAssignment
from app.models.user import UserRole
from tests.conftest import login, make_school, make_user


async def _seed(db, *, assign_teacher=True, link_parent=True):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id,
                              email=f"msg_t_{assign_teacher}_{link_parent}@x.test")
    parent = await make_user(db, role=UserRole.parent, school_id=school.id,
                             email=f"msg_p_{assign_teacher}_{link_parent}@x.test")
    student = await make_user(db, role=UserRole.student, school_id=school.id,
                              email=f"msg_s_{assign_teacher}_{link_parent}@x.test", grade=6)
    with tenant_bypass():
        db.add(Enrollment(school_id=school.id, student_id=student.id, class_id="c1"))
        if assign_teacher:
            db.add(TeacherAssignment(teacher_id=teacher.id, class_id="c1", subject_id="s1", school_id=school.id))
        if link_parent:
            db.add(ParentStudentLink(parent_id=parent.id, student_id=student.id, school_id=school.id))
        await db.commit()
    return school, teacher, parent, student


@pytest.mark.asyncio
async def test_teacher_and_parent_round_trip(client, db):
    school, teacher, parent, student = await _seed(db)
    teacher_headers = await login(client, teacher.email)
    parent_headers = await login(client, parent.email)

    resp = await client.post("/api/v1/teacher/messages", headers=teacher_headers,
                             json={"student_id": student.id, "body": "How is homework going?"})
    assert resp.status_code == 200, resp.text
    assert resp.json()[0]["sender_role"] == "teacher"

    resp2 = await client.post("/api/v1/parent/messages", headers=parent_headers,
                              json={"student_id": student.id, "teacher_id": teacher.id, "body": "Going well!"})
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["sender_role"] == "parent"

    thread = await client.get(f"/api/v1/teacher/messages?student_id={student.id}", headers=teacher_headers)
    assert thread.status_code == 200, thread.text
    bodies = [m["body"] for m in thread.json()]
    assert bodies == ["How is homework going?", "Going well!"]
    assert all(m["read_at"] is not None for m in thread.json() if m["sender_role"] == "parent")

    parent_thread = await client.get(
        f"/api/v1/parent/messages?student_id={student.id}", headers=parent_headers
    )
    assert parent_thread.status_code == 200, parent_thread.text
    assert len(parent_thread.json()) == 2


@pytest.mark.asyncio
async def test_teacher_message_rejected_when_not_assigned(client, db):
    school, teacher, parent, student = await _seed(db, assign_teacher=False)
    headers = await login(client, teacher.email)

    resp = await client.post("/api/v1/teacher/messages", headers=headers,
                             json={"student_id": student.id, "body": "hello"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_parent_message_rejected_when_teacher_not_assigned(client, db):
    school, teacher, parent, student = await _seed(db, assign_teacher=False)
    headers = await login(client, parent.email)

    resp = await client.post("/api/v1/parent/messages", headers=headers,
                             json={"student_id": student.id, "teacher_id": teacher.id, "body": "hi"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_parent_message_rejected_for_unlinked_child(client, db):
    school, teacher, parent, student = await _seed(db, link_parent=False)
    headers = await login(client, parent.email)

    resp = await client.post("/api/v1/parent/messages", headers=headers,
                             json={"student_id": student.id, "teacher_id": teacher.id, "body": "hi"})
    assert resp.status_code == 403
