"""Auth routes: /login, /refresh, /me, /password-reset."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.password import hash_password, verify_password
from app.core.exceptions import UnauthorizedError
from app.db.session import get_db
from app.deps import build_token_claims, get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    PasswordResetRequest,
    RefreshRequest,
    TokenResponse,
)
from app.services.audit_service import record_audit

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


async def _issue_tokens(db: AsyncSession, user: User) -> TokenResponse:
    claims = await build_token_claims(db, user)
    access = create_access_token(
        sub=user.id,
        role=user.role.value,
        school_id=user.school_id,
        class_ids=claims["class_ids"],
        subject_ids=claims["subject_ids"],
        linked_student_ids=claims["linked_student_ids"],
    )
    refresh = create_refresh_token(sub=user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
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
async def refresh(body: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    payload = decode_token(body.refresh_token, refresh=True)
    user = await db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    await record_audit(db, action="TOKEN_REFRESH", actor=user, request=request)
    return await _issue_tokens(db, user)


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        id=user.id, name=user.name, email=user.email, role=user.role.value,
        school_id=user.school_id, grade=user.grade, interests=user.interests,
    )


@router.post("/password-reset")
async def password_reset(
    body: PasswordResetRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Authenticated self-service password reset."""
    if body.email.lower() != user.email.lower():
        raise UnauthorizedError("Can only reset your own password")
    user.password_hash = hash_password(body.new_password)
    db.add(user)
    await record_audit(db, action="PASSWORD_RESET", actor=user, target_type="user",
                       target_id=user.id, request=request)
    return {"status": "ok"}
