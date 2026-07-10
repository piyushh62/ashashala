"""Scheduling Agent.

Proposes 2-4 draft timetable slot options for a (teacher, class, subject),
grounded in the school's actual free/occupied slot grid. The LLM only picks
among slots we hand it; every option is re-validated against that same
free-slot set afterward (hallucination guard) before it's ever queued as an
AgentAction — see `app/routes/teacher.py::ai_suggest_timetable`.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.json_utils import extract_json
from app.agents.prompts.scheduling_prompt import build_scheduling_prompt
from app.core.config import settings
from app.models.timetable import Timetable
from app.models.user import User
from app.services.llm_router import chat as llm_chat

logger = logging.getLogger(__name__)

MAX_OPTIONS = 4


async def _free_slots_for(
    db: AsyncSession, *, teacher_id: str, class_id: str,
) -> tuple[set[tuple[int, int]], dict[int, int]]:
    """Return (free_slots, teacher_load_by_day) for the full weekly grid."""
    class_rows = (await db.execute(
        select(Timetable.day_of_week, Timetable.period_number).where(Timetable.class_id == class_id)
    )).all()
    teacher_rows = (await db.execute(
        select(Timetable.day_of_week, Timetable.period_number).where(Timetable.teacher_id == teacher_id)
    )).all()

    occupied = {(d, p) for d, p in class_rows} | {(d, p) for d, p in teacher_rows}
    all_slots = {
        (d, p)
        for d in range(6)
        for p in range(1, settings.SCHEDULING_MAX_PERIODS_PER_DAY + 1)
    }
    free = all_slots - occupied

    teacher_load: dict[int, int] = {}
    for d, _ in teacher_rows:
        teacher_load[d] = teacher_load.get(d, 0) + 1

    return free, teacher_load


async def _class_subject_days(db: AsyncSession, *, class_id: str, subject_id: str) -> dict[int, int]:
    rows = (await db.execute(
        select(Timetable.day_of_week).where(
            Timetable.class_id == class_id, Timetable.subject_id == subject_id
        )
    )).all()
    counts: dict[int, int] = {}
    for (d,) in rows:
        counts[d] = counts.get(d, 0) + 1
    return counts


def _validate_option(raw_option: dict, free_slots: set[tuple[int, int]], periods_per_week: int) -> dict | None:
    if not isinstance(raw_option, dict):
        return None
    strategy = str(raw_option.get("strategy", "")).strip() or "suggested"
    rationale = str(raw_option.get("rationale", "")).strip()

    seen: set[tuple[int, int]] = set()
    valid_slots: list[dict] = []
    for slot in raw_option.get("slots", []):
        if not isinstance(slot, dict):
            continue
        try:
            day = int(slot.get("day_of_week"))
            period = int(slot.get("period_number"))
        except (TypeError, ValueError):
            continue
        pair = (day, period)
        if pair not in free_slots or pair in seen:
            continue
        seen.add(pair)
        room = slot.get("room")
        valid_slots.append({
            "day_of_week": day, "period_number": period,
            "room": str(room) if room else None,
        })

    if len(valid_slots) != periods_per_week:
        return None
    return {"strategy": strategy, "rationale": rationale, "slots": valid_slots}


async def generate_timetable_options(
    db: AsyncSession,
    teacher: User,
    *,
    class_id: str,
    subject_id: str,
    periods_per_week: int,
    lang: str = "en",
) -> list[dict]:
    """Generate 2-4 valid draft timetable options. Raises ValueError if none
    survive validation against the real free-slot grid."""
    free_slots, teacher_load = await _free_slots_for(db, teacher_id=teacher.id, class_id=class_id)
    class_subject_days = await _class_subject_days(db, class_id=class_id, subject_id=subject_id)

    prompt = build_scheduling_prompt(
        free_slots=sorted(free_slots), teacher_load=teacher_load,
        class_subject_days=class_subject_days, periods_per_week=periods_per_week, lang=lang,
    )
    raw_text = await llm_chat(
        messages=[{"role": "user", "content": prompt}],
        task="schedule", lang_hint=lang, school_id=teacher.school_id, user_id=teacher.id,
    )
    parsed = extract_json(raw_text)
    raw_options = parsed.get("options", []) if isinstance(parsed, dict) else []

    options: list[dict] = []
    for raw_option in raw_options:
        validated = _validate_option(raw_option, free_slots, periods_per_week)
        if validated is not None:
            options.append(validated)
        if len(options) >= MAX_OPTIONS:
            break

    if not options:
        raise ValueError("Scheduling agent produced no valid options")
    return options
