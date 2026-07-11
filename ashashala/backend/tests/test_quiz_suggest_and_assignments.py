"""Teacher-triggered quiz suggestion (#2 material-grounded, Assignment Builder
auto-generate) and the Assignment Builder itself (#3) — POST
/teacher/materials/{doc_id}/suggest-quiz and POST /teacher/assignment-tasks."""

import json

import pytest
from sqlalchemy import select

from app.agents import quiz_suggest as quiz_suggest_mod
from app.db.tenant_filter import tenant_bypass
from app.models.assignment import Assignment, AssignmentStatus
from app.models.document import DocStatus, Document, SourceType
from app.models.learning import Quiz, QuizAttempt, QuizStatus
from app.models.notification import Notification
from app.models.structure import Enrollment, Subject, TeacherAssignment
from app.models.user import UserRole
from tests.conftest import login, make_school, make_user

CLASS_ID = "class-7b"

_QUIZ_JSON = json.dumps({
    "topic": "Photosynthesis",
    "questions": [
        {"type": "mcq", "question": "What gas do plants absorb?", "options": ["O2", "CO2", "N2", "H2"],
         "answer_index": 1, "difficulty": "easy", "xp": 10, "explanation": "CO2 is absorbed."},
        {"type": "mcq", "question": "Where does photosynthesis occur?", "options": ["Root", "Chloroplast", "Stem", "Flower"],
         "answer_index": 1, "difficulty": "easy", "xp": 10, "explanation": "In chloroplasts."},
        {"type": "mcq", "question": "What is released?", "options": ["O2", "CO2", "N2", "H2"],
         "answer_index": 0, "difficulty": "medium", "xp": 20, "explanation": "Oxygen is released."},
        {"type": "short", "question": "Why do plants need sunlight?", "expected_answer": "Energy source for the reaction.",
         "difficulty": "hard", "xp": 30, "explanation": "Sunlight provides energy."},
        {"type": "short", "question": "Define chlorophyll.", "expected_answer": "Green pigment that absorbs light.",
         "difficulty": "medium", "xp": 20, "explanation": "Green pigment."},
    ],
})


async def _seed(db):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="qs_tea@x.test")
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="qs_stu@x.test", grade=7)
    with tenant_bypass():
        subject = Subject(school_id=school.id, name="Science")
        db.add(subject)
        await db.flush()
        db.add(TeacherAssignment(school_id=school.id, teacher_id=teacher.id,
                                 class_id=CLASS_ID, subject_id=subject.id))
        db.add(Enrollment(school_id=school.id, student_id=student.id, class_id=CLASS_ID))
        await db.commit()
    return school, teacher, student, subject


def _patch_llm(monkeypatch):
    async def fake_retrieve(**kw):
        return []

    async def fake_llm(messages, task, **kw):
        return _QUIZ_JSON

    monkeypatch.setattr(quiz_suggest_mod, "retrieve", fake_retrieve)
    monkeypatch.setattr(quiz_suggest_mod, "llm_chat", fake_llm)


