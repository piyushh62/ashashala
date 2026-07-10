"""Approval-triggered side effects for the generalized AgentAction queue.

Most agent proposals (e.g. the Scheduling Agent's timetable options) have
their own dedicated approve-equivalent route because approval needs extra
context (re-validating slots, picking one of several options). The two
handlers here are the first to need only "approved -> do the one obvious
thing" — registered by (agent_name, action_type) and invoked by
`app.routes.agent_actions.approve_agent_action` after it flips the action to
`approved`. Unregistered pairs are a no-op, so this never changes behavior
for producers that don't opt in.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import communication
from app.models.agent_action import AgentAction
from app.models.report import Report, ReportStatus
from app.models.user import User
from app.services.notification_preference_service import get_enabled_channels
from app.services.notification_service import notify

Handler = Callable[[AsyncSession, AgentAction, User], Awaitable[None]]


async def _send_report_after_approval(db: AsyncSession, action: AgentAction, user: User) -> None:
    report_id = action.payload_json.get("report_id")
    report = await db.get(Report, report_id) if report_id else None
    if report is None or report.status != ReportStatus.draft:
        return
    await communication.send_report_message(db, report=report, actor=user)


async def _send_at_risk_message_after_approval(db: AsyncSession, action: AgentAction, user: User) -> None:
    parent_id = action.payload_json.get("parent_id")
    message_text = action.payload_json.get("message_text", "")
    link = action.payload_json.get("link")
    if not parent_id:
        return
    channels = await get_enabled_channels(db, user_id=parent_id, school_id=action.school_id)
    for channel in channels:
        await notify(
            db, user_id=parent_id, school_id=action.school_id, type="at_risk_alert",
            title="A note about your child", body=message_text, link=link, channel=channel,
        )


AGENT_ACTION_HANDLERS: dict[tuple[str, str], Handler] = {
    ("reporting_agent", "report_ready"): _send_report_after_approval,
    ("communication_agent", "at_risk_parent_message"): _send_at_risk_message_after_approval,
}
