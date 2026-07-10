"""Teacher routes: materials (file/url/youtube), timetables, dashboard."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.core.permissions import TEACHER_PORTAL
from app.db.session import get_db
from app.deps import PageParams, page_params, require_permission
from app.models.document import DocStatus, Document, SourceType
from app.models.flagged_answer import FlaggedAnswer, FlagStatus
from app.models.learning import ProgressRecord, Quiz, QuizStatus
from app.models.school import School
from app.models.structure import ClassSection, Enrollment, ParentStudentLink, Subject, TeacherAssignment
from app.models.timetable import ExamTimetable, Timetable
from app.models.user import User, UserRole
from app.schemas.school_admin import UserCreatedResponse, UserOut
from app.schemas.teacher import (
    DocumentOut,
    ExamTimetableCreate,
    ExamTimetableOut,
    FlaggedAnswerOut,
    FlaggedAnswerOverride,
    MaterialUrlCreate,
    MaterialYoutubeCreate,
    ParentCreate,
    QuizApproval,
    StudentCreate,
    TimetableCreate,
    TimetableOut,
    TimetableUpdate,
)
from app.schemas.pagination import Page
from app.services.audit_service import record_audit
from app.services.ingestion.pipeline import ingest_document
from app.services.notification_service import notify
from app.services.r2_client import get_storage_client
from app.services.rbac_service import can_create_role

router = APIRouter(prefix="/api/v1/teacher", tags=["Teacher"])
_guard = require_permission(TEACHER_PORTAL)

_EXT_TO_TYPE = {"pdf": SourceType.pdf, "docx": SourceType.docx, "txt": SourceType.txt,
                "jpg": SourceType.image, "jpeg": SourceType.image, "png": SourceType.image}


async def _assert_assigned(db: AsyncSession, teacher: User, class_id: str, subject_id: str | None) -> None:
    stmt = select(TeacherAssignment).where(
        TeacherAssignment.teacher_id == teacher.id, TeacherAssignment.class_id == class_id,
        TeacherAssignment.end_date.is_(None),
    )
    if subject_id:
        stmt = stmt.where(TeacherAssignment.subject_id == subject_id)
    if (await db.execute(stmt)).first() is None:
        raise ForbiddenError("Not assigned to this class/subject")


async def _feature_enabled(db: AsyncSession, school_id: str, flag: str) -> bool:
    school = await db.get(School, school_id)
    return bool(school and school.features_json.get(flag, True))


async def _create_and_schedule(
    db: AsyncSession, tasks: BackgroundTasks, teacher: User, request: Request, *,
    class_id: str, subject_id: str | None, filename: str, source_type: SourceType,
    source_ref: str | None, storage_url: str | None, data: bytes | None,
    content_type: str | None = None,
) -> Document:
    doc = Document(school_id=teacher.school_id, class_id=class_id, subject_id=subject_id,
                   uploaded_by_teacher_id=teacher.id, filename=filename, storage_url=storage_url,
                   source_type=source_type, source_ref=source_ref, status=DocStatus.pending)
    db.add(doc)
    await db.flush()
    await record_audit(db, action="MATERIAL_UPLOAD", actor=teacher, target_type="document",
                       target_id=doc.id, payload={"type": source_type.value}, request=request)
    tasks.add_task(ingest_document, doc_id=doc.id, school_id=teacher.school_id, class_id=class_id,
                   subject_id=subject_id, source_type=source_type, data=data, source_ref=source_ref,
                   content_type=content_type)
    return doc


@router.post("/materials/file", response_model=DocumentOut)
async def upload_file(request: Request, tasks: BackgroundTasks, file: UploadFile,
                      class_id: str = Form(...), subject_id: str | None = Form(default=None),
                      teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> DocumentOut:
    await _assert_assigned(db, teacher, class_id, subject_id)
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    source_type = _EXT_TO_TYPE.get(ext)
    if source_type is None:
        raise ValidationError(f"Unsupported file type: .{ext}")
    if source_type == SourceType.image and not await _feature_enabled(db, teacher.school_id, "ocr"):
        raise ForbiddenError("OCR feature disabled for this school")

    data = await file.read()
    key = f"school_{teacher.school_id}/class_{class_id}/{file.filename}"
    storage_url = await get_storage_client().upload_bytes(key, data, file.content_type or "application/octet-stream")
    doc = await _create_and_schedule(db, tasks, teacher, request, class_id=class_id, subject_id=subject_id,
                                     filename=file.filename or key, source_type=source_type,
                                     source_ref=file.filename, storage_url=storage_url, data=data,
                                     content_type=file.content_type)
    return DocumentOut.model_validate(doc)


@router.post("/materials/url", response_model=DocumentOut)
async def upload_url(body: MaterialUrlCreate, request: Request, tasks: BackgroundTasks,
                     teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> DocumentOut:
    await _assert_assigned(db, teacher, body.class_id, body.subject_id)
    doc = await _create_and_schedule(db, tasks, teacher, request, class_id=body.class_id,
                                     subject_id=body.subject_id, filename=body.url, source_type=SourceType.url,
                                     source_ref=body.url, storage_url=None, data=None)
    return DocumentOut.model_validate(doc)


@router.post("/materials/youtube", response_model=DocumentOut)
async def upload_youtube(body: MaterialYoutubeCreate, request: Request, tasks: BackgroundTasks,
                         teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> DocumentOut:
    await _assert_assigned(db, teacher, body.class_id, body.subject_id)
    if not await _feature_enabled(db, teacher.school_id, "youtube"):
        raise ForbiddenError("YouTube feature disabled for this school")
    doc = await _create_and_schedule(db, tasks, teacher, request, class_id=body.class_id,
                                     subject_id=body.subject_id, filename=body.url, source_type=SourceType.youtube,
                                     source_ref=body.url, storage_url=None, data=None)
    return DocumentOut.model_validate(doc)


@router.get("/materials", response_model=Page[DocumentOut])
async def list_materials(page: PageParams = Depends(page_params), teacher: User = Depends(_guard),
                         db: AsyncSession = Depends(get_db)) -> Page[DocumentOut]:
    total = (await db.execute(
        select(func.count()).select_from(Document).where(Document.uploaded_by_teacher_id == teacher.id)
    )).scalar_one()
    docs = (await db.execute(
        select(Document).where(Document.uploaded_by_teacher_id == teacher.id)
        .order_by(Document.created_at.desc()).limit(page.limit).offset(page.offset)
    )).scalars().all()
    return Page(items=[DocumentOut.model_validate(d) for d in docs], total=total,
               limit=page.limit, offset=page.offset)


@router.delete("/materials/{doc_id}")
async def delete_material(doc_id: str, request: Request,
                          teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    doc = await db.get(Document, doc_id)
    if doc is None or doc.school_id != teacher.school_id:
        raise NotFoundError("Document", doc_id)
    await db.delete(doc)
    await record_audit(db, action="MATERIAL_DELETE", actor=teacher, target_type="document",
                       target_id=doc_id, request=request)
    return {"status": "deleted", "id": doc_id}


@router.post("/timetable", response_model=TimetableOut)
async def create_timetable(body: TimetableCreate, request: Request,
                           teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> TimetableOut:
    await _assert_assigned(db, teacher, body.class_id, body.subject_id)
    tt = Timetable(teacher_id=teacher.id, class_id=body.class_id, subject_id=body.subject_id,
                   day_of_week=body.day_of_week, period_number=body.period_number, room=body.room,
                   topic=body.topic, school_id=teacher.school_id)
    db.add(tt)
    await db.flush()
    await record_audit(db, action="TIMETABLE_CREATE", actor=teacher, target_type="timetable",
                       target_id=tt.id, request=request)
    return TimetableOut.model_validate(tt)


@router.get("/timetable", response_model=list[TimetableOut])
async def list_timetable(teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[TimetableOut]:
    rows = (await db.execute(
        select(Timetable).where(Timetable.teacher_id == teacher.id)
        .order_by(Timetable.day_of_week, Timetable.period_number)
    )).scalars().all()
    return [TimetableOut.model_validate(r) for r in rows]


@router.patch("/timetable/{entry_id}", response_model=TimetableOut)
async def update_timetable_entry(entry_id: str, body: TimetableUpdate, request: Request,
                                 teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> TimetableOut:
    entry = await db.get(Timetable, entry_id)
    if entry is None or entry.teacher_id != teacher.id:
        raise NotFoundError("Timetable", entry_id)
    entry.topic = body.topic
    db.add(entry)
    await record_audit(db, action="TIMETABLE_UPDATE", actor=teacher, target_type="timetable",
                       target_id=entry_id, request=request)
    return TimetableOut.model_validate(entry)


@router.delete("/timetable/{entry_id}")
async def delete_timetable_entry(entry_id: str, request: Request,
                                 teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    entry = await db.get(Timetable, entry_id)
    if entry is None or entry.teacher_id != teacher.id:
        raise NotFoundError("Timetable", entry_id)
    await db.delete(entry)
    await record_audit(db, action="TIMETABLE_DELETE", actor=teacher, target_type="timetable",
                       target_id=entry_id, request=request)
    return {"status": "deleted", "id": entry_id}


@router.post("/exam-timetable", response_model=ExamTimetableOut)
async def create_exam_timetable(body: ExamTimetableCreate, request: Request,
                                teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> ExamTimetableOut:
    await _assert_assigned(db, teacher, body.class_id, body.subject_id)
    ex = ExamTimetable(class_id=body.class_id, subject_id=body.subject_id, exam_name=body.exam_name,
                       exam_date=body.exam_date, start_time=body.start_time,
                       duration_minutes=body.duration_minutes, syllabus_ref=body.syllabus_ref,
                       school_id=teacher.school_id)
    db.add(ex)
    await db.flush()
    await record_audit(db, action="EXAM_TIMETABLE_CREATE", actor=teacher, target_type="exam_timetable",
                       target_id=ex.id, request=request)
    return ExamTimetableOut.model_validate(ex)


@router.get("/assignments")
async def list_assignments(teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[dict]:
    """This teacher's (class, subject) assignments with names, for the
    Materials/Timetable pickers — avoids the frontend needing raw class/subject
    UUIDs to build a working upload/timetable form."""
    rows = (await db.execute(
        select(TeacherAssignment).where(
            TeacherAssignment.teacher_id == teacher.id, TeacherAssignment.end_date.is_(None)
        )
    )).scalars().all()
    class_ids = {r.class_id for r in rows}
    subject_ids = {r.subject_id for r in rows}
    classes = {c.id: c.name for c in (await db.execute(
        select(ClassSection).where(ClassSection.id.in_(class_ids))
    )).scalars().all()} if class_ids else {}
    subjects = {s.id: s.name for s in (await db.execute(
        select(Subject).where(Subject.id.in_(subject_ids))
    )).scalars().all()} if subject_ids else {}
    return [
        {
            "class_id": r.class_id, "class_name": classes.get(r.class_id, r.class_id),
            "subject_id": r.subject_id, "subject_name": subjects.get(r.subject_id, r.subject_id),
        }
        for r in rows
    ]


@router.get("/dashboard")
async def teacher_dashboard(teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    assignments = (await db.execute(
        select(TeacherAssignment).where(
            TeacherAssignment.teacher_id == teacher.id, TeacherAssignment.end_date.is_(None)
        )
    )).scalars().all()
    materials = (await db.execute(
        select(Document).where(Document.uploaded_by_teacher_id == teacher.id)
    )).scalars().all()
    return {
        "classes": sorted({a.class_id for a in assignments}),
        "subjects": sorted({a.subject_id for a in assignments}),
        "materials_uploaded": len(materials),
    }


@router.get("/classes/{class_id}/progress")
async def class_progress(class_id: str, teacher: User = Depends(_guard),
                         db: AsyncSession = Depends(get_db)) -> list[dict]:
    """Per-student mastery for a class the teacher is assigned to."""
    await _assert_assigned(db, teacher, class_id, None)

    student_ids = [
        r.student_id for r in
        (await db.execute(
            select(Enrollment).where(Enrollment.class_id == class_id, Enrollment.end_date.is_(None))
        )).scalars().all()
    ]
    if not student_ids:
        return []

    students = (await db.execute(select(User).where(User.id.in_(student_ids)))).scalars().all()
    records = (await db.execute(
        select(ProgressRecord).where(ProgressRecord.student_id.in_(student_ids))
    )).scalars().all()

    by_student: dict[str, list[ProgressRecord]] = {}
    for rec in records:
        by_student.setdefault(rec.student_id, []).append(rec)

    out: list[dict] = []
    for st in students:
        recs = by_student.get(st.id, [])
        avg = round(sum(r.mastery_score for r in recs) / len(recs), 1) if recs else 0.0
        out.append({
            "student_id": st.id,
            "name": st.name,
            "grade": st.grade,
            "avg_mastery": avg,
            "topics": [{"topic": r.topic, "score": r.mastery_score} for r in recs],
        })
    out.sort(key=lambda s: s["avg_mastery"])  # weakest students first
    return out


@router.get("/flagged-answers", response_model=Page[FlaggedAnswerOut])
async def list_flagged_answers(page: PageParams = Depends(page_params), teacher: User = Depends(_guard),
                               db: AsyncSession = Depends(get_db)) -> Page[FlaggedAnswerOut]:
    """Open teacher review queue for this school (Evaluator-flagged short answers)."""
    total = (await db.execute(
        select(func.count()).select_from(FlaggedAnswer).where(FlaggedAnswer.status == FlagStatus.open)
    )).scalar_one()
    rows = (await db.execute(
        select(FlaggedAnswer)
        .where(FlaggedAnswer.status == FlagStatus.open)
        .order_by(FlaggedAnswer.created_at.desc())
        .limit(page.limit).offset(page.offset)
    )).scalars().all()
    return Page(items=[FlaggedAnswerOut.model_validate(r) for r in rows], total=total,
               limit=page.limit, offset=page.offset)


@router.post("/flagged-answers/{answer_id}/override")
async def override_flagged_answer(answer_id: str, body: FlaggedAnswerOverride, request: Request,
                                  teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    """Teacher sets the authoritative grade for a flagged answer and resolves it."""
    flagged = await db.get(FlaggedAnswer, answer_id)
    if flagged is None or flagged.school_id != teacher.school_id:
        raise NotFoundError("FlaggedAnswer", answer_id)

    flagged.override_score = body.score
    flagged.override_feedback = body.feedback
    flagged.status = FlagStatus.resolved
    flagged.resolved_by_teacher_id = teacher.id
    db.add(flagged)
    await notify(db, user_id=flagged.student_id, school_id=teacher.school_id, type="answer_reviewed",
                title="Your answer was reviewed", body="A teacher reviewed one of your flagged answers.",
                link="/student/history")
    await record_audit(db, action="ANSWER_GRADE_OVERRIDE", actor=teacher, target_type="flagged_answer",
                       target_id=answer_id, payload={"score": body.score}, request=request)
    return {"status": "resolved", "id": answer_id, "score": body.score}


@router.post("/quizzes/{quiz_id}/approve")
async def approve_quiz(quiz_id: str, body: QuizApproval, request: Request,
                       teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    """Approve (or keep draft) a quiz so it appears in the student's curated list."""
    quiz = await db.get(Quiz, quiz_id)
    if quiz is None or quiz.school_id != teacher.school_id:
        raise NotFoundError("Quiz", quiz_id)
    await _assert_assigned(db, teacher, quiz.class_id, quiz.subject_id)

    if body.approved:
        quiz.status = QuizStatus.approved
        quiz.created_by_teacher_id = teacher.id
        db.add(quiz)
        student_ids = (await db.execute(
            select(Enrollment.student_id).where(
                Enrollment.class_id == quiz.class_id, Enrollment.end_date.is_(None)
            )
        )).scalars().all()
        for student_id in student_ids:
            await notify(db, user_id=student_id, school_id=teacher.school_id, type="quiz_approved",
                        title="New quiz available", body=f"A new quiz on {quiz.topic} is ready.",
                        link="/student/quiz")
        await record_audit(db, action="QUIZ_APPROVE", actor=teacher, target_type="quiz",
                           target_id=quiz_id, request=request)
    return {"status": quiz.status.value, "id": quiz_id}


