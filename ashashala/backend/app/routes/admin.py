"""Super-admin routes: schools, first school-admin, platform dashboard, deletion."""

from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password
from app.core.exceptions import NotFoundError, ValidationError
from app.core.permissions import PLATFORM_ADMIN
from app.db.session import get_db
from app.db.tenant_filter import tenant_bypass
from app.deps import PageParams, page_params, require_permission
from app.models.audit import AuditLog
from app.models.document import Document
from app.models.learning import ProgressRecord
from app.models.llm_usage import LlmUsage
from app.models.rbac import Permission, Role, RoleTemplate, TemplatePermission
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
from app.schemas.rbac import PermissionOut, RoleTemplateCreate, RoleTemplateOut, RoleTemplateUpdate
from app.services.audit_service import record_audit
from app.services.r2_client import get_storage_client
from app.services.rag.store import get_qdrant_store
from app.services.rbac_service import ensure_catalog_seeded, ensure_school_roles, ensure_user_role_assignment

router = APIRouter(prefix="/api/v1/admin", tags=["Super Admin"])
_guard = require_permission(PLATFORM_ADMIN)


@router.post("/schools", response_model=SchoolOut)
async def create_school(body: SchoolCreate, request: Request,
                        admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> SchoolOut:
    school = School(name=body.name, address=body.address, timezone=body.timezone)
    if body.features_json:
        school.features_json = body.features_json
    db.add(school)
    await db.flush()
    await ensure_school_roles(db, school.id)
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
    await ensure_user_role_assignment(db, user)
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


@router.get("/audit")
async def audit_viewer(school_id: str | None = Query(default=None), action: str | None = Query(default=None),
                       date_from: date | None = Query(default=None), date_to: date | None = Query(default=None),
                       page: PageParams = Depends(page_params), admin: User = Depends(_guard),
                       db: AsyncSession = Depends(get_db)) -> dict:
    """Cross-tenant audit viewer (Super Admin only) — the school-level
    `/school/audit` route is scoped to one school; this one is not, since
    `AuditLog` isn't `TenantScoped` (see app/models/audit.py)."""
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)
    if school_id:
        stmt = stmt.where(AuditLog.school_id == school_id)
        count_stmt = count_stmt.where(AuditLog.school_id == school_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if date_from:
        stmt = stmt.where(AuditLog.ts >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc))
        count_stmt = count_stmt.where(
            AuditLog.ts >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
        )
    if date_to:
        stmt = stmt.where(AuditLog.ts <= datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc))
        count_stmt = count_stmt.where(
            AuditLog.ts <= datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)
        )
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(
        stmt.order_by(AuditLog.ts.desc()).limit(page.limit).offset(page.offset)
    )).scalars().all()
    items = [
        {"id": r.id, "ts": r.ts.isoformat(), "action": r.action, "actor_user_id": r.actor_user_id,
         "actor_role": r.actor_role, "school_id": r.school_id, "target_type": r.target_type,
         "target_id": r.target_id, "status": r.status}
        for r in rows
    ]
    return {"items": items, "total": total, "limit": page.limit, "offset": page.offset}


# --- Role template management (platform-wide catalog) ---------------------


async def _template_permissions(db: AsyncSession, template_ids: list[str]) -> dict[str, set[str]]:
    if not template_ids:
        return {}
    rows = (await db.execute(
        select(TemplatePermission.template_id, Permission.resource, Permission.action)
        .join(Permission, Permission.id == TemplatePermission.permission_id)
        .where(TemplatePermission.template_id.in_(template_ids))
    )).all()
    out: dict[str, set[str]] = {tid: set() for tid in template_ids}
    for tid, resource, action in rows:
        out[tid].add(f"{resource}:{action}")
    return out


async def _permissions_by_strings(db: AsyncSession, perm_strings: list[str]) -> list[Permission]:
    if not perm_strings:
        return []
    rows = (await db.execute(select(Permission))).scalars().all()
    by_str = {f"{p.resource}:{p.action}": p for p in rows}
    unknown = set(perm_strings) - by_str.keys()
    if unknown:
        raise ValidationError(f"Unknown permission(s): {', '.join(sorted(unknown))}")
    return [by_str[s] for s in perm_strings]


