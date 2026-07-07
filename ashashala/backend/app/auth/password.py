"""Password hashing via passlib bcrypt."""

from __future__ import annotations

import re

from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd.verify(plain, hashed)
    except Exception:
        return False


def validate_password_complexity(value: str) -> str:
    """Shared Pydantic validator: min length is enforced by the field itself
    (Field(min_length=8)); this adds a letter + digit requirement so
    user-chosen passwords aren't purely numeric or purely alphabetic.

    Auto-generated temp passwords (`secrets.token_urlsafe(...)`) bypass this
    entirely — they're assigned straight to `hash_password()`, never through
    a schema that calls this validator, and already exceed this bar.
    """
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one digit")
    return value
