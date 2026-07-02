"""Student routes: dashboard, classes, timetable, quizzes, progress, export.

Chat/voice endpoints arrive in Phase 3 (stubbed 501 here).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.db.session import get_db
from app.deps import require_role
from app.models.learning import Message, ProgressRecord, Quiz, QuizAttempt, QuizStatus
from app.models.structure import Enrollment
from app.models.timetable import ExamTimetable, Timetable
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/v1/student", tags=["Student"])
_guard = require_role(UserRole.student)


async def _class_ids(db: AsyncSession, student: User) -> list[str]:
    rows = (await db.execute(select(Enrollment).where(Enrollment.student_id == student.id))).scalars().all()
    return sorted({r.class_id for r in rows})


@router.get("/classes")
async def my_classes(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    return {"class_ids": await _class_ids(db, student)}


@router.get("/dashboard")
async def dashboard(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    progress = (await db.execute(
        select(ProgressRecord).where(ProgressRecord.student_id == student.id)
    )).scalars().all()
    return {
        "name": student.name,
        "grade": student.grade,
        "mastery": [{"topic": p.topic, "score": p.mastery_score} for p in progress],
        "recommended_topic": min(progress, key=lambda p: p.mastery_score).topic if progress else None,
    }


@router.get("/timetable")
async def timetable(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[dict]:
    class_ids = await _class_ids(db, student)
    if not class_ids:
        return []
    rows = (await db.execute(select(Timetable).where(Timetable.class_id.in_(class_ids)))).scalars().all()
    return [{"day_of_week": t.day_of_week, "period_number": t.period_number,
             "class_id": t.class_id, "subject_id": t.subject_id, "room": t.room} for t in rows]


@router.get("/exam-timetable")
async def exam_timetable(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[dict]:
    class_ids = await _class_ids(db, student)
    if not class_ids:
        return []
    rows = (await db.execute(select(ExamTimetable).where(ExamTimetable.class_id.in_(class_ids)))).scalars().all()
    return [{"exam_name": e.exam_name, "exam_date": e.exam_date.isoformat(),
             "class_id": e.class_id, "subject_id": e.subject_id} for e in rows]


@router.get("/quizzes")
async def quizzes(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[dict]:
    class_ids = await _class_ids(db, student)
    if not class_ids:
        return []
    rows = (await db.execute(
        select(Quiz).where(Quiz.class_id.in_(class_ids), Quiz.status == QuizStatus.approved)
    )).scalars().all()
    return [{"id": q.id, "topic": q.topic, "class_id": q.class_id} for q in rows]


@router.get("/progress")
async def progress(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (await db.execute(select(ProgressRecord).where(ProgressRecord.student_id == student.id))).scalars().all()
    return [{"topic": p.topic, "subject_id": p.subject_id, "mastery_score": p.mastery_score} for p in rows]


@router.get("/history")
async def history(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    attempts = (await db.execute(select(QuizAttempt).where(QuizAttempt.student_id == student.id))).scalars().all()
    return {"quiz_attempts": [{"quiz_id": a.quiz_id, "score": a.score} for a in attempts]}


@router.get("/data-export")
async def data_export(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    """GDPR-style export of the student's own data."""
    attempts = (await db.execute(select(QuizAttempt).where(QuizAttempt.student_id == student.id))).scalars().all()
    progress = (await db.execute(select(ProgressRecord).where(ProgressRecord.student_id == student.id))).scalars().all()
    # Messages via the student's chat sessions are Phase 3; include mastery + attempts now.
    return {
        "student": {"id": student.id, "name": student.name, "email": student.email, "grade": student.grade},
        "quiz_attempts": [{"quiz_id": a.quiz_id, "score": a.score, "answers": a.answers_json} for a in attempts],
        "mastery": [{"topic": p.topic, "score": p.mastery_score} for p in progress],
    }


@router.post("/chat")
async def chat_stub() -> dict:
    raise AppError("Chat arrives in Phase 3", error_code="NOT_IMPLEMENTED", status_code=501)
