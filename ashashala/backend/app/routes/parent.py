"""Parent routes: read-only views of linked children (every read audited)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.permissions import PARENT_PORTAL
from app.db.session import get_db
from app.deps import PageParams, get_linked_child, page_params, require_permission
from app.models.communication import MessageSenderRole, ParentMessage
from app.models.learning import ProgressRecord, QuizAttempt
from app.models.report import Report, ReportStatus
from app.models.structure import Enrollment, ParentStudentLink, TeacherAssignment
from app.models.user import User
from app.schemas.pagination import Page
from app.schemas.parent import (
    NotificationPreferenceOut,
    NotificationPreferencePatch,
    ParentMessageCreate,
    ParentMessageOut,
)
from app.schemas.quiz import QuizAttemptOut
from app.schemas.report import ReportOut
from app.services.audit_service import record_audit
from app.services.notification_preference_service import get_or_create_preference
from app.services.notification_service import notify
from app.services.pdf_service import render_report_pdf

router = APIRouter(prefix="/api/v1/parent", tags=["Parent"])
_guard = require_permission(PARENT_PORTAL)


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
    rows = (await db.execute(
        select(Enrollment).where(Enrollment.student_id == student_id, Enrollment.end_date.is_(None))
    )).scalars().all()
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


@router.get("/children/{student_id}/history", response_model=Page[QuizAttemptOut])
async def child_history(student_id: str, request: Request, page: PageParams = Depends(page_params),
                        parent: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> Page[QuizAttemptOut]:
    await get_linked_child(db, parent, student_id)
    await record_audit(db, action="PARENT_VIEW_CHILD", actor=parent, target_type="student",
                       target_id=student_id, request=request)
    total = (await db.execute(
        select(func.count()).select_from(QuizAttempt).where(QuizAttempt.student_id == student_id)
    )).scalar_one()
    attempts = (await db.execute(
        select(QuizAttempt).where(QuizAttempt.student_id == student_id)
        .order_by(QuizAttempt.attempted_at.desc()).limit(page.limit).offset(page.offset)
    )).scalars().all()
    items = [
        QuizAttemptOut(quiz_id=a.quiz_id, score=a.score, attempted_at=a.attempted_at.isoformat())
        for a in attempts
    ]
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


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
             "class_id": t.class_id, "subject_id": t.subject_id, "room": t.room,
             "topic": t.topic} for t in rows]


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


@router.get("/children/{student_id}/reports", response_model=list[ReportOut])
async def child_reports(student_id: str, request: Request,
                        parent: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[ReportOut]:
    await get_linked_child(db, parent, student_id)
    await record_audit(db, action="PARENT_VIEW_CHILD", actor=parent, target_type="student",
                       target_id=student_id, request=request)
    rows = (await db.execute(
        select(Report).where(Report.student_id == student_id, Report.status == ReportStatus.sent)
        .order_by(Report.period_start.desc())
    )).scalars().all()
    return [ReportOut.model_validate(r) for r in rows]


async def _get_sent_report(db: AsyncSession, student_id: str, report_id: str) -> Report:
    report = await db.get(Report, report_id)
    if report is None or report.student_id != student_id or report.status != ReportStatus.sent:
        raise NotFoundError("Report", report_id)
    return report


@router.get("/children/{student_id}/reports/{report_id}/pdf")
async def child_report_pdf(student_id: str, report_id: str, request: Request,
                           parent: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> Response:
    child = await get_linked_child(db, parent, student_id)
    report = await _get_sent_report(db, student_id, report_id)
    await record_audit(db, action="PARENT_VIEW_CHILD", actor=parent, target_type="student",
                       target_id=student_id, request=request)
    pdf_bytes = render_report_pdf(report, student_name=child.name)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="report-{report.id}.pdf"'})


async def _assert_teacher_assigned_to_child(db: AsyncSession, student_id: str, teacher_id: str) -> None:
    class_ids = await _child_class_ids(db, student_id)
    assigned = (await db.execute(
        select(TeacherAssignment.id).where(
            TeacherAssignment.teacher_id == teacher_id, TeacherAssignment.class_id.in_(class_ids),
            TeacherAssignment.end_date.is_(None),
        )
    )).first() if class_ids else None
    if assigned is None:
        raise ValidationError("That teacher is not assigned to this student")


@router.post("/messages", response_model=ParentMessageOut)
async def send_parent_message(body: ParentMessageCreate, request: Request,
                              parent: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> ParentMessageOut:
    await get_linked_child(db, parent, body.student_id)
    await _assert_teacher_assigned_to_child(db, body.student_id, body.teacher_id)
    msg = ParentMessage(school_id=parent.school_id, student_id=body.student_id, parent_id=parent.id,
                        teacher_id=body.teacher_id, sender_role=MessageSenderRole.parent, body=body.body)
    db.add(msg)
    await db.flush()
    await notify(db, user_id=body.teacher_id, school_id=parent.school_id, type="parent_message",
                title="New message from a parent", body=body.body[:140], link="/teacher/messages")
    await record_audit(db, action="PARENT_MESSAGE_SEND", actor=parent, target_type="parent_message",
                       target_id=body.student_id, request=request)
    return ParentMessageOut.model_validate(msg)


@router.get("/messages", response_model=list[ParentMessageOut])
async def list_parent_messages(student_id: str, teacher_id: str | None = None,
                               parent: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[ParentMessageOut]:
    await get_linked_child(db, parent, student_id)
    stmt = select(ParentMessage).where(
        ParentMessage.student_id == student_id, ParentMessage.parent_id == parent.id,
    )
    if teacher_id is not None:
        stmt = stmt.where(ParentMessage.teacher_id == teacher_id)
    rows = (await db.execute(stmt.order_by(ParentMessage.created_at))).scalars().all()
    unread = [m for m in rows if m.sender_role == MessageSenderRole.teacher and m.read_at is None]
    if unread:
        now = datetime.now(UTC)
        for m in unread:
            m.read_at = now
            db.add(m)
        await db.flush()
    return [ParentMessageOut.model_validate(m) for m in rows]


@router.get("/notification-preferences", response_model=NotificationPreferenceOut)
async def get_notification_preferences(parent: User = Depends(_guard),
                                       db: AsyncSession = Depends(get_db)) -> NotificationPreferenceOut:
    pref = await get_or_create_preference(db, user_id=parent.id, school_id=parent.school_id)
    return NotificationPreferenceOut.model_validate(pref)


@router.patch("/notification-preferences", response_model=NotificationPreferenceOut)
async def update_notification_preferences(body: NotificationPreferencePatch,
                                          parent: User = Depends(_guard),
                                          db: AsyncSession = Depends(get_db)) -> NotificationPreferenceOut:
    pref = await get_or_create_preference(db, user_id=parent.id, school_id=parent.school_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(pref, field, value)
    db.add(pref)
    return NotificationPreferenceOut.model_validate(pref)
