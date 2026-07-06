"""Name-based picker endpoints — school admin class/subject lists, teacher
assignments-with-names — that the frontend uses to build real <select> pickers
instead of asking users to type raw UUIDs."""

import pytest

from app.db.tenant_filter import tenant_bypass
from app.models.structure import ClassSection, Subject, TeacherAssignment
from app.models.user import UserRole
from tests.conftest import login, make_school, make_user


@pytest.mark.asyncio
async def test_school_admin_lists_classes_and_subjects(client, db):
    school = await make_school(db)
    await make_user(db, role=UserRole.school_admin, school_id=school.id, email="adm5@x.test")
    headers = await login(client, "adm5@x.test")

    created = await client.post("/api/v1/school/classes", headers=headers,
                                json={"name": "6-A", "grade_level": 6})
    assert created.status_code == 200
    await client.post("/api/v1/school/subjects", headers=headers, json={"name": "Mathematics"})

    classes = await client.get("/api/v1/school/classes", headers=headers)
    assert classes.status_code == 200
    assert any(c["name"] == "6-A" for c in classes.json())

    subjects = await client.get("/api/v1/school/subjects", headers=headers)
    assert subjects.status_code == 200
    assert any(s["name"] == "Mathematics" for s in subjects.json())


@pytest.mark.asyncio
async def test_school_admin_class_list_is_tenant_scoped(client, db):
    school_a = await make_school(db, name="A")
    school_b = await make_school(db, name="B")
    with tenant_bypass():
        db.add(ClassSection(school_id=school_a.id, name="A-Class", grade_level=1))
        db.add(ClassSection(school_id=school_b.id, name="B-Class", grade_level=1))
        await db.commit()

    await make_user(db, role=UserRole.school_admin, school_id=school_a.id, email="admA5@x.test")
    headers = await login(client, "admA5@x.test")
    classes = await client.get("/api/v1/school/classes", headers=headers)
    names = {c["name"] for c in classes.json()}
    assert "A-Class" in names
    assert "B-Class" not in names


@pytest.mark.asyncio
async def test_teacher_assignments_include_class_and_subject_names(client, db):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="tea5@x.test")
    with tenant_bypass():
        cls = ClassSection(school_id=school.id, name="Grade 7B", grade_level=7)
        subj = Subject(school_id=school.id, name="Physics")
        db.add(cls)
        db.add(subj)
        await db.flush()
        db.add(TeacherAssignment(teacher_id=teacher.id, class_id=cls.id,
                                 subject_id=subj.id, school_id=school.id))
        await db.commit()

    headers = await login(client, "tea5@x.test")
    resp = await client.get("/api/v1/teacher/assignments", headers=headers)
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["class_name"] == "Grade 7B"
    assert rows[0]["subject_name"] == "Physics"
