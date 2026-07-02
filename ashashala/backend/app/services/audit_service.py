"""Audit logging (Section 5).

- `AuditMiddleware` stamps each request with a request_id + client info on
  `request.state`, so any handler can attach them to an audit row.
- `record_audit(...)` writes one `AuditLog` row (payload is hashed, never stored
  raw). Call it from routes for state-changing actions and sensitive reads
  (PARENT_VIEW_CHILD, SUPER_ADMIN_DATA_ACCESS).
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.models.audit import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        client = request.client
        request.state.client_ip = client.host if client else None
        request.state.user_agent = request.headers.get("user-agent")
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response


def _hash_payload(payload: Any) -> str | None:
    if payload is None:
        return None
    try:
        raw = json.dumps(payload, sort_keys=True, default=str).encode()
    except Exception:
        raw = str(payload).encode()
    return hashlib.sha256(raw).hexdigest()


async def record_audit(
    db: AsyncSession,
    *,
    action: str,
    actor: User | None = None,
    school_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    status: str = "success",
    payload: Any | None = None,
    error_msg: str | None = None,
    request: Request | None = None,
) -> None:
    """Persist an audit row and COMMIT it.

    Audits are committed here (not merely flushed) so that failure-path audits
    (e.g. LOGIN_FAILURE, followed by the route raising 401) survive the request's
    rollback. On success paths this also commits the pending state change, which
    is the intended effect. Never breaks the request.
    """
    try:
        row = AuditLog(
            action=action,
            actor_user_id=actor.id if actor else None,
            actor_role=actor.role.value if actor else None,
            school_id=school_id if school_id is not None else (actor.school_id if actor else None),
            target_type=target_type,
            target_id=target_id,
            status=status,
            payload_hash=_hash_payload(payload),
            error_msg=error_msg,
            ip=getattr(request.state, "client_ip", None) if request else None,
            user_agent=getattr(request.state, "user_agent", None) if request else None,
            request_id=getattr(request.state, "request_id", None) if request else None,
        )
        db.add(row)
        await db.commit()
    except Exception as e:  # noqa: BLE001 — auditing must not break the action
        logger.error("Failed to write audit log (action=%s): %s", action, e)
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            pass