@router.post("/students", response_model=UserCreatedResponse)
async def create_student(body: StudentCreate, request: Request,
                         teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> UserCreatedResponse:
    """Teacher-initiated student creation — 403 unless the school has granted
    this teacher's role `user:create_student` (off by default)."""
    if not await can_create_role(db, teacher, UserRole.student):
        raise ForbiddenError("Not permitted to create students")
    if (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none():
        raise ValidationError("Email already in use")

    temp = body.password or secrets.token_urlsafe(10)
    student = User(name=body.name, email=body.email, password_hash=hash_password(temp),
                   role=UserRole.student, school_id=teacher.school_id, grade=body.grade,
                   interests=body.interests)
    db.add(student)
    await db.flush()
    await record_audit(db, action="USER_CREATE", actor=teacher, target_type="user",
                       target_id=student.id, payload={"role": "student"}, request=request)
    return UserCreatedResponse(user=UserOut.model_validate(student),
                               temp_password=None if body.password else temp)


@router.post("/parents", response_model=UserCreatedResponse)
async def create_parent(body: ParentCreate, request: Request,
                        teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> UserCreatedResponse:
    """Teacher-initiated parent creation + link to a student in this school —
    403 unless the school has granted this teacher's role `user:create_parent`."""
    if not await can_create_role(db, teacher, UserRole.parent):
        raise ForbiddenError("Not permitted to create parents")
    student = (await db.execute(
        select(User).where(User.id == body.student_id, User.school_id == teacher.school_id,
                          User.role == UserRole.student)
    )).scalar_one_or_none()
    if student is None:
        raise NotFoundError("Student", body.student_id)
    if (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none():
        raise ValidationError("Email already in use")

    temp = body.password or secrets.token_urlsafe(10)
    parent = User(name=body.name, email=body.email, password_hash=hash_password(temp),
                 role=UserRole.parent, school_id=teacher.school_id)
    db.add(parent)
    await db.flush()
    db.add(ParentStudentLink(parent_id=parent.id, student_id=student.id, school_id=teacher.school_id,
                             consent_given_at=datetime.now(UTC)))
    await db.flush()
    await notify(db, user_id=parent.id, school_id=teacher.school_id, type="parent_linked",
                title="Linked to a student", body=f"You've been linked to {student.name}.", link="/parent")
    await record_audit(db, action="USER_CREATE", actor=teacher, target_type="user",
                       target_id=parent.id, payload={"role": "parent"}, request=request)
    return UserCreatedResponse(user=UserOut.model_validate(parent),
                               temp_password=None if body.password else temp)
