"""Reporting Agent — weekly report generation: mastery snapshot + quiz trend
are deterministic, the narrative is LLM-composed with a templated fallback.
Governance: reports_auto_approve (default off) controls draft-vs-auto-send."""

import json
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from app.agents import reporting as reporting_mod
from app.agents.reporting import generate_reports
from app.db.tenant_filter import tenant_bypass
from app.models.agent_action import AgentAction, AgentActionStatus
from app.models.learning import ProgressRecord, QuizAttempt
from app.models.notification import Notification
from app.models.report import Report, ReportStatus
from app.models.structure import Enrollment, ParentStudentLink
from app.models.user import UserRole
from tests.conftest import make_school, make_user

PERIOD_START = date(2026, 7, 1)
PERIOD_END = date(2026, 7, 8)


def _fake_llm(narrative: str = "Great progress this week."):
    async def _inner(messages, task, **kw):
        return json.dumps({"narrative": narrative})
    return _inner


async def _seed(db, *, with_parent=True, auto_approve=False, mastery_score=70):
    school = await make_school(db, reports_auto_approve=auto_approve)
    student = await make_user(db, role=UserRole.student, school_id=school.id,
                              email=f"rep_stu_{with_parent}_{auto_approve}_{mastery_score}@x.test", grade=6)
    with tenant_bypass():
        db.add(Enrollment(school_id=school.id, student_id=student.id, class_id="c1"))
        db.add(ProgressRecord(school_id=school.id, student_id=student.id, subject_id="s1",
                              topic="Fractions", mastery_score=mastery_score))
        db.add(QuizAttempt(school_id=school.id, student_id=student.id, quiz_id="q1", score=85.0,
                           attempted_at=datetime(2026, 7, 3, 10, 0, tzinfo=UTC)))
        if with_parent:
            parent = await make_user(db, role=UserRole.parent, school_id=school.id,
                                     email=f"rep_par_{with_parent}_{auto_approve}_{mastery_score}@x.test")
            db.add(ParentStudentLink(parent_id=parent.id, student_id=student.id, school_id=school.id))
        await db.commit()
    return school, student


@pytest.mark.asyncio
async def test_generate_reports_creates_draft_and_pending_action(db, monkeypatch):
    school, student = await _seed(db)
    monkeypatch.setattr(reporting_mod, "llm_chat", _fake_llm("Great progress this week."))

    student_id = student.id
    count = await generate_reports(db, period_start=PERIOD_START, period_end=PERIOD_END)
    assert count == 1

    db.expire_all()
    reports = (await db.execute(select(Report).where(Report.student_id == student_id))).scalars().all()
    assert len(reports) == 1
    assert reports[0].status == ReportStatus.draft
    assert reports[0].narrative == "Great progress this week."
    assert reports[0].sent_at is None

    actions = (await db.execute(
        select(AgentAction).where(AgentAction.agent_name == "reporting_agent")
    )).scalars().all()
    assert len(actions) == 1
    assert actions[0].status == AgentActionStatus.pending
    assert actions[0].payload_json["report_id"] == reports[0].id


@pytest.mark.asyncio
async def test_generate_reports_auto_approve_sends_immediately(db, monkeypatch):
    school, student = await _seed(db, auto_approve=True)
    monkeypatch.setattr(reporting_mod, "llm_chat", _fake_llm())
    monkeypatch.setattr(reporting_mod.communication, "llm_chat", _fake_llm("Your report is ready."))

    student_id = student.id
    count = await generate_reports(db, period_start=PERIOD_START, period_end=PERIOD_END)
    assert count == 1

    db.expire_all()
    report = (await db.execute(select(Report).where(Report.student_id == student_id))).scalars().first()
    assert report.status == ReportStatus.sent
    assert report.sent_at is not None

    action = (await db.execute(
        select(AgentAction).where(AgentAction.agent_name == "reporting_agent")
    )).scalars().first()
    assert action.status == AgentActionStatus.auto_applied

    parent_link = (await db.execute(
        select(ParentStudentLink).where(ParentStudentLink.student_id == student_id)
    )).scalars().first()
    notifications = (await db.execute(
        select(Notification).where(Notification.user_id == parent_link.parent_id)
    )).scalars().all()
    assert len(notifications) == 1
    assert notifications[0].type == "report_ready"


@pytest.mark.asyncio
async def test_generate_reports_idempotent_same_period(db, monkeypatch):
    await _seed(db)
    monkeypatch.setattr(reporting_mod, "llm_chat", _fake_llm())

    first = await generate_reports(db, period_start=PERIOD_START, period_end=PERIOD_END)
    second = await generate_reports(db, period_start=PERIOD_START, period_end=PERIOD_END)
    assert first == 1
    assert second == 0


@pytest.mark.asyncio
async def test_generate_reports_skips_students_without_parent(db, monkeypatch):
    await _seed(db, with_parent=False)
    monkeypatch.setattr(reporting_mod, "llm_chat", _fake_llm())

    count = await generate_reports(db, period_start=PERIOD_START, period_end=PERIOD_END)
    assert count == 0


@pytest.mark.asyncio
async def test_generate_reports_falls_back_on_llm_failure(db, monkeypatch):
    school, student = await _seed(db)

    async def _boom(messages, task, **kw):
        raise RuntimeError("llm down")

    monkeypatch.setattr(reporting_mod, "llm_chat", _boom)

    student_id = student.id
    count = await generate_reports(db, period_start=PERIOD_START, period_end=PERIOD_END)
    assert count == 1

    db.expire_all()
    report = (await db.execute(select(Report).where(Report.student_id == student_id))).scalars().first()
    assert "Fractions" in report.narrative
