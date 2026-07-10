"""Communication Agent.

Two triggers, per Part 5.2 of the master doc:
  - Report ready (low-risk digest) -> composes a short parent-facing message
    and sends it immediately via each parent's enabled channels.
  - At-risk student detected (high-risk concern, called from the Insight
    Agent) -> drafts a parent-facing message but leaves it `pending` in the
    AgentAction queue for a teacher to approve before it's sent.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.json_utils import extract_json
from app.agents.prompts.communication_prompt import (
    build_at_risk_message_prompt,
    build_report_message_prompt,
)
from app.models.report import Report, ReportStatus
from app.models.structure import ParentStudentLink
from app.models.user import User
from app.services.audit_service import record_audit
from app.services.llm_router import chat as llm_chat
from app.services.notification_preference_service import get_enabled_channels
from app.services.notification_service import notify
from app.services.rbac_service import propose_agent_action

logger = logging.getLogger(__name__)


def _fallback_report_message(period_end: str) -> str:
    return f"Your child's progress report for the period ending {period_end} is ready — open the app to view it."


def _fallback_at_risk_message(topic: str) -> str:
    return f"Your child could use a bit of extra support with {topic}. The school is here to help if you'd like to check in."


async def _compose_report_message(*, student_name: str, narrative: str, school_id: str, student_id: str) -> str:
    try:
        prompt = build_report_message_prompt(student_name=student_name, narrative=narrative)
        raw = await llm_chat(
            messages=[{"role": "user", "content": prompt}], task="explain",
            school_id=school_id, user_id=student_id,
        )
        parsed = extract_json(raw)
        message = str(parsed.get("message", "")).strip() if isinstance(parsed, dict) else ""
        if message:
            return message
    except Exception as e:  # noqa: BLE001 — never block a report send on LLM failure
        logger.warning("Communication agent report-message composition failed, using fallback: %s", e)
    return ""


async def send_report_message(db: AsyncSession, *, report: Report, actor: User | None) -> None:
    """Notify every parent linked to `report.student_id` that their report is
    ready, via each parent's enabled channels. Marks the report sent."""
    student = await db.get(User, report.student_id)
    student_name = student.name if student else report.student_id

    message = await _compose_report_message(
        student_name=student_name, narrative=report.narrative,
        school_id=report.school_id, student_id=report.student_id,
    ) or _fallback_report_message(report.period_end.isoformat())

    parent_links = (await db.execute(
        select(ParentStudentLink).where(ParentStudentLink.student_id == report.student_id)
    )).scalars().all()

    for link in parent_links:
        channels = await get_enabled_channels(db, user_id=link.parent_id, school_id=report.school_id)
        for channel in channels:
            await notify(
                db, user_id=link.parent_id, school_id=report.school_id, type="report_ready",
                title="New progress report available", body=message,
                link=f"/parent/children/{report.student_id}/reports/{report.id}", channel=channel,
            )

    report.status = ReportStatus.sent
    report.sent_at = datetime.now(UTC)
    db.add(report)

    await record_audit(
        db, action="REPORT_SENT", actor=actor, school_id=report.school_id,
        target_type="report", target_id=report.id, payload={"student_id": report.student_id},
    )


async def _compose_at_risk_message(*, student_name: str, topic: str, alert_text: str, school_id: str, student_id: str) -> str:
    try:
        prompt = build_at_risk_message_prompt(student_name=student_name, topic=topic, alert_text=alert_text)
        raw = await llm_chat(
            messages=[{"role": "user", "content": prompt}], task="explain",
            school_id=school_id, user_id=student_id,
        )
        parsed = extract_json(raw)
        message = str(parsed.get("message", "")).strip() if isinstance(parsed, dict) else ""
        if message:
            return message
    except Exception as e:  # noqa: BLE001 — never block alert creation on LLM failure
        logger.warning("Communication agent at-risk-message composition failed, using fallback: %s", e)
    return ""


async def propose_at_risk_message(
    db: AsyncSession, *, school_id: str, student: User, parent_links: list[ParentStudentLink],
    topic: str, mastery_score: int, alert_text: str,
) -> None:
    """Draft a parent-facing at-risk message per linked parent and queue it as
    a pending AgentAction — high-risk, needs teacher approval before send."""
    if not parent_links:
        return

    message = await _compose_at_risk_message(
        student_name=student.name, topic=topic, alert_text=alert_text,
        school_id=school_id, student_id=student.id,
    ) or _fallback_at_risk_message(topic)

    confidence = round(1 - mastery_score / 100, 2)
    for link in parent_links:
        await propose_agent_action(
            db, school_id=school_id, agent_name="communication_agent", action_type="at_risk_parent_message",
            payload={
                "student_id": student.id, "parent_id": link.parent_id, "topic": topic,
                "message_text": message, "link": f"/parent/children/{student.id}/dashboard",
            },
            confidence=confidence,
        )
