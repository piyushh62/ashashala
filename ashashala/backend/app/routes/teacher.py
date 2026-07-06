"""Teacher routes: materials (file/url/youtube), timetables, dashboard."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.db.session import get_db
from app.deps import require_role
from app.models.document import Document, DocStatus, SourceType
from app.models.flagged_answer import FlaggedAnswer, FlagStatus
from app.models.learning import ProgressRecord, Quiz, QuizStatus
from app.models.school import School
from app.models.structure import Enrollment, TeacherAssignment
from app.models.timetable import ExamTimetable, Timetable
from app.models.user import User, UserRole
from app.schemas.teacher import (
    DocumentOut,
    ExamTimetableCreate,
    ExamTimetableOut,
    FlaggedAnswerOut,
    FlaggedAnswerOverride,
    MaterialUrlCreate,
    MaterialYoutubeCreate,
    QuizApproval,
    TimetableCreate,
    TimetableOut,
)
from app.services.audit_service import record_audit
from app.services.ingestion.pipeline import ingest_document
from app.services.r2_client import get_r2_client

router = APIRouter(prefix="/api/v1/teacher", tags=["Teacher"])
_guard = require_role(UserRole.teacher)

_EXT_TO_TYPE = {"pdf": SourceType.pdf, "docx": SourceType.docx, "txt": SourceType.txt,
                "jpg": SourceType.image, "jpeg": SourceType.image, "png": SourceType.image}


async def _assert_assigned(db: AsyncSession, teacher: User, class_id: str, subject_id: str | None) -> None:
    stmt = select(TeacherAssignment).where(
        TeacherAssignment.teacher_id == teacher.id, TeacherAssignment.class_id == class_id
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
) -> Document:
    doc = Document(school_id=teacher.school_id, class_id=class_id, subject_id=subject_id,
                   uploaded_by_teacher_id=teacher.id, filename=filename, storage_url=storage_url,
                   source_type=source_type, source_ref=source_ref, status=DocStatus.pending)
    db.add(doc)
    await db.flush()
    await record_audit(db, action="MATERIAL_UPLOAD", actor=teacher, target_type="document",
                       target_id=doc.id, payload={"type": source_type.value}, request=request)
    tasks.add_task(ingest_document, doc_id=doc.id, school_id=teacher.school_id, class_id=class_id,
                   subject_id=subject_id, source_type=source_type, data=data, source_ref=source_ref)
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
    storage_url = await get_r2_client().upload_bytes(key, data, file.content_type or "application/octet-stream")
    doc = await _create_and_schedule(db, tasks, teacher, request, class_id=class_id, subject_id=subject_id,
                                     filename=file.filename or key, source_type=source_type,
                                     source_ref=file.filename, storage_url=storage_url, data=data)
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


@router.get("/materials", response_model=list[DocumentOut])
async def list_materials(teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[DocumentOut]:
    docs = (await db.execute(
        select(Document).where(Document.uploaded_by_teacher_id == teacher.id)
    )).scalars().all()
    return [DocumentOut.model_validate(d) for d in docs]


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
                   school_id=teacher.school_id)
    db.add(tt)
    await db.flush()
    await record_audit(db, action="TIMETABLE_CREATE", actor=teacher, target_type="timetable",
                       target_id=tt.id, request=request)
    return TimetableOut.model_validate(tt)


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


@router.get("/dashboard")
async def teacher_dashboard(teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    assignments = (await db.execute(
        select(TeacherAssignment).where(TeacherAssignment.teacher_id == teacher.id)
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
        (await db.execute(select(Enrollment).where(Enrollment.class_id == class_id))).scalars().all()
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


@router.get("/flagged-answers", response_model=list[FlaggedAnswerOut])
async def list_flagged_answers(teacher: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[FlaggedAnswerOut]:
    """Open teacher review queue for this school (Evaluator-flagged short answers)."""
    rows = (await db.execute(
        select(FlaggedAnswer)
        .where(FlaggedAnswer.status == FlagStatus.open)
        .order_by(FlaggedAnswer.created_at.desc())
    )).scalars().all()
    return [FlaggedAnswerOut.model_validate(r) for r in rows]


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
        await record_audit(db, action="QUIZ_APPROVE", actor=teacher, target_type="quiz",
                           target_id=quiz_id, request=request)
    return {"status": quiz.status.value, "id": quiz_id}
