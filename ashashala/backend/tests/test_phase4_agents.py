"""Phase 4 — full multi-agent loop.

ask (weakest topic) -> quiz generated -> submit -> graded (MCQ + short) ->
mastery updated via EMA -> low-confidence short answers flagged -> teacher
review queue populated -> teacher overrides + approves -> next quiz still
targets the weakest topic.
"""

import json

import pytest
from sqlalchemy import select

from app.agents import evaluator as evaluator_mod
from app.agents import quiz_master as quiz_master_mod
from app.agents.progress import ema
from app.db.tenant_filter import tenant_bypass
from app.models.flagged_answer import FlaggedAnswer, FlagStatus
from app.models.learning import ProgressRecord, Quiz, QuizAttempt, QuizStatus
from app.models.structure import Enrollment, Subject, TeacherAssignment
from app.models.user import UserRole
from tests.conftest import login, make_school, make_user

CLASS_ID = "class-6a"

# LLM-shaped quiz JSON the (mocked) Quiz Master returns.
_QUIZ_JSON = json.dumps({
    "topic": "Fractions",
    "questions": [
        {"type": "mcq", "question": "1/2 + 1/2 = ?", "options": ["1", "1/4", "2/4", "0"],
         "answer_index": 0, "difficulty": "easy", "xp": 10, "explanation": "Two halves make a whole."},
        {"type": "mcq", "question": "1/4 of 8 = ?", "options": ["2", "4", "1", "8"],
         "answer_index": 0, "difficulty": "easy", "xp": 10, "explanation": "8/4 = 2."},
        {"type": "mcq", "question": "Which is larger?", "options": ["1/2", "1/3", "1/4", "1/5"],
         "answer_index": 0, "difficulty": "medium", "xp": 20, "explanation": "1/2 is largest."},
        {"type": "short", "question": "Why isn't 1/2 + 1/3 = 2/5?", "expected_answer": "Unequal pieces; need common denominator.",
         "difficulty": "hard", "xp": 30, "explanation": "Common denominator."},
        {"type": "short", "question": "Define a fraction.", "expected_answer": "Part of a whole.",
         "difficulty": "medium", "xp": 20, "explanation": "Part of a whole."},
    ],
})

# Low score + low confidence => the short answers get flagged.
_GRADE_JSON = json.dumps({"score": 0.2, "confidence": 0.5,
                          "feedback": "Good start — revisit common denominators.", "missed_concepts": ["common denominator"]})


async def _seed(db):
    school = await make_school(db)
    student = await make_user(db, role=UserRole.student, school_id=school.id,
                              email="stu4@x.test", grade=6, interests="cricket")
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="tea4@x.test")
    with tenant_bypass():
        subject = Subject(school_id=school.id, name="Mathematics")
        db.add(subject)
        await db.flush()
        db.add(Enrollment(school_id=school.id, student_id=student.id, class_id=CLASS_ID))
        db.add(TeacherAssignment(school_id=school.id, teacher_id=teacher.id,
                                 class_id=CLASS_ID, subject_id=subject.id))
        # Two topics: Fractions is the weakest (20 < 80).
        db.add(ProgressRecord(school_id=school.id, student_id=student.id,
                              subject_id=subject.id, topic="Fractions", mastery_score=20))
        db.add(ProgressRecord(school_id=school.id, student_id=student.id,
                              subject_id=subject.id, topic="Algebra", mastery_score=80))
        await db.commit()
    return school, student, teacher, subject


def _patch_agents(monkeypatch):
    async def fake_retrieve(**kw):
        return []

    async def fake_quiz_llm(messages, task, **kw):
        return _QUIZ_JSON

    async def fake_eval_llm(messages, task, **kw):
        return _GRADE_JSON

    monkeypatch.setattr(quiz_master_mod, "retrieve", fake_retrieve)
    monkeypatch.setattr(quiz_master_mod, "llm_chat", fake_quiz_llm)
    monkeypatch.setattr(evaluator_mod, "retrieve", fake_retrieve)
    monkeypatch.setattr(evaluator_mod, "llm_chat", fake_eval_llm)


