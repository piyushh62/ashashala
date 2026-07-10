"""Auth routes: /login, /refresh, /logout, /logout-all, /me, /password-reset."""

# NOTE: do NOT add `from __future__ import annotations` here. This module uses
# @limiter.limit(...) (slowapi) on login/refresh/password-reset, which wraps
# endpoints in a closure defined in slowapi's own module. Postponed annotations
# would need to resolve forward refs against that wrapper's __globals__
# (slowapi's, not this module's), causing a PydanticUndefinedAnnotation error
# at import time. Same reasoning as app/routes/student.py.

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import REFRESH_TTL, create_access_token, create_refresh_token, decode_token
from app.auth.password import hash_password, verify_password
from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.ratelimit import limiter
from app.db.session import get_db
from app.deps import build_token_claims, get_current_user
from app.models.mixins import as_utc, new_uuid
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MeResponse,
    PasswordResetRequest,
    RefreshRequest,
    TokenResponse,
)
from app.services.audit_service import record_audit
from app.services.rbac_service import resolve_permissions

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


async def _issue_tokens(
    db: AsyncSession, user: User, *, replaces: RefreshToken | None = None
) -> TokenResponse:
    """Mint a fresh access+refresh pair, recording a new `RefreshToken` row.

    When `replaces` is given (rotation on /refresh), the old row is linked via
    `replaced_by_id` — it must already be marked `revoked_at` by the caller.
    """
    claims = await build_token_claims(db, user)
    access = create_access_token(
        sub=user.id,
        role=user.role.value,
        school_id=user.school_id,
        class_ids=claims["class_ids"],
        subject_ids=claims["subject_ids"],
        linked_student_ids=claims["linked_student_ids"],
        permissions=claims["permissions"],
    )
    jti = new_uuid()
    now = datetime.now(timezone.utc)
    db.add(RefreshToken(id=jti, user_id=user.id, expires_at=now + REFRESH_TTL))
    if replaces is not None:
        replaces.replaced_by_id = jti
        db.add(replaces)
    refresh = create_refresh_token(sub=user.id, jti=jti)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = (await db.execute(
        select(User).where(User.email == body.email)
    )).scalar_one_or_none()

    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        await record_audit(db, action="LOGIN_FAILURE", target_type="user",
                           target_id=body.email, status="failure", request=request)
        raise UnauthorizedError("Invalid email or password")

    await record_audit(db, action="LOGIN_SUCCESS", actor=user, target_type="user",
                       target_id=user.id, request=request)
    return await _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def refresh(body: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    payload = decode_token(body.refresh_token, refresh=True)
    user = await db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    jti = payload.get("jti")
    token_row = await db.get(RefreshToken, jti) if jti else None
    if token_row is None or token_row.user_id != user.id:
        raise UnauthorizedError("Refresh token not recognized")

    now = datetime.now(timezone.utc)

    if token_row.revoked_at is not None:
        # Reuse of an already-rotated/revoked token — treat as a compromised
        # session and kill every outstanding refresh + access token for this user.
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        user.tokens_valid_after = now
        db.add(user)
        await record_audit(db, action="TOKEN_REUSE_DETECTED", actor=user, target_type="user",
                           target_id=user.id, status="failure", request=request)
        raise UnauthorizedError("Refresh token reuse detected — all sessions revoked")

    if as_utc(token_row.expires_at) < now:
        raise UnauthorizedError("Refresh token expired")

    token_row.revoked_at = now
    result = await _issue_tokens(db, user, replaces=token_row)
    await record_audit(db, action="TOKEN_REFRESH", actor=user, request=request)
    return result


@router.post("/logout")
async def logout(body: LogoutRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """Revoke a single refresh token. Idempotent — an unrecognized or already
    revoked/expired token is treated as already logged out, not an error."""
    try:
        payload = decode_token(body.refresh_token, refresh=True)
    except UnauthorizedError:
        return {"status": "ok"}

    jti = payload.get("jti")
    token_row = await db.get(RefreshToken, jti) if jti else None
    if token_row is not None and token_row.revoked_at is None:
        token_row.revoked_at = datetime.now(timezone.utc)
        db.add(token_row)
    return {"status": "ok"}


@router.post("/logout-all")
async def logout_all(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke every refresh token for the caller and invalidate all live
    access tokens (e.g. "log out of all devices")."""
    now = datetime.now(timezone.utc)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    user.tokens_valid_after = now
    db.add(user)
    await record_audit(db, action="LOGOUT_ALL", actor=user, target_type="user",
                       target_id=user.id, request=request)
    return {"status": "ok"}


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> MeResponse:
    permissions = sorted(await resolve_permissions(db, user))
    return MeResponse(
        id=user.id, name=user.name, email=user.email, role=user.role.value,
        school_id=user.school_id, grade=user.grade, interests=user.interests,
        permissions=permissions,
    )


@router.post("/password-reset")
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def password_reset(
    body: PasswordResetRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Authenticated self-service password reset. Invalidates all existing
    sessions (access + refresh tokens) so a leaked old session can't persist
    past the user changing their password."""
    if body.email.lower() != user.email.lower():
        raise UnauthorizedError("Can only reset your own password")
    user.password_hash = hash_password(body.new_password)
    user.tokens_valid_after = datetime.now(timezone.utc)
    db.add(user)
    await record_audit(db, action="PASSWORD_RESET", actor=user, target_type="user",
                       target_id=user.id, request=request)
    return {"status": "ok"}
