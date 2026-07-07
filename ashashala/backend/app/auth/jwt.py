"""JWT access + refresh tokens.

HS256 with symmetric secrets from the environment (JWT_SECRET / JWT_REFRESH_SECRET).
This deviates from the spec's RS256 because the provided env vars are shared
secrets, not an RSA key pair — HS256 is the correct primitive for that input.

Every token carries a `jti`. Refresh tokens' `jti` matches the id of their
`RefreshToken` DB row (see app/models/refresh_token.py), which is how
/auth/refresh detects rotation/reuse. Access tokens' `jti` is not looked up in
the DB (that would mean a query on every request) — access-token validity is
instead checked cheaply against `User.tokens_valid_after` in deps.py.

Access-token payload:
  {sub, role, school_id, class_ids, subject_ids, linked_student_ids, type, jti, exp, iat}
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.models.mixins import new_uuid

ALGORITHM = "HS256"
ACCESS_TTL = timedelta(minutes=60)
REFRESH_TTL = timedelta(days=14)


def _encode(claims: dict[str, Any], secret: str, ttl: timedelta, token_type: str, *, jti: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        **claims,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def create_access_token(
    *,
    sub: str,
    role: str,
    school_id: str | None = None,
    class_ids: list[str] | None = None,
    subject_ids: list[str] | None = None,
    linked_student_ids: list[str] | None = None,
) -> str:
    return _encode(
        {
            "sub": sub,
            "role": role,
            "school_id": school_id,
            "class_ids": class_ids or [],
            "subject_ids": subject_ids or [],
            "linked_student_ids": linked_student_ids or [],
        },
        settings.JWT_SECRET,
        ACCESS_TTL,
        "access",
        jti=new_uuid(),
    )


def create_refresh_token(*, sub: str, jti: str) -> str:
    """`jti` must be the id of the caller's already-created `RefreshToken` row."""
    return _encode({"sub": sub}, settings.JWT_REFRESH_SECRET, REFRESH_TTL, "refresh", jti=jti)


def decode_token(token: str, *, refresh: bool = False) -> dict[str, Any]:
    secret = settings.JWT_REFRESH_SECRET if refresh else settings.JWT_SECRET
    expected_type = "refresh" if refresh else "access"
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except JWTError as e:
        raise UnauthorizedError(f"Invalid token: {e}")
    if payload.get("type") != expected_type:
        raise UnauthorizedError("Wrong token type")
    return payload
