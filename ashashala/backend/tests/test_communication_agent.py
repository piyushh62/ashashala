"""Communication Agent — report-ready sends immediately via every enabled
channel; at-risk drafts stay pending until a teacher approves them through the
generalized AgentAction queue (verifies the approval-handler registry)."""

import json
from datetime import date

import pytest
from sqlalchemy import select

from app.agents import communication as comm_mod
from app.agents.communication import propose_at_risk_message, send_report_message
from app.db.tenant_filter import tenant_bypass
from app.models.agent_action import AgentAction, AgentActionStatus
from app.models.notification import Notification, NotificationChannel
from app.models.report import Report, ReportStatus
from app.models.structure import ParentStudentLink, TeacherAssignment
from app.models.user import UserRole
from tests.conftest import login, make_school, make_user


def _fake_llm(message: str):
    async def _inner(messages, task, **kw):
        return json.dumps({"message": message})
    return _inner


@pytest.mark.asyncio
async def test_send_report_message_notifies_every_enabled_channel(db, monkeypatch):
    school = await make_school(db)
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="cs1@x.test", grade=6)
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="cp1@x.test")
    with tenant_bypass():
        db.add(ParentStudentLink(parent_id=parent.id, student_id=student.id, school_id=school.id))
        report = Report(school_id=school.id, student_id=student.id, period_start=date(2026, 7, 1),
                        period_end=date(2026, 7, 8), narrative="Doing well.", status=ReportStatus.draft)
        db.add(report)
        await db.commit()
        await db.refresh(report)

    monkeypatch.setattr(comm_mod, "llm_chat", _fake_llm("Your child's report is ready."))

    async def _fake_channels(db, *, user_id, school_id):
        return [NotificationChannel.in_app, NotificationChannel.sms]

    monkeypatch.setattr(comm_mod, "get_enabled_channels", _fake_channels)

    report_id = report.id
    parent_id = parent.id
    await send_report_message(db, report=report, actor=None)
    await db.commit()

    db.expire_all()
    refreshed = await db.get(Report, report_id)
    assert refreshed.status == ReportStatus.sent
    assert refreshed.sent_at is not None

    notifications = (await db.execute(
        select(Notification).where(Notification.user_id == parent_id)
    )).scalars().all()
    assert {n.channel for n in notifications} == {NotificationChannel.in_app, NotificationChannel.sms}
    assert all(n.type == "report_ready" for n in notifications)


@pytest.mark.asyncio
async def test_propose_at_risk_message_creates_pending_action_per_parent(db, monkeypatch):
    school = await make_school(db)
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="cs2@x.test", grade=6)
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="cp2@x.test")
    with tenant_bypass():
        link = ParentStudentLink(parent_id=parent.id, student_id=student.id, school_id=school.id)
        db.add(link)
        await db.commit()

    monkeypatch.setattr(comm_mod, "llm_chat", _fake_llm("Your child could use a little extra help."))

    parent_id = parent.id
    await propose_at_risk_message(
        db, school_id=school.id, student=student, parent_links=[link], topic="Fractions",
        mastery_score=20, alert_text="Struggling with fractions.",
    )
    await db.commit()

    db.expire_all()
    actions = (await db.execute(
        select(AgentAction).where(AgentAction.agent_name == "communication_agent")
    )).scalars().all()
    assert len(actions) == 1
    assert actions[0].status == AgentActionStatus.pending
    assert actions[0].payload_json["parent_id"] == parent_id
    assert actions[0].payload_json["message_text"] == "Your child could use a little extra help."


@pytest.mark.asyncio
async def test_approving_at_risk_action_sends_notification(client, db, monkeypatch):
    """End-to-end: approving via POST /agent-actions/{id}/approve invokes the
    registered handler, which notifies the parent — verifies the registry
    wiring in app.routes.agent_actions."""
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="ct1@x.test")
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="cs3@x.test", grade=6)
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="cp3@x.test")
    with tenant_bypass():
        db.add(TeacherAssignment(teacher_id=teacher.id, class_id="c1", subject_id="s1", school_id=school.id))
        link = ParentStudentLink(parent_id=parent.id, student_id=student.id, school_id=school.id)
        db.add(link)
        await db.commit()

    monkeypatch.setattr(comm_mod, "llm_chat", _fake_llm("A note about your child."))
    parent_id = parent.id
    await propose_at_risk_message(
        db, school_id=school.id, student=student, parent_links=[link], topic="Fractions",
        mastery_score=20, alert_text="Struggling with fractions.",
    )
    await db.commit()

    action = (await db.execute(
        select(AgentAction).where(AgentAction.agent_name == "communication_agent")
    )).scalars().first()
    action_id = action.id

    headers = await login(client, "ct1@x.test")
    resp = await client.post(f"/api/v1/agent-actions/{action_id}/approve", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "approved"

    db.expire_all()
    notifications = (await db.execute(
        select(Notification).where(Notification.user_id == parent_id)
    )).scalars().all()
    assert len(notifications) == 1
    assert notifications[0].type == "at_risk_alert"