@pytest.mark.asyncio
async def test_suggest_quiz_from_material_returns_draft_with_answers(client, db, monkeypatch):
    school, teacher, student, subject = await _seed(db)
    _patch_llm(monkeypatch)
    with tenant_bypass():
        doc = Document(school_id=school.id, class_id=CLASS_ID, subject_id=subject.id,
                       uploaded_by_teacher_id=teacher.id, filename="cell_biology.pdf",
                       source_type=SourceType.pdf, status=DocStatus.indexed)
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

    headers = await login(client, "qs_tea@x.test")
    resp = await client.post(f"/api/v1/teacher/materials/{doc.id}/suggest-quiz", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["topic"] == "Cell Biology"
    assert body["class_id"] == CLASS_ID
    assert len(body["questions"]) == 5
    assert body["questions"][0]["answer_index"] == 1   # answers included for review

    db.expire_all()
    quiz = await db.get(Quiz, body["quiz_id"])
    assert quiz.status == QuizStatus.draft

    # Teacher reviews, then approves via the existing generic endpoint.
    ap = await client.post(f"/api/v1/teacher/quizzes/{body['quiz_id']}/approve",
                           headers=headers, json={"approved": True})
    assert ap.status_code == 200 and ap.json()["status"] == QuizStatus.approved.value


@pytest.mark.asyncio
async def test_suggest_quiz_rejects_unindexed_document(client, db, monkeypatch):
    school, teacher, student, subject = await _seed(db)
    _patch_llm(monkeypatch)
    with tenant_bypass():
        doc = Document(school_id=school.id, class_id=CLASS_ID, subject_id=subject.id,
                       uploaded_by_teacher_id=teacher.id, filename="still_processing.pdf",
                       source_type=SourceType.pdf, status=DocStatus.pending)
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

    headers = await login(client, "qs_tea@x.test")
    resp = await client.post(f"/api/v1/teacher/materials/{doc.id}/suggest-quiz", headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_suggest_quiz_404_for_other_school_document(client, db, monkeypatch):
    school, teacher, student, subject = await _seed(db)
    other_school = await make_school(db, name="Other School")
    _patch_llm(monkeypatch)
    with tenant_bypass():
        other_teacher = await make_user(db, role=UserRole.teacher, school_id=other_school.id, email="other_tea@x.test")
        doc = Document(school_id=other_school.id, class_id="c-other", uploaded_by_teacher_id=other_teacher.id,
                       filename="foreign.pdf", source_type=SourceType.pdf, status=DocStatus.indexed)
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

    headers = await login(client, "qs_tea@x.test")
    resp = await client.post(f"/api/v1/teacher/materials/{doc.id}/suggest-quiz", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_assignment_task_auto_generates_and_publishes_quiz(client, db, monkeypatch):
    school, teacher, student, subject = await _seed(db)
    _patch_llm(monkeypatch)
    student_id = student.id
    headers = await login(client, "qs_tea@x.test")

    resp = await client.post("/api/v1/teacher/assignment-tasks", headers=headers, json={
        "class_id": CLASS_ID, "subject_id": subject.id, "topic": "Photosynthesis",
        "due_date": "2026-07-20",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["topic"] == "Photosynthesis"
    assert body["class_name"] == CLASS_ID  # no ClassSection row seeded; falls back to id
    assert body["status"] == AssignmentStatus.published.value
    assert body["submission_count"] == 0
    assert body["quiz_id"] is not None

    db.expire_all()
    quiz = await db.get(Quiz, body["quiz_id"])
    assert quiz.status == QuizStatus.approved   # auto-approved, unlike the material-suggest flow

    notifications = (await db.execute(
        select(Notification).where(Notification.user_id == student_id, Notification.type == "assignment_created")
    )).scalars().all()
    assert len(notifications) == 1

    listing = await client.get("/api/v1/teacher/assignment-tasks", headers=headers)
    assert listing.status_code == 200
    items = listing.json()
    assert len(items) == 1
    assert items[0]["id"] == body["id"]


@pytest.mark.asyncio
async def test_assignment_submission_count_reflects_quiz_attempts(client, db, monkeypatch):
    school, teacher, student, subject = await _seed(db)
    _patch_llm(monkeypatch)
    headers = await login(client, "qs_tea@x.test")

    created = (await client.post("/api/v1/teacher/assignment-tasks", headers=headers, json={
        "class_id": CLASS_ID, "subject_id": subject.id, "topic": "Photosynthesis",
        "due_date": "2026-07-20",
    })).json()

    with tenant_bypass():
        db.add(QuizAttempt(school_id=school.id, quiz_id=created["quiz_id"], student_id=student.id,
                           answers_json=[1, 1, 0, "a", "b"], score=0.8, feedback_json={}))
        await db.commit()

    listing = (await client.get("/api/v1/teacher/assignment-tasks", headers=headers)).json()
    assert listing[0]["submission_count"] == 1


@pytest.mark.asyncio
async def test_assignment_task_blocked_for_unassigned_class(client, db, monkeypatch):
    school, teacher, student, subject = await _seed(db)
    _patch_llm(monkeypatch)
    headers = await login(client, "qs_tea@x.test")

    resp = await client.post("/api/v1/teacher/assignment-tasks", headers=headers, json={
        "class_id": "some-other-class", "subject_id": subject.id, "topic": "Anything",
        "due_date": "2026-07-20",
    })
    assert resp.status_code == 403
