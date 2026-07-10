"""Scheduled-Learning Agent — daily cron generates topic explainers for that
weekday's Timetable entries; students read them via GET /student/today."""

import json
from datetime import date

import pytest
from sqlalchemy import select

from app.agents import scheduled_learning as sl_mod
from app.agents.scheduled_learning import generate_daily_feed
from app.db.tenant_filter import tenant_bypass
from app.models.feed import LearningFeedItem
from app.models.notification import Notification
from app.models.structure import Enrollment
from app.models.timetable import Timetable
from app.models.user import UserRole
from app.routes import student as student_mod
from tests.conftest import login, make_school, make_user

MONDAY = date(2026, 7, 13)   # weekday() == 0
SUNDAY = date(2026, 7, 12)   # weekday() == 6, no school

_EXPLAINER_JSON = json.dumps({
    "explainer": "Fractions represent parts of a whole.",
    "questions": [
        {"question": "What is 1/2 + 1/2?", "options": ["1", "2"], "answer": "1"},
        {"question": "Define numerator.", "options": None, "answer": "top number"},
    ],
})


def _fake_llm(text=_EXPLAINER_JSON):
    async def _inner(messages, task, **kw):
        return text
    return _inner


async def _seed(db, *, day_of_week=0, topic="Fractions", period_number=1,
                class_id="c1", subject_id="s1"):
    school = await make_school(db)
    student = await make_user(db, role=UserRole.student, school_id=school.id,
                              email=f"sl_stu_{day_of_week}_{period_number}_{topic}@x.test", grade=6)
    with tenant_bypass():
        db.add(Enrollment(school_id=school.id, student_id=student.id, class_id=class_id))
        tt = Timetable(school_id=school.id, teacher_id="teacher-x", class_id=class_id,
                       subject_id=subject_id, day_of_week=day_of_week, period_number=period_number,
                       topic=topic)
        db.add(tt)
        await db.commit()
        await db.refresh(tt)
    return school, student, tt


@pytest.mark.asyncio
async def test_generate_daily_feed_creates_item_and_notifies(db, monkeypatch):
    school, student, tt = await _seed(db)
    student_id = student.id
    monkeypatch.setattr(sl_mod, "llm_chat", _fake_llm())

    count = await generate_daily_feed(db, for_date=MONDAY)
    assert count == 1

    db.expire_all()
    items = (await db.execute(select(LearningFeedItem))).scalars().all()
    assert len(items) == 1
    assert items[0].topic == "Fractions"
    assert items[0].feed_date == MONDAY
    assert len(items[0].questions_json) == 2

    notifications = (await db.execute(
        select(Notification).where(Notification.user_id == student_id)
    )).scalars().all()
    assert len(notifications) == 1
    assert notifications[0].type == "today_feed"


@pytest.mark.asyncio
async def test_generate_daily_feed_is_idempotent_same_day(db, monkeypatch):
    await _seed(db)
    monkeypatch.setattr(sl_mod, "llm_chat", _fake_llm())

    first = await generate_daily_feed(db, for_date=MONDAY)
    second = await generate_daily_feed(db, for_date=MONDAY)
    assert first == 1
    assert second == 0

    db.expire_all()
    items = (await db.execute(select(LearningFeedItem))).scalars().all()
    assert len(items) == 1


@pytest.mark.asyncio
async def test_generate_daily_feed_skips_other_weekday_and_missing_topic(db, monkeypatch):
    school, student, _tt = await _seed(db, day_of_week=0, topic="Fractions")
    with tenant_bypass():
        db.add(Timetable(school_id=school.id, teacher_id="teacher-x", class_id="c1",
                         subject_id="s1", day_of_week=1, period_number=1, topic="Algebra"))
        db.add(Timetable(school_id=school.id, teacher_id="teacher-x", class_id="c1",
                         subject_id="s1", day_of_week=0, period_number=2, topic=None))
        await db.commit()
    monkeypatch.setattr(sl_mod, "llm_chat", _fake_llm())

    count = await generate_daily_feed(db, for_date=MONDAY)
    assert count == 1

    db.expire_all()
    items = (await db.execute(select(LearningFeedItem))).scalars().all()
    assert len(items) == 1
    assert items[0].topic == "Fractions"


@pytest.mark.asyncio
async def test_generate_daily_feed_sunday_short_circuits(db, monkeypatch):
    await _seed(db)

    async def _boom(messages, task, **kw):
        raise AssertionError("LLM should not be called on a no-school day")

    monkeypatch.setattr(sl_mod, "llm_chat", _boom)

    count = await generate_daily_feed(db, for_date=SUNDAY)
    assert count == 0


@pytest.mark.asyncio
async def test_student_today_returns_items_ordered_by_period(client, db, monkeypatch):
    school, student, _tt1 = await _seed(db, day_of_week=0, topic="Fractions", period_number=2)
    with tenant_bypass():
        db.add(Timetable(school_id=school.id, teacher_id="teacher-x", class_id="c1",
                         subject_id="s1", day_of_week=0, period_number=1, topic="Algebra"))
        await db.commit()
    monkeypatch.setattr(sl_mod, "llm_chat", _fake_llm())

    count = await generate_daily_feed(db, for_date=MONDAY)
    assert count == 2

    class _FixedDatetime:
        @classmethod
        def now(cls, tz=None):
            import datetime as _dt
            return _dt.datetime(2026, 7, 13, 6, 0, tzinfo=tz)

    monkeypatch.setattr(student_mod, "datetime", _FixedDatetime)
    headers = await login(client, student.email)

    resp = await client.get("/api/v1/student/today", headers=headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert len(items) == 2
    assert [i["period_number"] for i in items] == [1, 2]
    assert items[0]["topic"] == "Algebra"
    assert items[1]["topic"] == "Fractions"
