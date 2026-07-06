"""School-admin routes: users, classes/subjects, assignments, enrollments, links."""

from __future__ import annotations

import csv
import io
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password
from app.core.exceptions import NotFoundError, ValidationError
from app.db.session import get_db
from app.deps import require_role
from app.models.audit import AuditLog
from app.models.learning import ProgressRecord
from app.models.llm_usage import LlmUsage
from app.models.school import School
from app.models.structure import (
    ClassSection,
    Enrollment,
    ParentStudentLink,
    Subject,
    TeacherAssignment,
)
from app.models.user import User, UserRole
from app.schemas.school_admin import (
    ClassCreate,
    ClassOut,
    EnrollmentCreate,
    IdResponse,
    ParentLinkCreate,
    SubjectCreate,
    SubjectOut,
    TeacherAssignmentCreate,
    UserCreate,
    UserCreatedResponse,
    UserOut,
    UserUpdate,
)
from app.services.audit_service import record_audit

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


@router.get("/users", response_model=list[UserOut])
async def list_users(role: UserRole | None = Query(default=None),
                     admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[UserOut]:
    stmt = select(User).where(User.school_id == admin.school_id)
    if role is not None:
        stmt = stmt.where(User.role == role)
    users = (await db.execute(stmt)).scalars().all()
    return [UserOut.model_validate(u) for u in users]


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
    db.add(user)
    await record_audit(db, action=action, actor=admin, target_type="user",
                       target_id=user.id, request=request)
    return UserOut.model_validate(user)


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
    ta = TeacherAssignment(teacher_id=body.teacher_id, class_id=body.class_id,
                           subject_id=body.subject_id, school_id=admin.school_id)
    db.add(ta)
    await db.flush()
    await record_audit(db, action="TEACHER_ASSIGN", actor=admin, target_type="teacher_assignment",
                       target_id=ta.id, request=request)
    return IdResponse(id=ta.id)


@router.post("/enrollments", response_model=IdResponse)
async def enroll_student(body: EnrollmentCreate, request: Request,
                         admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> IdResponse:
    en = Enrollment(student_id=body.student_id, class_id=body.class_id, school_id=admin.school_id)
    db.add(en)
    await db.flush()
    await record_audit(db, action="STUDENT_ENROLL", actor=admin, target_type="enrollment",
                       target_id=en.id, request=request)
    return IdResponse(id=en.id)


@router.post("/parent-links", response_model=IdResponse)
async def link_parent(body: ParentLinkCreate, request: Request,
                      admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> IdResponse:
    link = ParentStudentLink(parent_id=body.parent_id, student_id=body.student_id,
                             school_id=admin.school_id, consent_given_at=datetime.now(timezone.utc))
    db.add(link)
    await db.flush()
    await record_audit(db, action="PARENT_LINK", actor=admin, target_type="parent_student_link",
                       target_id=link.id, request=request)
    return IdResponse(id=link.id)


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


@router.get("/audit")
async def audit_viewer(action: str | None = Query(default=None), limit: int = Query(default=100, le=500),
                       admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[dict]:
    stmt = select(AuditLog).where(AuditLog.school_id == admin.school_id).order_by(AuditLog.ts.desc()).limit(limit)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {"id": r.id, "ts": r.ts.isoformat(), "action": r.action, "actor_user_id": r.actor_user_id,
         "actor_role": r.actor_role, "target_type": r.target_type, "target_id": r.target_id, "status": r.status}
        for r in rows
    ]


# Free-tier soft ceiling (tokens/day). Over this we surface a warning so a
# school admin can throttle before the provider hard-caps them.
DAILY_TOKEN_WARN = 200_000


@router.get("/llm-usage")
async def llm_usage(days: int = Query(default=7, ge=1, le=30),
                    admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    """LLM cost mini-dashboard: tokens per provider per day for this school,
    today's totals, and an over-quota warning."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
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
    start_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
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
