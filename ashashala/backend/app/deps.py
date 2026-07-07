"""FastAPI dependencies: auth, role guards, tenant scoping."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_token
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.db.session import get_db
from app.db.tenant_filter import set_current_school_id  # noqa: F401 (registers event on import)
from app.models.mixins import as_utc
from app.models.structure import (
    Enrollment,
    ParentStudentLink,
    TeacherAssignment,
)
from app.models.user import User, UserRole

# Ensure the tenant-filter session event is registered.
import app.db.tenant_filter  # noqa: F401,E402

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode the bearer token, load the user, and set the tenant context."""
    if creds is None or not creds.credentials:
        raise UnauthorizedError("Missing bearer token")

    payload = decode_token(creds.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Token missing subject")

    # User is not TenantScoped, so this load is not tenant-filtered.
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    # Reject tokens minted before the user's sessions were force-invalidated
    # (password reset, admin reset, deactivation, logout-all). Cheap: no extra
    # query, `user` is already loaded above.
    if user.tokens_valid_after is not None:
        issued_at = datetime.fromtimestamp(payload.get("iat", 0), tz=timezone.utc)
        # jose's jwt.encode truncates `iat` to whole seconds (timegm on
        # utctimetuple()), but tokens_valid_after is stored with microsecond
        # precision. Without slack, a token legitimately minted in the same
        # wall-clock second as the invalidation (e.g. reset-password ->
        # immediate re-login) can floor to just *before* tokens_valid_after
        # and get wrongly rejected. 1s tolerance matches iat's own precision.
        if issued_at < as_utc(user.tokens_valid_after) - timedelta(seconds=1):
            raise UnauthorizedError("Token has been revoked")

    # Establish tenant scope for the rest of the request from the token.
    set_current_school_id(payload.get("school_id"))
    return user


@dataclass
class PageParams:
    limit: int
    offset: int


def page_params(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> PageParams:
    """Shared limit/offset dependency for every paginated list endpoint."""
    return PageParams(limit=limit, offset=offset)


def require_role(*roles: UserRole):
    """Dependency factory enforcing that the current user has one of `roles`."""
    allowed = set(roles)

    async def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise ForbiddenError(
                f"Requires role in {[r.value for r in allowed]}, got {user.role.value}"
            )
        return user

    return _guard


async def build_token_claims(db: AsyncSession, user: User) -> dict:
    """Assemble the role-specific claim lists embedded in the access token."""
    class_ids: list[str] = []
    subject_ids: list[str] = []
    linked_student_ids: list[str] = []

    if user.role == UserRole.teacher:
        rows = (await db.execute(
            select(TeacherAssignment).where(TeacherAssignment.teacher_id == user.id)
        )).scalars().all()
        class_ids = sorted({r.class_id for r in rows})
        subject_ids = sorted({r.subject_id for r in rows})
    elif user.role == UserRole.student:
        rows = (await db.execute(
            select(Enrollment).where(Enrollment.student_id == user.id)
        )).scalars().all()
        class_ids = sorted({r.class_id for r in rows})
    elif user.role == UserRole.parent:
        rows = (await db.execute(
            select(ParentStudentLink).where(ParentStudentLink.parent_id == user.id)
        )).scalars().all()
        linked_student_ids = sorted({r.student_id for r in rows})

    return {
        "class_ids": class_ids,
        "subject_ids": subject_ids,
        "linked_student_ids": linked_student_ids,
    }


async def get_linked_child(db: AsyncSession, parent: User, student_id: str) -> User:
    """Return the student the parent is linked to.

    - Non-existent OR cross-tenant student  -> 404 (don't leak existence).
    - Exists in the same school but NOT linked -> 403 (authorization failure).
    """
    child = await db.get(User, student_id)
    if child is None or child.role != UserRole.student or child.school_id != parent.school_id:
        raise NotFoundError("Student", student_id)

    link = (await db.execute(
        select(ParentStudentLink).where(
            ParentStudentLink.parent_id == parent.id,
            ParentStudentLink.student_id == student_id,
        )
    )).scalar_one_or_none()
    if link is None:
        raise ForbiddenError("Not linked to this student")
    return child
