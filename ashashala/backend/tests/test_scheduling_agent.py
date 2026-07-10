"""Scheduling Agent — ai-suggest generates draft options, select persists a
choice + auto-rejects siblings, PATCH re-validates conflicts on edit."""

import json

import pytest
from sqlalchemy import select

from app.agents import scheduling as scheduling_mod
from app.db.tenant_filter import tenant_bypass
from app.models.agent_action import AgentAction, AgentActionStatus
from app.models.structure import TeacherAssignment
from app.models.timetable import Timetable
from app.models.user import UserRole
from tests.conftest import login, make_school, make_user


async def _assign(db, *, teacher_id, school_id, class_id="c1", subject_id="s1"):
    with tenant_bypass():
        db.add(TeacherAssignment(teacher_id=teacher_id, class_id=class_id,
                                 subject_id=subject_id, school_id=school_id))
        await db.commit()


def _fake_llm(payload: dict):
    async def _inner(messages, task, **kw):
        return json.dumps(payload)
    return _inner


@pytest.mark.asyncio
async def test_ai_suggest_creates_pending_actions(client, db, monkeypatch):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="sch1@x.test")
    await _assign(db, teacher_id=teacher.id, school_id=school.id)
    headers = await login(client, "sch1@x.test")

    monkeypatch.setattr(scheduling_mod, "llm_chat", _fake_llm({
        "options": [
            {"strategy": "workload-balanced", "rationale": "spread out",
             "slots": [{"day_of_week": 0, "period_number": 1, "room": None},
                       {"day_of_week": 1, "period_number": 1, "room": None}]},
            {"strategy": "early-week", "rationale": "front-load",
             "slots": [{"day_of_week": 2, "period_number": 1, "room": "R1"},
                       {"day_of_week": 3, "period_number": 1, "room": None}]},
        ]
    }))

    resp = await client.post("/api/v1/teacher/timetable/ai-suggest", headers=headers,
                             json={"class_id": "c1", "subject_id": "s1", "periods_per_week": 2})
    assert resp.status_code == 200, resp.text
    options = resp.json()
    assert len(options) == 2
    assert {o["strategy"] for o in options} == {"workload-balanced", "early-week"}
    assert len(options[0]["slots"]) == 2

    db.expire_all()
    actions = (await db.execute(
        select(AgentAction).where(AgentAction.agent_name == "scheduling_agent")
    )).scalars().all()
    assert len(actions) == 2
    assert all(a.status == AgentActionStatus.pending for a in actions)


@pytest.mark.asyncio
async def test_ai_suggest_filters_hallucinated_slots(client, db, monkeypatch):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="sch2@x.test")
    await _assign(db, teacher_id=teacher.id, school_id=school.id)
    headers = await login(client, "sch2@x.test")

    monkeypatch.setattr(scheduling_mod, "llm_chat", _fake_llm({
        "options": [
            {"strategy": "valid-one", "rationale": "ok",
             "slots": [{"day_of_week": 0, "period_number": 1, "room": None}]},
            {"strategy": "hallucinated", "rationale": "invented a slot outside the grid",
             "slots": [{"day_of_week": 9, "period_number": 99, "room": None}]},
            {"strategy": "valid-two", "rationale": "ok",
             "slots": [{"day_of_week": 5, "period_number": 8, "room": None}]},
        ]
    }))

    resp = await client.post("/api/v1/teacher/timetable/ai-suggest", headers=headers,
                             json={"class_id": "c1", "subject_id": "s1", "periods_per_week": 1})
    assert resp.status_code == 200, resp.text
    options = resp.json()
    assert len(options) == 2
    assert {o["strategy"] for o in options} == {"valid-one", "valid-two"}


