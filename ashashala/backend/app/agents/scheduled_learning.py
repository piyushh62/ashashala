"""Scheduled-Learning Agent.

Daily cron (early morning, before the school day) generates a topic explainer
+ micro-questions for every Timetable entry scheduled that weekday, across all
schools. No approval needed — student-facing, low-risk, no AgentAction queue
involved. Students read it any time that day via GET /student/today.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.json_utils import extract_json
from app.agents.prompts.scheduled_learning_prompt import build_explainer_prompt
from app.db.tenant_filter import tenant_bypass
from app.models.feed import LearningFeedItem
from app.models.structure import ClassSection, Enrollment, Subject
from app.models.timetable import Timetable
from app.services.llm_router import chat as llm_chat
from app.services.notification_service import notify

logger = logging.getLogger(__name__)

MAX_QUESTIONS = 3


def _normalize_questions(raw: dict) -> list[dict]:
    questions = raw.get("questions", []) if isinstance(raw, dict) else []
    cleaned: list[dict] = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        question_text = str(q.get("question", "")).strip()
        if not question_text:
            continue
        options = q.get("options")
        cleaned.append({
            "question": question_text,
            "options": [str(o) for o in options][:6] if isinstance(options, list) else None,
            "answer": str(q.get("answer", "")).strip(),
        })
    return cleaned[:MAX_QUESTIONS]


async def generate_daily_feed(db: AsyncSession, *, for_date: date) -> int:
    """Generate today's learning feed items. Returns the number created."""
    if for_date.weekday() > 5:
        return 0

    created = 0
    with tenant_bypass():
        entries = (await db.execute(
            select(Timetable).where(
                Timetable.day_of_week == for_date.weekday(), Timetable.topic.is_not(None)
            )
        )).scalars().all()

        for entry in entries:
            already_exists = (await db.execute(
                select(LearningFeedItem.id).where(
                    LearningFeedItem.timetable_id == entry.id, LearningFeedItem.feed_date == for_date
                )
            )).first()
            if already_exists is not None:
                continue

            subject = await db.get(Subject, entry.subject_id)
            subject_name = subject.name if subject else "General"
            class_section = await db.get(ClassSection, entry.class_id)
            grade = class_section.grade_level if class_section else None

            try:
                prompt = build_explainer_prompt(topic=entry.topic, subject=subject_name, grade=grade)
                raw_text = await llm_chat(
                    messages=[{"role": "user", "content": prompt}],
                    task="explain", school_id=entry.school_id, user_id=entry.teacher_id,
                )
                parsed = extract_json(raw_text)
                explainer = str(parsed.get("explainer", "")).strip() if isinstance(parsed, dict) else ""
                questions = _normalize_questions(parsed) if isinstance(parsed, dict) else []
            except Exception as e:  # noqa: BLE001 — one bad response must not abort the batch
                logger.warning("Scheduled-learning generation failed (timetable_id=%s): %s", entry.id, e)
                continue

            if not explainer or not questions:
                logger.warning(
                    "Scheduled-learning produced empty content (timetable_id=%s), skipping", entry.id
                )
                continue

            item = LearningFeedItem(
                school_id=entry.school_id, timetable_id=entry.id, class_id=entry.class_id,
                subject_id=entry.subject_id, topic=entry.topic, explainer=explainer,
                questions_json=questions, feed_date=for_date,
            )
            db.add(item)
            await db.flush()

            student_ids = (await db.execute(
                select(Enrollment.student_id).where(
                    Enrollment.class_id == entry.class_id, Enrollment.end_date.is_(None)
                )
            )).scalars().all()
            for student_id in student_ids:
                await notify(
                    db, user_id=student_id, school_id=entry.school_id, type="today_feed",
                    title=f"Today's topic: {entry.topic}", body=explainer[:140], link="/student/today",
                )
            created += 1

        await db.commit()

    return created
