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


async def _notify_substitute_after_approval(db: AsyncSession, action: AgentAction, user: User) -> None:
    """Approving a Staffing Agent proposal always notifies its top-ranked
    candidate — the generic approve route only carries a free-text `note`, not
    a candidate pick, so the ranking done at proposal time is the decision."""
    candidates = action.payload_json.get("candidates") or []
    if not candidates:
        return
    teacher_id = candidates[0].get("teacher_id")
    if not teacher_id:
        return
    subject_name = action.payload_json.get("subject_name", "a class")
    class_name = action.payload_json.get("class_name", "")
    period = action.payload_json.get("period_number")
    absence_date = action.payload_json.get("absence_date")
    await notify(
        db, user_id=teacher_id, school_id=action.school_id, type="substitute_request",
        title="You've been asked to substitute",
        body=f"Cover {subject_name} for {class_name}, period {period} on {absence_date}.",
        link="/teacher/timetable",
    )


AGENT_ACTION_HANDLERS: dict[tuple[str, str], Handler] = {
    ("reporting_agent", "report_ready"): _send_report_after_approval,
    ("communication_agent", "at_risk_parent_message"): _send_at_risk_message_after_approval,
    ("staffing_agent", "substitute_suggestion"): _notify_substitute_after_approval,
}