@pytest.mark.asyncio
async def test_select_creates_timetable_and_rejects_siblings(client, db, monkeypatch):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="sch3@x.test")
    await _assign(db, teacher_id=teacher.id, school_id=school.id)
    headers = await login(client, "sch3@x.test")

    monkeypatch.setattr(scheduling_mod, "llm_chat", _fake_llm({
        "options": [
            {"strategy": "option-a", "rationale": "a",
             "slots": [{"day_of_week": 0, "period_number": 1, "room": None}]},
            {"strategy": "option-b", "rationale": "b",
             "slots": [{"day_of_week": 1, "period_number": 1, "room": None}]},
        ]
    }))

    suggest = await client.post("/api/v1/teacher/timetable/ai-suggest", headers=headers,
                                json={"class_id": "c1", "subject_id": "s1", "periods_per_week": 1})
    options = suggest.json()
    chosen_id = options[0]["option_id"]
    other_id = options[1]["option_id"]

    resp = await client.post(f"/api/v1/teacher/timetable/{chosen_id}/select", headers=headers)
    assert resp.status_code == 200, resp.text
    created = resp.json()
    assert len(created) == 1
    assert created[0]["day_of_week"] == options[0]["slots"][0]["day_of_week"]

    db.expire_all()
    rows = (await db.execute(select(Timetable).where(Timetable.class_id == "c1"))).scalars().all()
    assert len(rows) == 1

    chosen_action = await db.get(AgentAction, chosen_id)
    other_action = await db.get(AgentAction, other_id)
    assert chosen_action.status == AgentActionStatus.approved
    assert other_action.status == AgentActionStatus.rejected


@pytest.mark.asyncio
async def test_select_conflict_marks_rejected(client, db, monkeypatch):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="sch4@x.test")
    await _assign(db, teacher_id=teacher.id, school_id=school.id)
    headers = await login(client, "sch4@x.test")

    monkeypatch.setattr(scheduling_mod, "llm_chat", _fake_llm({
        "options": [
            {"strategy": "option-a", "rationale": "a",
             "slots": [{"day_of_week": 0, "period_number": 1, "room": None}]},
        ]
    }))
    suggest = await client.post("/api/v1/teacher/timetable/ai-suggest", headers=headers,
                                json={"class_id": "c1", "subject_id": "s1", "periods_per_week": 1})
    option_id = suggest.json()[0]["option_id"]

    # A conflicting entry lands on that exact slot after suggestion time.
    conflict = await client.post("/api/v1/teacher/timetable", headers=headers, json={
        "class_id": "c1", "subject_id": "s1", "day_of_week": 0, "period_number": 1})
    assert conflict.status_code == 200

    resp = await client.post(f"/api/v1/teacher/timetable/{option_id}/select", headers=headers)
    assert resp.status_code == 422

    db.expire_all()
    action = await db.get(AgentAction, option_id)
    assert action.status == AgentActionStatus.rejected


@pytest.mark.asyncio
async def test_patch_timetable_conflict_and_success(client, db):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="sch5@x.test")
    await _assign(db, teacher_id=teacher.id, school_id=school.id)
    headers = await login(client, "sch5@x.test")

    e1 = await client.post("/api/v1/teacher/timetable", headers=headers, json={
        "class_id": "c1", "subject_id": "s1", "day_of_week": 0, "period_number": 1})
    e2 = await client.post("/api/v1/teacher/timetable", headers=headers, json={
        "class_id": "c1", "subject_id": "s1", "day_of_week": 1, "period_number": 1})
    e2_id = e2.json()["id"]

    conflict = await client.patch(f"/api/v1/teacher/timetable/{e2_id}", headers=headers,
                                  json={"day_of_week": 0, "period_number": 1})
    assert conflict.status_code == 422

    ok = await client.patch(f"/api/v1/teacher/timetable/{e2_id}", headers=headers,
                            json={"day_of_week": 2, "period_number": 3})
    assert ok.status_code == 200, ok.text
    assert ok.json()["day_of_week"] == 2
    assert ok.json()["period_number"] == 3
