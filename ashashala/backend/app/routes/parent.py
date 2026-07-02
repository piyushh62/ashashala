"""Parent routes: read-only views of linked children (every read audited)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_linked_child, require_role
from app.models.learning import ProgressRecord, QuizAttempt
from app.models.structure import Enrollment, ParentStudentLink
from app.models.timetable import ExamTimetable, Timetable
from app.models.user import User, UserRole
from app.services.audit_service import record_audit

router = APIRouter(prefix="/api/v1/parent", tags=["Parent"])
_guard = require_role(UserRole.parent)


@router.get("/children")
async def children(parent: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[dict]:
    links = (await db.execute(
        select(ParentStudentLink).where(ParentStudentLink.parent_id == parent.id)
    )).scalars().all()
    out = []
    for link in links:
        child = await db.get(User, link.student_id)
        if child is not None:
            out.append({"id": child.id, "name": child.name, "grade": child.grade})
    return out


async def _child_class_ids(db: AsyncSession, student_id: str) -> list[str]:
    rows = (await db.execute(select(Enrollment).where(Enrollment.student_id == student_id))).scalars().all()
    return sorted({r.class_id for r in rows})


@router.get("/children/{student_id}/dashboard")
async def child_dashboard(student_id: str, request: Request,
                          parent: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    child = await get_linked_child(db, parent, student_id)
    await record_audit(db, action="PARENT_VIEW_CHILD", actor=parent, target_type="student",
                       target_id=student_id, request=request)
    progress = (await db.execute(select(ProgressRecord).where(ProgressRecord.student_id == student_id))).scalars().all()
    return {
        "student": {"id": child.id, "name": child.name, "grade": child.grade},
        "mastery": [{"topic": p.topic, "score": p.mastery_score} for p in progress],
    }


@router.get("/children/{student_id}/history")
async def child_history(student_id: str, request: Request,
                        parent: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    await get_linked_child(db, parent, student_id)
    await record_audit(db, action="PARENT_VIEW_CHILD", actor=parent, target_type="student",
                       target_id=student_id, request=request)
    attempts = (await db.execute(select(QuizAttempt).where(QuizAttempt.student_id == student_id))).scalars().all()
    return {"quiz_attempts": [{"quiz_id": a.quiz_id, "score": a.score} for a in attempts]}


@router.get("/children/{student_id}/timetable")
async def child_timetable(student_id: str, request: Request,
                          parent: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[dict]:
    await get_linked_child(db, parent, student_id)
    await record_audit(db, action="PARENT_VIEW_CHILD", actor=parent, target_type="student",
                       target_id=student_id, request=request)
    class_ids = await _child_class_ids(db, student_id)
    if not class_ids:
        return []
    rows = (await db.execute(select(Timetable).where(Timetable.class_id.in_(class_ids)))).scalars().all()
    return [{"day_of_week": t.day_of_week, "period_number": t.period_number,
             "class_id": t.class_id, "subject_id": t.subject_id, "room": t.room} for t in rows]


@router.get("/children/{student_id}/exam-timetable")
async def child_exam_timetable(student_id: str, request: Request,
                               parent: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[dict]:
    await get_linked_child(db, parent, student_id)
    await record_audit(db, action="PARENT_VIEW_CHILD", actor=parent, target_type="student",
                       target_id=student_id, request=request)
    class_ids = await _child_class_ids(db, student_id)
    if not class_ids:
        return []
    rows = (await db.execute(select(ExamTimetable).where(ExamTimetable.class_id.in_(class_ids)))).scalars().all()
    return [{"exam_name": e.exam_name, "exam_date": e.exam_date.isoformat(),
             "class_id": e.class_id, "subject_id": e.subject_id} for e in rows]
