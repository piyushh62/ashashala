"""Insight Agent — nightly scan for struggling students: mastery threshold +
cooldown dedup are deterministic, the alert sentence is LLM-composed."""

import json

import pytest
from sqlalchemy import select

from app.agents import insight as insight_mod
from app.agents.insight import run_insight_scan
from app.db.tenant_filter import tenant_bypass
from app.models.agent_action import AgentAction, AgentActionStatus
from app.models.learning import ProgressRecord
from app.models.notification import Notification
from app.models.structure import Enrollment, TeacherAssignment
from app.models.user import UserRole
from tests.conftest import make_school, make_user


def _fake_llm(alert_text: str):
    async def _inner(messages, task, **kw):
        return json.dumps({"alert": alert_text})
    return _inner


async def _seed(db, *, mastery_score=20, with_teacher=True):
    school = await make_school(db)
    student = await make_user(db, role=UserRole.student, school_id=school.id,
                              email=f"ins_stu_{mastery_score}_{with_teacher}@x.test", grade=6)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id,
                              email=f"ins_tea_{mastery_score}_{with_teacher}@x.test")
    with tenant_bypass():
        db.add(Enrollment(school_id=school.id, student_id=student.id, class_id="c1"))
        if with_teacher:
            db.add(TeacherAssignment(school_id=school.id, teacher_id=teacher.id,
                                     class_id="c1", subject_id="s1"))
        db.add(ProgressRecord(school_id=school.id, student_id=student.id, subject_id="s1",
                              topic="Fractions", mastery_score=mastery_score))
        await db.commit()
    return school, student, teacher


@pytest.mark.asyncio
async def test_insight_scan_creates_alert_and_notifies_teacher(db, monkeypatch):
    school, student, teacher = await _seed(db, mastery_score=20)
    student_id, teacher_id = student.id, teacher.id
    monkeypatch.setattr(insight_mod, "llm_chat", _fake_llm("Check in with this student on Fractions."))

    count = await run_insight_scan(db)
    assert count == 1

    db.expire_all()
    actions = (await db.execute(
        select(AgentAction).where(AgentAction.agent_name == "insight_agent")
    )).scalars().all()
    assert len(actions) == 1
    assert actions[0].status == AgentActionStatus.auto_applied
    assert actions[0].payload_json["alert_text"] == "Check in with this student on Fractions."
    assert actions[0].payload_json["student_id"] == student_id

    notifications = (await db.execute(
        select(Notification).where(Notification.user_id == teacher_id)
    )).scalars().all()
    assert len(notifications) == 1
    assert notifications[0].type == "insight_alert"


@pytest.mark.asyncio
async def test_insight_scan_dedups_within_cooldown(db, monkeypatch):
    await _seed(db, mastery_score=20)
    monkeypatch.setattr(insight_mod, "llm_chat", _fake_llm("First alert."))

    first = await run_insight_scan(db)
    assert first == 1

    second = await run_insight_scan(db)
    assert second == 0

    db.expire_all()
    actions = (await db.execute(
        select(AgentAction).where(AgentAction.agent_name == "insight_agent")
    )).scalars().all()
    assert len(actions) == 1


@pytest.mark.asyncio
async def test_insight_scan_skips_mastery_above_threshold(db, monkeypatch):
    await _seed(db, mastery_score=80)
    monkeypatch.setattr(insight_mod, "llm_chat", _fake_llm("Should not be called."))

    count = await run_insight_scan(db)
    assert count == 0


@pytest.mark.asyncio
async def test_insight_scan_skips_without_assigned_teacher(db, monkeypatch):
    await _seed(db, mastery_score=20, with_teacher=False)
    monkeypatch.setattr(insight_mod, "llm_chat", _fake_llm("Should not be called."))

    count = await run_insight_scan(db)
    assert count == 0


@pytest.mark.asyncio
async def test_insight_scan_falls_back_on_llm_failure(db, monkeypatch):
    school, student, teacher = await _seed(db, mastery_score=20)

    async def _boom(messages, task, **kw):
        raise RuntimeError("llm down")

    monkeypatch.setattr(insight_mod, "llm_chat", _boom)

    count = await run_insight_scan(db)
    assert count == 1

    db.expire_all()
    action = (await db.execute(
        select(AgentAction).where(AgentAction.agent_name == "insight_agent")
    )).scalars().first()
    assert "Fractions" in action.payload_json["alert_text"]
