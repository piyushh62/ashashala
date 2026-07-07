"""Shared model mixins."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """Attach UTC tzinfo to a naive datetime read back from the DB.

    Postgres (prod) round-trips `DateTime(timezone=True)` values with tzinfo
    intact; SQLite (tests) does not — every column using this pattern is
    written via `utcnow()`/`datetime.now(timezone.utc)`, so a naive value read
    back is always UTC. Comparing it against a tz-aware datetime without this
    raises `TypeError: can't compare offset-naive and offset-aware datetimes`.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class UUIDPk:
    """String(36) UUID primary key + created_at timestamp."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class TenantScoped:
    """Marks a model as tenant-scoped. The tenant filter (app/db/tenant_filter.py)
    auto-injects `school_id == current_school_id` on every SELECT for subclasses.

    Presence of this mixin — NOT merely a school_id column — is what the filter
    keys on, so `User`/`School` (which have special cross-tenant rules) are
    deliberately NOT TenantScoped even though User has a school_id.
    """

    school_id: Mapped[str] = mapped_column(String(36), index=True)