def _template_out(template: RoleTemplate, perm_strings: set[str]) -> RoleTemplateOut:
    return RoleTemplateOut(id=template.id, name=template.name, is_system=template.is_system,
                           description=template.description, permissions=sorted(perm_strings))


@router.get("/permissions", response_model=list[PermissionOut])
async def list_permissions(admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[PermissionOut]:
    """The full platform permission catalog."""
    await ensure_catalog_seeded(db)
    rows = (await db.execute(select(Permission).order_by(Permission.resource, Permission.action))).scalars().all()
    return [PermissionOut.model_validate(p) for p in rows]


@router.get("/role-templates", response_model=list[RoleTemplateOut])
async def list_role_templates(admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[RoleTemplateOut]:
    await ensure_catalog_seeded(db)
    templates = (await db.execute(select(RoleTemplate).order_by(RoleTemplate.name))).scalars().all()
    perms_by_template = await _template_permissions(db, [t.id for t in templates])
    return [_template_out(t, perms_by_template.get(t.id, set())) for t in templates]


@router.post("/role-templates", response_model=RoleTemplateOut)
async def create_role_template(body: RoleTemplateCreate, request: Request,
                               admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> RoleTemplateOut:
    existing = (await db.execute(select(RoleTemplate).where(RoleTemplate.name == body.name))).scalar_one_or_none()
    if existing is not None:
        raise ValidationError("Template name already in use")

    perms = await _permissions_by_strings(db, body.permissions)
    template = RoleTemplate(name=body.name, is_system=False, description=body.description)
    db.add(template)
    await db.flush()
    for perm in perms:
        db.add(TemplatePermission(template_id=template.id, permission_id=perm.id))
    await db.flush()
    await record_audit(db, action="ROLE_TEMPLATE_CREATE", actor=admin, target_type="role_template",
                       target_id=template.id, payload={"name": body.name}, request=request)
    return _template_out(template, {f"{p.resource}:{p.action}" for p in perms})


@router.patch("/role-templates/{template_id}", response_model=RoleTemplateOut)
async def update_role_template(template_id: str, body: RoleTemplateUpdate, request: Request,
                               admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> RoleTemplateOut:
    template = await db.get(RoleTemplate, template_id)
    if template is None:
        raise NotFoundError("RoleTemplate", template_id)
    if template.is_system:
        raise ValidationError("Cannot modify a system role template")

    if body.description is not None:
        template.description = body.description
        db.add(template)
    if body.permissions is not None:
        perms = await _permissions_by_strings(db, body.permissions)
        existing = (await db.execute(
            select(TemplatePermission).where(TemplatePermission.template_id == template.id)
        )).scalars().all()
        for row in existing:
            await db.delete(row)
        await db.flush()
        for perm in perms:
            db.add(TemplatePermission(template_id=template.id, permission_id=perm.id))
    await db.flush()
    await record_audit(db, action="ROLE_TEMPLATE_UPDATE", actor=admin, target_type="role_template",
                       target_id=template.id, request=request)
    perms_by_template = await _template_permissions(db, [template.id])
    return _template_out(template, perms_by_template.get(template.id, set()))


@router.delete("/role-templates/{template_id}")
async def delete_role_template(template_id: str, request: Request,
                               admin: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    template = await db.get(RoleTemplate, template_id)
    if template is None:
        raise NotFoundError("RoleTemplate", template_id)
    if template.is_system:
        raise ValidationError("Cannot delete a system role template")

    in_use = (await db.execute(
        select(func.count()).select_from(Role).where(Role.template_id == template.id)
    )).scalar_one()
    if in_use:
        raise ValidationError("Template is in use by existing roles; cannot delete")

    for row in (await db.execute(
        select(TemplatePermission).where(TemplatePermission.template_id == template.id)
    )).scalars().all():
        await db.delete(row)
    await db.delete(template)
    await record_audit(db, action="ROLE_TEMPLATE_DELETE", actor=admin, target_type="role_template",
                       target_id=template_id, request=request)
    return {"status": "deleted", "id": template_id}
