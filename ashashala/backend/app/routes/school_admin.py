"""School-admin routes: users, classes/subjects, assignments, enrollments, links."""

from __future__ import annotations

import csv
import io
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password
from app.core.exceptions import NotFoundError, ValidationError
from app.db.session import get_db
from app.deps import PageParams, page_params, require_role
from app.models.audit import AuditLog
from app.models.learning import ProgressRecord
from app.models.llm_usage import LlmUsage
from app.models.structure import (
    ClassSection,
    Enrollment,
    ParentStudentLink,
    Subject,
    TeacherAssignment,
)
from app.models.user import User, UserRole
from app.schemas.school_admin import (
    AtRiskStudentOut,
    ClassCreate,
    ClassMasteryOut,
    ClassOut,
    EnrollmentCreate,
    EnrollmentOut,
    IdResponse,
    ParentLinkCreate,
    ParentLinkOut,
    SubjectCreate,
    SubjectOut,
    TeacherAssignmentCreate,
    TeacherAssignmentOut,
    TempPasswordResponse,
    UserCreate,
    UserCreatedResponse,
    UserOut,
    UserUpdate,
)
from app.schemas.pagination import Page
from app.services.audit_service import record_audit
from app.services.notification_service import notify

router = APIRouter(prefix="/api/v1/school", tags=["School Admin"])
_guard = require_role(UserRole.school_admin)

# Roles a school admin is allowed to create.
_CREATABLE = {UserRole.teacher, UserRole.student, UserRole.parent}


async def _get_school_user_or_404(db: AsyncSession, school_id: str, user_id: str) -> User:
    """Load a user and confirm they belong to this admin's school (else 404)."""
    user = await db.get(User, user_id)
    if user is None or user.school_id != school_id:
        raise NotFoundError("User", user_id)
    return user


async def _require_user_in_school(db: AsyncSession, school_id: str, user_id: str, role: UserRole) -> User:
    """Resolve a user by id, requiring they belong to this school AND hold the
    expected role — prevents wiring a raw id from another tenant (or the
    wrong role) into a teacher-assignment/enrollment/parent-link row."""
    user = (await db.execute(
        select(User).where(User.id == user_id, User.school_id == school_id, User.role == role)
    )).scalar_one_or_none()
    if user is None:
        raise NotFoundError(role.value.capitalize(), user_id)
    return user


async def _require_class_in_school(db: AsyncSession, school_id: str, class_id: str) -> ClassSection:
    cls = (await db.execute(
        select(ClassSection).where(ClassSection.id == class_id, ClassSection.school_id == school_id)
    )).scalar_one_or_none()
    if cls is None:
        raise NotFoundError("Class", class_id)
    return cls


async def _require_subject_in_school(db: AsyncSession, school_id: str, subject_id: str) -> Subject:
    subj = (await db.execute(
        select(Subject).where(Subject.id == subject_id, Subject.school_id == school_id)
    )).scalar_one_or_none()
    if subj is None:
        raise NotFoundError("Subject", subject_id)
    return subj


