"""Progress agent — mastery update via exponential moving average (Section 7.6).

    new_score = round(0.7 * old_score + 0.3 * attempt_score * 100)

Upserts ProgressRecord(student_id, subject_id, topic). A brand-new topic starts
from the attempt itself (old_score defaults to 0).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning import ProgressRecord
from app.models.mixins import utcnow
from app.models.user import User


def ema(old_score: int, attempt_score: float) -> int:
    """attempt_score is 0.0-1.0; returns a 0-100 integer mastery."""
    return int(round(0.7 * old_score + 0.3 * attempt_score * 100))


async def update_mastery(
    db: AsyncSession,
    student: User,
    *,
    subject_id: str | None,
    topic: str,
    attempt_score: float,
) -> dict:
    """Apply the EMA update and return {topic, subject_id, old, new}."""
    stmt = select(ProgressRecord).where(
        ProgressRecord.student_id == student.id,
        ProgressRecord.topic == topic,
    )
    if subject_id is None:
        stmt = stmt.where(ProgressRecord.subject_id.is_(None))
    else:
        stmt = stmt.where(ProgressRecord.subject_id == subject_id)

    rec = (await db.execute(stmt)).scalars().first()
    old = rec.mastery_score if rec is not None else 0
    new = ema(old, attempt_score)

    if rec is None:
        rec = ProgressRecord(
            school_id=student.school_id, student_id=student.id,
            subject_id=subject_id, topic=topic, mastery_score=new,
            last_reviewed_at=utcnow(),
        )
        db.add(rec)
    else:
        rec.mastery_score = new
        rec.last_reviewed_at = utcnow()
        db.add(rec)
    await db.flush()

    return {"topic": topic, "subject_id": subject_id, "old": old, "new": new}
