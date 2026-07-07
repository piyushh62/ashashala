"""Super-admin routes: schools, first school-admin, platform dashboard, deletion."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password
from app.core.exceptions import NotFoundError, ValidationError
from app.db.session import get_db
from app.db.tenant_filter import tenant_bypass
from app.deps import require_role
from app.models.document import Document
from app.models.learning import ProgressRecord
from app.models.llm_usage import LlmUsage
from app.models.school import School
from app.models.structure import ClassSection
from app.models.user import User, UserRole
from app.schemas.admin import (
    PlatformDashboard,
    SchoolAdminCreate,
    SchoolCreate,
    SchoolDashboardOut,
    SchoolOut,
    SchoolUpdate,
    TempPasswordResponse,
)
from app.services.audit_service import record_audit
from app.services.r2_client import get_storage_client
from app.services.rag.store import get_qdrant_store

router = APIRouter(prefix="/api/v1/admin", tags=["Super Admin"])
_guard = require_role(UserRole.super_admin)


@router.post("/schools", response_model=SchoolOut)
async def create_school(body: SchoolCreate, request: Request,
                        admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> SchoolOut:
    school = School(name=body.name, address=body.address, timezone=body.timezone)
    if body.features_json:
        school.features_json = body.features_json
    db.add(school)
    await db.flush()
    await record_audit(db, action="SCHOOL_CREATE", actor=admin, target_type="school",
                       target_id=school.id, request=request)
    return SchoolOut.model_validate(school)


@router.patch("/schools/{school_id}", response_model=SchoolOut)
async def update_school(school_id: str, body: SchoolUpdate, request: Request,
                        admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> SchoolOut:
    school = await db.get(School, school_id)
    if school is None:
        raise NotFoundError("School", school_id)
    if body.name is not None:
        school.name = body.name
    if body.address is not None:
        school.address = body.address
    if body.features_json is not None:
        school.features_json = body.features_json
    action = "SCHOOL_SUSPEND" if body.is_active is False else "SCHOOL_UPDATE"
    if body.is_active is not None:
        school.is_active = body.is_active
    db.add(school)
    await record_audit(db, action=action, actor=admin, target_type="school",
                       target_id=school.id, request=request)
    return SchoolOut.model_validate(school)


@router.delete("/schools/{school_id}")
async def delete_school(school_id: str, request: Request,
                        admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    school = await db.get(School, school_id)
    if school is None:
        raise NotFoundError("School", school_id)
    await db.delete(school)
    await record_audit(db, action="SCHOOL_DELETE", actor=admin, target_type="school",
                       target_id=school_id, request=request)
    return {"status": "deleted", "id": school_id}


@router.post("/schools/{school_id}/admins", response_model=TempPasswordResponse)
async def create_school_admin(school_id: str, body: SchoolAdminCreate, request: Request,
                              admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> TempPasswordResponse:
    school = await db.get(School, school_id)
    if school is None:
        raise NotFoundError("School", school_id)
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing is not None:
        raise ValidationError("Email already in use")

    temp_password = secrets.token_urlsafe(12)
    user = User(name=body.name, email=body.email, password_hash=hash_password(temp_password),
                role=UserRole.school_admin, school_id=school_id)
    db.add(user)
    await db.flush()
    await record_audit(db, action="USER_CREATE", actor=admin, school_id=school_id,
                       target_type="user", target_id=user.id, request=request)
    return TempPasswordResponse(user_id=user.id, email=body.email, temp_password=temp_password)


@router.get("/dashboard", response_model=PlatformDashboard)
async def dashboard(days: int = Query(default=14, ge=1, le=90),
                    admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> PlatformDashboard:
    active_schools = (await db.execute(
        select(func.count()).select_from(School).where(School.is_active.is_(True))
    )).scalar_one()
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()

    since = datetime.now(timezone.utc) - timedelta(days=1)
    rows = (await db.execute(
        select(LlmUsage.school_id, func.coalesce(func.sum(LlmUsage.prompt_tokens + LlmUsage.completion_tokens), 0))
        .where(LlmUsage.ts >= since).group_by(LlmUsage.school_id)
    )).all()
    tokens_today = {(sid or "platform"): int(tok) for sid, tok in rows}

    total = (await db.execute(select(func.count()).select_from(LlmUsage).where(LlmUsage.ts >= since))).scalar_one()
    errors = (await db.execute(
        select(func.count()).select_from(LlmUsage).where(LlmUsage.ts >= since, LlmUsage.status == "error")
    )).scalar_one()
    error_rate = (errors / total) if total else 0.0

    # Platform-wide token trend for the dashboard chart.
    since_trend = datetime.now(timezone.utc) - timedelta(days=days)
    day = func.date(LlmUsage.ts)
    trend_rows = (await db.execute(
        select(day, func.coalesce(func.sum(LlmUsage.prompt_tokens + LlmUsage.completion_tokens), 0), func.count())
        .where(LlmUsage.ts >= since_trend)
        .group_by(day)
        .order_by(day)
    )).all()
    tokens_by_day = [{"day": str(d), "tokens": int(tok), "calls": int(calls)} for d, tok, calls in trend_rows]

    return PlatformDashboard(active_schools=active_schools, total_users=total_users,
                             tokens_today_by_school=tokens_today, error_rate=error_rate,
                             tokens_by_day=tokens_by_day)


@router.get("/schools", response_model=list[SchoolOut])
async def list_schools(admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[SchoolOut]:
    schools = (await db.execute(select(School))).scalars().all()
    return [SchoolOut.model_validate(s) for s in schools]


@router.get("/schools/{school_id}", response_model=SchoolOut)
async def get_school(school_id: str, admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> SchoolOut:
    school = await db.get(School, school_id)
    if school is None:
        raise NotFoundError("School", school_id)
    return SchoolOut.model_validate(school)


@router.get("/schools/{school_id}/dashboard", response_model=SchoolDashboardOut)
async def school_drill_down(school_id: str, admin: User = Depends(_guard),
                            db: AsyncSession = Depends(get_db)) -> SchoolDashboardOut:
    """Per-school snapshot for the platform dashboard's drill-down view."""
    school = await db.get(School, school_id)
    if school is None:
        raise NotFoundError("School", school_id)

    n_teachers = (await db.execute(
        select(func.count()).select_from(User).where(User.school_id == school_id, User.role == UserRole.teacher)
    )).scalar_one()
    n_students = (await db.execute(
        select(func.count()).select_from(User).where(User.school_id == school_id, User.role == UserRole.student)
    )).scalar_one()
    with tenant_bypass():
        n_classes = (await db.execute(
            select(func.count()).select_from(ClassSection).where(ClassSection.school_id == school_id)
        )).scalar_one()
        avg_mastery = (await db.execute(
            select(func.coalesce(func.avg(ProgressRecord.mastery_score), 0))
            .where(ProgressRecord.school_id == school_id)
        )).scalar_one()

    return SchoolDashboardOut(school_id=school_id, teachers=n_teachers, students=n_students,
                              classes=n_classes, avg_mastery=round(float(avg_mastery), 1))


@router.delete("/users/{user_id}/data")
async def delete_user_data(user_id: str, request: Request, reason: str = Body(embed=True, default="compliance"),
                           admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    """Compliance deletion: remove the user's documents (rows + Qdrant + R2) and the user."""
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User", user_id)

    with tenant_bypass():
        docs = (await db.execute(select(Document).where(Document.uploaded_by_teacher_id == user_id))).scalars().all()
        for doc in docs:
            try:
                await get_qdrant_store().delete_by_doc(doc.school_id, doc.id)
            except Exception:  # noqa: BLE001
                pass
            if doc.storage_url:
                try:
                    key = doc.storage_url.split("/", 3)[-1]
                    await get_storage_client().delete_object(key)
                except Exception:  # noqa: BLE001
                    pass
            await db.delete(doc)
        await db.delete(user)

    await record_audit(db, action="SUPER_ADMIN_DATA_ACCESS", actor=admin, school_id=user.school_id,
                       target_type="user", target_id=user_id, payload={"reason": reason, "op": "delete"},
                       request=request)
    return {"status": "deleted", "user_id": user_id, "documents_removed": len(docs)}
