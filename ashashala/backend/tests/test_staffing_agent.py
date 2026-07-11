"""Staffing Agent (master doc §5.2) — POST /school/teacher-absences fires
`suggest_substitutes`, which queues one substitute-suggestion AgentAction per
timetable slot the absent teacher was scheduled to teach that weekday;
approving one notifies the top-ranked candidate."""

import pytest
from sqlalchemy import select

from app.agents.staffing import suggest_substitutes
from app.core.permissions import AGENT_ACTION_APPROVE, AGENT_ACTION_VIEW
from app.db.tenant_filter import tenant_bypass
from app.models.agent_action import AgentAction, AgentActionStatus
from app.models.notification import Notification
from app.models.structure import ClassSection, Subject, TeacherAssignment
from app.models.timetable import Timetable
from app.models.user import UserRole
from tests.conftest import login, make_school, make_user

MONDAY = "2026-07-13"  # date(2026, 7, 13).weekday() == 0
SUNDAY = "2026-07-12"  # weekday() == 6, no school


async def _seed(db):
    school = await make_school(db)
    absent = await make_user(db, role=UserRole.teacher, school_id=school.id, email="absent_tea@x.test")
    free_generalist = await make_user(db, role=UserRole.teacher, school_id=school.id, email="free_tea@x.test")
    same_subject = await make_user(db, role=UserRole.teacher, school_id=school.id, email="expert_tea@x.test")
    busy = await make_user(db, role=UserRole.teacher, school_id=school.id, email="busy_tea@x.test")
    admin = await make_user(db, role=UserRole.school_admin, school_id=school.id, email="staff_admin@x.test")
    with tenant_bypass():
        subject = Subject(school_id=school.id, name="Mathematics")
        db.add(subject)
        db.add(ClassSection(school_id=school.id, name="Class 7B", grade_level=7, id="class-7b"))
        await db.flush()
        # Absent teacher teaches period 1 Monday.
        db.add(Timetable(school_id=school.id, teacher_id=absent.id, class_id="class-7b",
                         subject_id=subject.id, day_of_week=0, period_number=1))
        # `busy` teacher is also scheduled period 1 Monday elsewhere -> not available.
        db.add(Timetable(school_id=school.id, teacher_id=busy.id, class_id="class-other",
                         subject_id=subject.id, day_of_week=0, period_number=1))
        # `same_subject` has taught this subject before (ranked first).
        db.add(TeacherAssignment(school_id=school.id, teacher_id=same_subject.id,
                                 class_id="class-other", subject_id=subject.id))
        await db.commit()
    return school, absent, free_generalist, same_subject, busy, admin, subject


@pytest.mark.asyncio
async def test_suggest_substitutes_ranks_subject_experience_first(db):
    school, absent, free_generalist, same_subject, busy, admin, subject = await _seed(db)
    absent_id, subject_id, busy_id, same_subject_id = absent.id, subject.id, busy.id, same_subject.id
    from datetime import date

    count = await suggest_substitutes(db, school_id=school.id, teacher_id=absent_id,
                                      absence_date=date(2026, 7, 13))
    assert count == 1

    db.expire_all()
    actions = (await db.execute(select(AgentAction).where(AgentAction.agent_name == "staffing_agent"))).scalars().all()
    assert len(actions) == 1
    payload = actions[0].payload_json
    assert payload["absent_teacher_id"] == absent_id
    assert payload["subject_id"] == subject_id
    candidate_ids = [c["teacher_id"] for c in payload["candidates"]]
    assert busy_id not in candidate_ids          # busy that period -> excluded
    assert candidate_ids[0] == same_subject_id   # subject experience ranked first


@pytest.mark.asyncio
async def test_suggest_substitutes_no_school_on_sunday(db):
    school, absent, *_ = await _seed(db)
    from datetime import date

    count = await suggest_substitutes(db, school_id=school.id, teacher_id=absent.id,
                                      absence_date=date(2026, 7, 12))
    assert count == 0


@pytest.mark.asyncio
async def test_mark_teacher_absent_route_queues_suggestions(client, db):
    school, absent, free_generalist, same_subject, busy, admin, subject = await _seed(db)
    headers = await login(client, "staff_admin@x.test")

    resp = await client.post("/api/v1/school/teacher-absences", headers=headers, json={
        "teacher_id": absent.id, "absence_date": MONDAY, "reason": "sick",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["teacher_id"] == absent.id
    assert body["substitute_suggestions"] == 1

    pending = await client.get("/api/v1/agent-actions?agent_name=staffing_agent", headers=headers)
    assert pending.status_code == 200
    assert pending.json()["total"] == 1


@pytest.mark.asyncio
async def test_approving_substitute_suggestion_notifies_top_candidate(client, db):
    school, absent, free_generalist, same_subject, busy, admin, subject = await _seed(db)
    absent_id, same_subject_id = absent.id, same_subject.id
    headers = await login(client, "staff_admin@x.test")

    await client.post("/api/v1/school/teacher-absences", headers=headers, json={
        "teacher_id": absent_id, "absence_date": MONDAY,
    })
    action = (await db.execute(
        select(AgentAction).where(AgentAction.agent_name == "staffing_agent")
    )).scalars().first()
    action_id = action.id

    approve = await client.post(f"/api/v1/agent-actions/{action_id}/approve", headers=headers)
    assert approve.status_code == 200
    assert approve.json()["status"] == AgentActionStatus.approved.value

    notifications = (await db.execute(
        select(Notification).where(Notification.user_id == same_subject_id, Notification.type == "substitute_request")
    )).scalars().all()
    assert len(notifications) == 1