@pytest.mark.asyncio
async def test_full_quiz_loop(client, db, monkeypatch):
    school, student, teacher, subject = await _seed(db)
    _patch_agents(monkeypatch)
    s_headers = await login(client, "stu4@x.test")

    # 1) Quiz Master targets the weakest topic (Fractions) and hides answers.
    start = await client.post("/api/v1/student/quiz/start", headers=s_headers,
                              json={"class_id": CLASS_ID})
    assert start.status_code == 200, start.text
    quiz = start.json()
    assert quiz["topic"] == "Fractions"
    assert len(quiz["questions"]) == 5
    assert "answer_index" not in json.dumps(quiz["questions"])   # answers stripped
    quiz_id = quiz["id"]

    # 2) Submit: all 3 MCQ correct (index 0), 2 short answers (graded low -> flagged).
    submit = await client.post(f"/api/v1/student/quiz/{quiz_id}/submit", headers=s_headers,
                               json={"answers": [0, 0, 0, "some answer", "another"]})
    assert submit.status_code == 200, submit.text
    res = submit.json()
    # score = (1+1+1+0.2+0.2)/5 = 0.68
    assert abs(res["attempt_score"] - 0.68) < 1e-6
    assert res["mastery_update"]["old"] == 20
    # EMA: round(0.7*20 + 0.3*0.68*100) = round(34.4) = 34
    assert res["mastery_update"]["new"] == ema(20, res["attempt_score"]) == 34

    # 3) Mastery persisted with the EMA value.
    db.expire_all()
    rec = (await db.execute(select(ProgressRecord).where(
        ProgressRecord.student_id == student.id, ProgressRecord.topic == "Fractions"
    ))).scalars().first()
    assert rec.mastery_score == ema(20, 0.68)

    # 4) QuizAttempt persisted; teacher review queue populated (2 short answers flagged).
    attempts = (await db.execute(select(QuizAttempt).where(QuizAttempt.quiz_id == quiz_id))).scalars().all()
    assert len(attempts) == 1
    flagged = (await db.execute(select(FlaggedAnswer))).scalars().all()
    assert len(flagged) == 2

    # 5) Teacher sees the queue, overrides one, approves the quiz.
    t_headers = await login(client, "tea4@x.test")
    q = await client.get("/api/v1/teacher/flagged-answers", headers=t_headers)
    assert q.status_code == 200
    queue = q.json()
    assert len(queue) == 2

    ov = await client.post(f"/api/v1/teacher/flagged-answers/{queue[0]['id']}/override",
                           headers=t_headers, json={"score": 0.9, "feedback": "Actually correct."})
    assert ov.status_code == 200 and ov.json()["status"] == "resolved"

    ap = await client.post(f"/api/v1/teacher/quizzes/{quiz_id}/approve",
                           headers=t_headers, json={"approved": True})
    assert ap.status_code == 200 and ap.json()["status"] == QuizStatus.approved.value

    # 6) Next practice quiz still targets the weakest topic (Fractions at 34 < Algebra 80).
    topic, _sid, mastery = await quiz_master_mod.pick_weakest_topic(db, student)
    assert topic == "Fractions"
    assert mastery == ema(20, 0.68)


@pytest.mark.asyncio
async def test_flagged_answer_resolved_after_override(client, db, monkeypatch):
    school, student, teacher, subject = await _seed(db)
    _patch_agents(monkeypatch)
    s_headers = await login(client, "stu4@x.test")

    quiz_id = (await client.post("/api/v1/student/quiz/start", headers=s_headers,
                                 json={"class_id": CLASS_ID})).json()["id"]
    await client.post(f"/api/v1/student/quiz/{quiz_id}/submit", headers=s_headers,
                      json={"answers": [0, 0, 0, "x", "y"]})

    t_headers = await login(client, "tea4@x.test")
    queue = (await client.get("/api/v1/teacher/flagged-answers", headers=t_headers)).json()
    await client.post(f"/api/v1/teacher/flagged-answers/{queue[0]['id']}/override",
                      headers=t_headers, json={"score": 1.0})

    db.expire_all()
    resolved = (await db.execute(select(FlaggedAnswer).where(
        FlaggedAnswer.status == FlagStatus.resolved))).scalars().all()
    assert len(resolved) == 1
    assert resolved[0].override_score == 1.0
    # The open queue shrank by one.
    remaining = (await client.get("/api/v1/teacher/flagged-answers", headers=t_headers)).json()
    assert len(remaining) == 1
