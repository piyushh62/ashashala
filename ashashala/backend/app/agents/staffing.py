"""Staffing Agent (master doc §5.2).

"Teacher marked absent -> Suggests substitute from available teachers ->
Admin approves." Fires synchronously when a school admin marks a teacher
absent (POST /school/teacher-absences). For each Timetable slot the absent
teacher was scheduled to teach that weekday, ranks other teachers in the
school as substitute candidates (free that period, same-subject experience
ranked first) and queues one AgentAction per slot for admin approval via the
existing generic queue. No LLM call — availability/subject matching is
deterministic, so this stays fast and free.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.structure import ClassSection, Subject, TeacherAssignment
from app.models.timetable import Timetable
from app.models.user import User, UserRole
from app.services.rbac_service import propose_agent_action

AGENT_NAME = "staffing_agent"
ACTION_TYPE = "substitute_suggestion"
MAX_CANDIDATES = 3


async def suggest_substitutes(
    db: AsyncSession, *, school_id: str, teacher_id: str, absence_date: date,
) -> int:
    """Queue one substitute-suggestion AgentAction per timetable slot the
    absent teacher was scheduled to teach that weekday. Returns the count
    queued (0 if it's a no-school day, the teacher has no slots that weekday,
    or no other teacher is free for a given slot)."""
    weekday = absence_date.weekday()
    if weekday > 5:
        return 0

    slots = (await db.execute(
        select(Timetable).where(Timetable.teacher_id == teacher_id, Timetable.day_of_week == weekday)
    )).scalars().all()
    if not slots:
        return 0

    # Every other teacher's slots that weekday, to check who's actually free.
    busy = {
        (t.teacher_id, t.period_number)
        for t in (await db.execute(
            select(Timetable).where(Timetable.day_of_week == weekday, Timetable.teacher_id != teacher_id)
        )).scalars().all()
    }
    # Subject -> teachers who've been assigned to teach it, to rank candidates
    # who already have relevant experience above a cold substitute.
    same_subject_teachers: dict[str, set[str]] = {}
    for subject_id, tid in (await db.execute(
        select(TeacherAssignment.subject_id, TeacherAssignment.teacher_id).where(
            TeacherAssignment.end_date.is_(None), TeacherAssignment.teacher_id != teacher_id
        )
    )).all():
        same_subject_teachers.setdefault(subject_id, set()).add(tid)

    teachers = {
        u.id: u.name for u in (await db.execute(
            select(User).where(
                User.school_id == school_id, User.role == UserRole.teacher,
                User.id != teacher_id, User.is_active.is_(True),
            )
        )).scalars().all()
    }
    if not teachers:
        return 0

    created = 0
    for slot in slots:
        available = [tid for tid in teachers if (tid, slot.period_number) not in busy]
        if not available:
            continue
        subject_matches = same_subject_teachers.get(slot.subject_id, set())
        ranked = sorted(available, key=lambda tid: tid not in subject_matches)[:MAX_CANDIDATES]

        class_section = await db.get(ClassSection, slot.class_id)
        subject = await db.get(Subject, slot.subject_id)
        candidates = [
            {
                "teacher_id": tid, "name": teachers[tid],
                "reason": "Has taught this subject before" if tid in subject_matches else "Available this period",
            }
            for tid in ranked
        ]
        await propose_agent_action(
            db, school_id=school_id, agent_name=AGENT_NAME, action_type=ACTION_TYPE,
            payload={
                "timetable_id": slot.id, "absent_teacher_id": teacher_id,
                "absence_date": absence_date.isoformat(), "class_id": slot.class_id,
                "class_name": class_section.name if class_section else "Unknown",
                "subject_id": slot.subject_id, "subject_name": subject.name if subject else "Unknown",
                "period_number": slot.period_number, "candidates": candidates,
            },
        )
        created += 1
    return created
