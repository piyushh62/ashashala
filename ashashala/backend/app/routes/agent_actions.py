"""Agent Action queue — generalized approval inbox for proactive agent output.

Generalizes the `FlaggedAnswer` review pattern into one inbox every agent
proposal flows through. `AgentAction` has no producer yet (agents land in
Phase 3+) — see `app/services/rbac_service.py::propose_agent_action` for the
entry point they'll call. This module is the review/approve/reject surface a
human uses once one does.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.permissions import AGENT_ACTION_APPROVE, AGENT_ACTION_REJECT, AGENT_ACTION_VIEW
from app.db.session import get_db
from app.deps import PageParams, page_params, require_permission
from app.models.agent_action import AgentAction, AgentActionStatus
from app.models.user import User
from app.schemas.agent_action import AgentActionOut, AgentActionReview
from app.schemas.pagination import Page
from app.services.agent_action_handlers import AGENT_ACTION_HANDLERS
from app.services.audit_service import record_audit

router = APIRouter(prefix="/api/v1/agent-actions", tags=["Agent Actions"])
_view_guard = require_permission(AGENT_ACTION_VIEW)
_approve_guard = require_permission(AGENT_ACTION_APPROVE)
_reject_guard = require_permission(AGENT_ACTION_REJECT)


@router.get("", response_model=Page[AgentActionOut])
async def list_agent_actions(status: AgentActionStatus | None = Query(default=None),
                             agent_name: str | None = Query(default=None),
                             page: PageParams = Depends(page_params),
                             user: User = Depends(_view_guard), db: AsyncSession = Depends(get_db)) -> Page[AgentActionOut]:
    """Tenant-scoped automatically (`AgentAction` is `TenantScoped`) — a school
    only ever sees its own agent proposals."""
    stmt = select(AgentAction)
    count_stmt = select(func.count()).select_from(AgentAction)
    if status is not None:
        stmt = stmt.where(AgentAction.status == status)
        count_stmt = count_stmt.where(AgentAction.status == status)
    if agent_name is not None:
        stmt = stmt.where(AgentAction.agent_name == agent_name)
        count_stmt = count_stmt.where(AgentAction.agent_name == agent_name)
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(
        stmt.order_by(AgentAction.created_at.desc()).limit(page.limit).offset(page.offset)
    )).scalars().all()
    return Page(items=[AgentActionOut.model_validate(r) for r in rows], total=total,
               limit=page.limit, offset=page.offset)


async def _get_pending_action(db: AsyncSession, user: User, action_id: str) -> AgentAction:
    """`db.get()` bypasses the SELECT-based tenant filter (it doesn't fire the
    `do_orm_execute` event) — same reason `override_flagged_answer` re-checks
    `school_id` manually after the fetch instead of trusting the query."""
    action = await db.get(AgentAction, action_id)
    if action is None or action.school_id != user.school_id:
        raise NotFoundError("AgentAction", action_id)
    if action.status != AgentActionStatus.pending:
        raise ValidationError(f"Action already {action.status.value}")
    return action


@router.post("/{action_id}/approve", response_model=AgentActionOut)
async def approve_agent_action(action_id: str, request: Request, body: AgentActionReview = AgentActionReview(),
                               user: User = Depends(_approve_guard), db: AsyncSession = Depends(get_db)) -> AgentActionOut:
    action = await _get_pending_action(db, user, action_id)
    action.status = AgentActionStatus.approved
    action.reviewed_by_user_id = user.id
    action.reviewed_at = datetime.now(UTC)
    db.add(action)
    handler = AGENT_ACTION_HANDLERS.get((action.agent_name, action.action_type))
    if handler is not None:
        await handler(db, action, user)
    await record_audit(db, action="AGENT_ACTION_APPROVE", actor=user, target_type="agent_action",
                       target_id=action_id, payload={"note": body.note}, request=request)
    return AgentActionOut.model_validate(action)


@router.post("/{action_id}/reject", response_model=AgentActionOut)
async def reject_agent_action(action_id: str, request: Request, body: AgentActionReview = AgentActionReview(),
                              user: User = Depends(_reject_guard), db: AsyncSession = Depends(get_db)) -> AgentActionOut:
    action = await _get_pending_action(db, user, action_id)
    action.status = AgentActionStatus.rejected
    action.reviewed_by_user_id = user.id
    action.reviewed_at = datetime.now(UTC)
    db.add(action)
    await record_audit(db, action="AGENT_ACTION_REJECT", actor=user, target_type="agent_action",
                       target_id=action_id, payload={"note": body.note}, request=request)
    return AgentActionOut.model_validate(action)