@router.post("/users", response_model=UserCreatedResponse)
async def create_user(body: UserCreate, request: Request,
                      admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> UserCreatedResponse:
    if body.role not in _CREATABLE:
        raise ValidationError("School admin can only create teacher/student/parent")
    if (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none():
        raise ValidationError("Email already in use")

    temp = body.password or secrets.token_urlsafe(10)
    user = User(name=body.name, email=body.email, password_hash=hash_password(temp),
                role=body.role, school_id=admin.school_id, grade=body.grade, interests=body.interests)
    db.add(user)
    await db.flush()
    await record_audit(db, action="USER_CREATE", actor=admin, target_type="user",
                       target_id=user.id, payload={"role": body.role.value}, request=request)
    return UserCreatedResponse(user=UserOut.model_validate(user),
                               temp_password=None if body.password else temp)


@router.post("/users/bulk")
async def bulk_import_students(request: Request, file: UploadFile,
                               admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    """CSV columns: name,email,grade — auto-generates a password per row."""
    raw = (await file.read()).decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    created: list[dict] = []
    for row in reader:
        email = (row.get("email") or "").strip()
        name = (row.get("name") or "").strip()
        if not email or not name:
            continue
        if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
            continue
        temp = secrets.token_urlsafe(10)
        grade = int(row["grade"]) if row.get("grade", "").strip().isdigit() else None
        user = User(name=name, email=email, password_hash=hash_password(temp),
                    role=UserRole.student, school_id=admin.school_id, grade=grade)
        db.add(user)
        await db.flush()
        created.append({"id": user.id, "email": email, "temp_password": temp})
    await record_audit(db, action="USER_CREATE", actor=admin, target_type="user_bulk",
                       target_id=None, payload={"count": len(created)}, request=request)
    return {"created": created, "count": len(created)}


@router.get("/users", response_model=Page[UserOut])
async def list_users(role: UserRole | None = Query(default=None), page: PageParams = Depends(page_params),
                     admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> Page[UserOut]:
    stmt = select(User).where(User.school_id == admin.school_id)
    count_stmt = select(func.count()).select_from(User).where(User.school_id == admin.school_id)
    if role is not None:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)
    total = (await db.execute(count_stmt)).scalar_one()
    users = (await db.execute(
        stmt.order_by(User.created_at).limit(page.limit).offset(page.offset)
    )).scalars().all()
    return Page(items=[UserOut.model_validate(u) for u in users], total=total,
               limit=page.limit, offset=page.offset)


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: str, body: UserUpdate, request: Request,
                      admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> UserOut:
    user = await _get_school_user_or_404(db, admin.school_id, user_id)
    if body.name is not None:
        user.name = body.name
    if body.grade is not None:
        user.grade = body.grade
    if body.interests is not None:
        user.interests = body.interests
    action = "USER_DEACTIVATE" if body.is_active is False else "USER_UPDATE"
    if body.is_active is not None:
        user.is_active = body.is_active
        if body.is_active is False:
            # Kill any live sessions immediately rather than letting existing
            # access/refresh tokens ride out their TTL after deactivation.
            user.tokens_valid_after = datetime.now(UTC)
    db.add(user)
    await record_audit(db, action=action, actor=admin, target_type="user",
                       target_id=user.id, request=request)
    return UserOut.model_validate(user)


@router.get("/classes", response_model=list[ClassOut])
async def list_classes(admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[ClassOut]:
    rows = (await db.execute(select(ClassSection).order_by(ClassSection.grade_level, ClassSection.name))).scalars().all()
    return [ClassOut.model_validate(c) for c in rows]


@router.get("/subjects", response_model=list[SubjectOut])
async def list_subjects(admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[SubjectOut]:
    rows = (await db.execute(select(Subject).order_by(Subject.name))).scalars().all()
    return [SubjectOut.model_validate(s) for s in rows]


@router.post("/classes", response_model=ClassOut)
async def create_class(body: ClassCreate, request: Request,
                       admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> ClassOut:
    cls = ClassSection(name=body.name, grade_level=body.grade_level, school_id=admin.school_id)
    db.add(cls)
    await db.flush()
    await record_audit(db, action="CLASS_CREATE", actor=admin, target_type="class",
                       target_id=cls.id, request=request)
    return ClassOut.model_validate(cls)


@router.post("/subjects", response_model=SubjectOut)
async def create_subject(body: SubjectCreate, request: Request,
                         admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> SubjectOut:
    subj = Subject(name=body.name, school_id=admin.school_id)
    db.add(subj)
    await db.flush()
    await record_audit(db, action="SUBJECT_CREATE", actor=admin, target_type="subject",
                       target_id=subj.id, request=request)
    return SubjectOut.model_validate(subj)


@router.post("/teacher-assignments", response_model=IdResponse)
async def assign_teacher(body: TeacherAssignmentCreate, request: Request,
                         admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> IdResponse:
    await _require_user_in_school(db, admin.school_id, body.teacher_id, UserRole.teacher)
    cls = await _require_class_in_school(db, admin.school_id, body.class_id)
    subj = await _require_subject_in_school(db, admin.school_id, body.subject_id)
    ta = TeacherAssignment(teacher_id=body.teacher_id, class_id=body.class_id,
                           subject_id=body.subject_id, school_id=admin.school_id)
    db.add(ta)
    await db.flush()
    await notify(db, user_id=body.teacher_id, school_id=admin.school_id, type="teacher_assigned",
                title="New class assignment",
                body=f"You've been assigned to {cls.name} for {subj.name}.",
                link="/teacher/timetable")
    await record_audit(db, action="TEACHER_ASSIGN", actor=admin, target_type="teacher_assignment",
                       target_id=ta.id, request=request)
    return IdResponse(id=ta.id)


@router.get("/teacher-assignments", response_model=Page[TeacherAssignmentOut])
async def list_teacher_assignments(page: PageParams = Depends(page_params), admin: User = Depends(_guard),
                                   db: AsyncSession = Depends(get_db)) -> Page[TeacherAssignmentOut]:
    total = (await db.execute(select(func.count()).select_from(TeacherAssignment))).scalar_one()
    rows = (await db.execute(
        select(TeacherAssignment).order_by(TeacherAssignment.created_at)
        .limit(page.limit).offset(page.offset)
    )).scalars().all()
    if not rows:
        return Page(items=[], total=total, limit=page.limit, offset=page.offset)
    teachers = {u.id: u.name for u in (await db.execute(
        select(User).where(User.id.in_({r.teacher_id for r in rows}))
    )).scalars().all()}
    classes = {c.id: c.name for c in (await db.execute(
        select(ClassSection).where(ClassSection.id.in_({r.class_id for r in rows}))
    )).scalars().all()}
    subjects = {s.id: s.name for s in (await db.execute(
        select(Subject).where(Subject.id.in_({r.subject_id for r in rows}))
    )).scalars().all()}
    items = [
        TeacherAssignmentOut(
            id=r.id, teacher_id=r.teacher_id, teacher_name=teachers.get(r.teacher_id, "Unknown"),
            class_id=r.class_id, class_name=classes.get(r.class_id, "Unknown"),
            subject_id=r.subject_id, subject_name=subjects.get(r.subject_id, "Unknown"),
        )
        for r in rows
    ]
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.delete("/teacher-assignments/{assignment_id}")
async def unassign_teacher(assignment_id: str, request: Request,
                           admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    row = (await db.execute(
        select(TeacherAssignment).where(TeacherAssignment.id == assignment_id)
    )).scalar_one_or_none()
    if row is None:
        raise NotFoundError("TeacherAssignment", assignment_id)
    await db.delete(row)
    await record_audit(db, action="TEACHER_UNASSIGN", actor=admin, target_type="teacher_assignment",
                       target_id=assignment_id, request=request)
    return {"status": "deleted", "id": assignment_id}


@router.post("/enrollments", response_model=IdResponse)
async def enroll_student(body: EnrollmentCreate, request: Request,
                         admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> IdResponse:
    await _require_user_in_school(db, admin.school_id, body.student_id, UserRole.student)
    cls = await _require_class_in_school(db, admin.school_id, body.class_id)
    en = Enrollment(student_id=body.student_id, class_id=body.class_id, school_id=admin.school_id)
    db.add(en)
    await db.flush()
    await notify(db, user_id=body.student_id, school_id=admin.school_id, type="student_enrolled",
                title="Enrolled in a new class", body=f"You've been enrolled in {cls.name}.",
                link="/student")
    await record_audit(db, action="STUDENT_ENROLL", actor=admin, target_type="enrollment",
                       target_id=en.id, request=request)
    return IdResponse(id=en.id)


@router.get("/enrollments", response_model=Page[EnrollmentOut])
async def list_enrollments(page: PageParams = Depends(page_params), admin: User = Depends(_guard),
                           db: AsyncSession = Depends(get_db)) -> Page[EnrollmentOut]:
    total = (await db.execute(select(func.count()).select_from(Enrollment))).scalar_one()
    rows = (await db.execute(
        select(Enrollment).order_by(Enrollment.created_at).limit(page.limit).offset(page.offset)
    )).scalars().all()
    if not rows:
        return Page(items=[], total=total, limit=page.limit, offset=page.offset)
    students = {u.id: u.name for u in (await db.execute(
        select(User).where(User.id.in_({r.student_id for r in rows}))
    )).scalars().all()}
    classes = {c.id: c.name for c in (await db.execute(
        select(ClassSection).where(ClassSection.id.in_({r.class_id for r in rows}))
    )).scalars().all()}
    items = [
        EnrollmentOut(
            id=r.id, student_id=r.student_id, student_name=students.get(r.student_id, "Unknown"),
            class_id=r.class_id, class_name=classes.get(r.class_id, "Unknown"),
        )
        for r in rows
    ]
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.delete("/enrollments/{enrollment_id}")
async def unenroll_student(enrollment_id: str, request: Request,
                           admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    row = (await db.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id)
    )).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Enrollment", enrollment_id)
    await db.delete(row)
    await record_audit(db, action="STUDENT_UNENROLL", actor=admin, target_type="enrollment",
                       target_id=enrollment_id, request=request)
    return {"status": "deleted", "id": enrollment_id}


@router.post("/parent-links", response_model=IdResponse)
async def link_parent(body: ParentLinkCreate, request: Request,
                      admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> IdResponse:
    await _require_user_in_school(db, admin.school_id, body.parent_id, UserRole.parent)
    student = await _require_user_in_school(db, admin.school_id, body.student_id, UserRole.student)
    link = ParentStudentLink(parent_id=body.parent_id, student_id=body.student_id,
                             school_id=admin.school_id, consent_given_at=datetime.now(UTC))
    db.add(link)
    await db.flush()
    await notify(db, user_id=body.parent_id, school_id=admin.school_id, type="parent_linked",
                title="Linked to a student", body=f"You've been linked to {student.name}.",
                link="/parent")
    await record_audit(db, action="PARENT_LINK", actor=admin, target_type="parent_student_link",
                       target_id=link.id, request=request)
    return IdResponse(id=link.id)


@router.get("/parent-links", response_model=Page[ParentLinkOut])
async def list_parent_links(page: PageParams = Depends(page_params), admin: User = Depends(_guard),
                            db: AsyncSession = Depends(get_db)) -> Page[ParentLinkOut]:
    total = (await db.execute(select(func.count()).select_from(ParentStudentLink))).scalar_one()
    rows = (await db.execute(
        select(ParentStudentLink).order_by(ParentStudentLink.created_at)
        .limit(page.limit).offset(page.offset)
    )).scalars().all()
    if not rows:
        return Page(items=[], total=total, limit=page.limit, offset=page.offset)
    users = {u.id: u.name for u in (await db.execute(
        select(User).where(User.id.in_({r.parent_id for r in rows} | {r.student_id for r in rows}))
    )).scalars().all()}
    items = [
        ParentLinkOut(
            id=r.id, parent_id=r.parent_id, parent_name=users.get(r.parent_id, "Unknown"),
            student_id=r.student_id, student_name=users.get(r.student_id, "Unknown"),
        )
        for r in rows
    ]
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.delete("/parent-links/{link_id}")
async def unlink_parent(link_id: str, request: Request,
                        admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    row = (await db.execute(
        select(ParentStudentLink).where(ParentStudentLink.id == link_id)
    )).scalar_one_or_none()
    if row is None:
        raise NotFoundError("ParentStudentLink", link_id)
    await db.delete(row)
    await record_audit(db, action="PARENT_UNLINK", actor=admin, target_type="parent_student_link",
                       target_id=link_id, request=request)
    return {"status": "deleted", "id": link_id}


@router.post("/users/{user_id}/reset-password", response_model=TempPasswordResponse)
async def reset_user_password(user_id: str, request: Request,
                              admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> TempPasswordResponse:
    user = await _get_school_user_or_404(db, admin.school_id, user_id)
    temp = secrets.token_urlsafe(10)
    user.password_hash = hash_password(temp)
    user.tokens_valid_after = datetime.now(UTC)
    db.add(user)
    await notify(db, user_id=user.id, school_id=admin.school_id, type="password_reset",
                title="Your password was reset", body="An admin reset your password.",
                link="/settings")
    await record_audit(db, action="PASSWORD_RESET_BY_ADMIN", actor=admin, target_type="user",
                       target_id=user.id, request=request)
    return TempPasswordResponse(temp_password=temp)


@router.get("/dashboard")
async def school_dashboard(admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    n_teachers = (await db.execute(
        select(func.count()).select_from(User).where(User.school_id == admin.school_id, User.role == UserRole.teacher)
    )).scalar_one()
    n_students = (await db.execute(
        select(func.count()).select_from(User).where(User.school_id == admin.school_id, User.role == UserRole.student)
    )).scalar_one()
    n_classes = (await db.execute(select(func.count()).select_from(ClassSection))).scalar_one()
    avg_mastery = (await db.execute(select(func.coalesce(func.avg(ProgressRecord.mastery_score), 0)))).scalar_one()
    return {
        "teachers": n_teachers, "students": n_students, "classes": n_classes,
        "avg_mastery": round(float(avg_mastery), 1),
    }


@router.get("/dashboard/at-risk", response_model=list[AtRiskStudentOut])
async def at_risk_students(limit: int = Query(default=10, ge=1, le=50),
                           admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[AtRiskStudentOut]:
    """Students with the lowest average mastery across all tracked topics."""
    rows = (await db.execute(
        select(ProgressRecord.student_id, func.avg(ProgressRecord.mastery_score))
        .group_by(ProgressRecord.student_id)
        .order_by(func.avg(ProgressRecord.mastery_score))
        .limit(limit)
    )).all()
    if not rows:
        return []
    names = {u.id: u.name for u in (await db.execute(
        select(User).where(User.id.in_({sid for sid, _ in rows}))
    )).scalars().all()}
    return [
        AtRiskStudentOut(student_id=sid, student_name=names.get(sid, "Unknown"), avg_mastery=round(float(avg), 1))
        for sid, avg in rows
    ]


@router.get("/dashboard/mastery-by-class", response_model=list[ClassMasteryOut])
async def mastery_by_class(admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[ClassMasteryOut]:
    """Average mastery per class, joining enrollments to progress records."""
    rows = (await db.execute(
        select(
            Enrollment.class_id,
            func.avg(ProgressRecord.mastery_score),
            func.count(func.distinct(Enrollment.student_id)),
        )
        .join(ProgressRecord, ProgressRecord.student_id == Enrollment.student_id)
        .group_by(Enrollment.class_id)
    )).all()
    if not rows:
        return []
    classes = {c.id: c.name for c in (await db.execute(
        select(ClassSection).where(ClassSection.id.in_({cid for cid, _, _ in rows}))
    )).scalars().all()}
    return [
        ClassMasteryOut(class_id=cid, class_name=classes.get(cid, "Unknown"),
                        avg_mastery=round(float(avg), 1), student_count=int(cnt))
        for cid, avg, cnt in rows
    ]


@router.get("/audit")
async def audit_viewer(action: str | None = Query(default=None), page: PageParams = Depends(page_params),
                       admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    stmt = select(AuditLog).where(AuditLog.school_id == admin.school_id)
    count_stmt = select(func.count()).select_from(AuditLog).where(AuditLog.school_id == admin.school_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(
        stmt.order_by(AuditLog.ts.desc()).limit(page.limit).offset(page.offset)
    )).scalars().all()
    items = [
        {"id": r.id, "ts": r.ts.isoformat(), "action": r.action, "actor_user_id": r.actor_user_id,
         "actor_role": r.actor_role, "target_type": r.target_type, "target_id": r.target_id, "status": r.status}
        for r in rows
    ]
    return {"items": items, "total": total, "limit": page.limit, "offset": page.offset}


# Free-tier soft ceiling (tokens/day). Over this we surface a warning so a
# school admin can throttle before the provider hard-caps them.
DAILY_TOKEN_WARN = 200_000


@router.get("/llm-usage")
async def llm_usage(days: int = Query(default=7, ge=1, le=30),
                    admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    """LLM cost mini-dashboard: tokens per provider per day for this school,
    today's totals, and an over-quota warning."""
    since = datetime.now(UTC) - timedelta(days=days)
    tokens = func.coalesce(func.sum(LlmUsage.prompt_tokens + LlmUsage.completion_tokens), 0)

    # Per-provider, per-day breakdown.
    day = func.date(LlmUsage.ts)
    rows = (await db.execute(
        select(day, LlmUsage.provider, tokens, func.count())
        .where(LlmUsage.school_id == admin.school_id, LlmUsage.ts >= since)
        .group_by(day, LlmUsage.provider)
        .order_by(day)
    )).all()
    by_day = [
        {"day": str(d), "provider": provider, "tokens": int(tok), "calls": int(calls)}
        for d, provider, tok, calls in rows
    ]

    # Today's totals + error rate.
    start_today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today_tokens = (await db.execute(
        select(tokens).where(LlmUsage.school_id == admin.school_id, LlmUsage.ts >= start_today)
    )).scalar_one()
    today_calls = (await db.execute(
        select(func.count()).select_from(LlmUsage)
        .where(LlmUsage.school_id == admin.school_id, LlmUsage.ts >= start_today)
    )).scalar_one()
    today_errors = (await db.execute(
        select(func.count()).select_from(LlmUsage)
        .where(LlmUsage.school_id == admin.school_id, LlmUsage.ts >= start_today, LlmUsage.status == "error")
    )).scalar_one()

    return {
        "days": days,
        "by_day": by_day,
        "today_tokens": int(today_tokens),
        "today_calls": int(today_calls),
        "today_error_rate": round(today_errors / today_calls, 3) if today_calls else 0.0,
        "daily_token_limit": DAILY_TOKEN_WARN,
        "over_quota": int(today_tokens) > DAILY_TOKEN_WARN,
    }
