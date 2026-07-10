"""Insight / Intervention Agent.

Nightly scan for struggling students (deterministic: mastery threshold +
cooldown-based dedup — there's no history table to read "N weeks running"
from). The teacher-facing alert sentence is LLM-composed with a plain-text
fallback so an LLM outage never blocks the alert itself.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import communication
from app.agents.json_utils import extract_json
from app.agents.prompts.insight_prompt import build_insight_prompt
from app.core.config import settings
from app.db.tenant_filter import tenant_bypass
from app.models.agent_action import AgentAction, AgentActionStatus
from app.models.learning import ProgressRecord
from app.models.structure import Enrollment, ParentStudentLink, TeacherAssignment
from app.models.user import User
from app.services.audit_service import record_audit
from app.services.llm_router import chat as llm_chat
from app.services.notification_service import notify
from app.services.rbac_service import propose_agent_action

logger = logging.getLogger(__name__)


def _fallback_alert(student_name: str, topic: str, mastery_score: int) -> str:
    return (
        f"{student_name} is struggling with {topic} (mastery {mastery_score}/100) "
        "— consider a quick check-in or a targeted practice set."
    )


async def _compose_alert(*, student_name: str, topic: str, mastery_score: int, grade: int | None,
                         school_id: str, student_id: str) -> str:
    try:
        prompt = build_insight_prompt(
            student_name=student_name, topic=topic, mastery_score=mastery_score, grade=grade,
        )
        raw = await llm_chat(
            messages=[{"role": "user", "content": prompt}], task="explain",
            school_id=school_id, user_id=student_id,
        )
        parsed = extract_json(raw)
        alert = str(parsed.get("alert", "")).strip() if isinstance(parsed, dict) else ""
        if alert:
            return alert
    except Exception as e:  # noqa: BLE001 — never let a non-critical alert block on LLM failure
        logger.warning("Insight agent alert composition failed, using fallback: %s", e)
    return _fallback_alert(student_name, topic, mastery_score)


async def run_insight_scan(db: AsyncSession) -> int:
    """Scan for struggling students, queue an auto-applied AgentAction + notify
    their teacher(s) for each. Returns the number of alerts created."""
    created = 0
    with tenant_bypass():
        struggling = (await db.execute(
            select(ProgressRecord).where(ProgressRecord.mastery_score < settings.INSIGHT_STRUGGLE_THRESHOLD)
        )).scalars().all()

        cutoff = datetime.now(UTC) - timedelta(days=settings.INSIGHT_REALERT_COOLDOWN_DAYS)
        recent_alerts = (await db.execute(
            select(AgentAction).where(
                AgentAction.agent_name == "insight_agent", AgentAction.created_at >= cutoff,
            )
        )).scalars().all()
        already_alerted = {
            (a.payload_json.get("student_id"), a.payload_json.get("topic")) for a in recent_alerts
        }

        for record in struggling:
            if (record.student_id, record.topic) in already_alerted:
                continue

            enrollment = (await db.execute(
                select(Enrollment).where(
                    Enrollment.student_id == record.student_id, Enrollment.end_date.is_(None)
                )
            )).scalars().first()
            if enrollment is None:
                continue

            teacher_ids = (await db.execute(
                select(TeacherAssignment.teacher_id).where(
                    TeacherAssignment.class_id == enrollment.class_id,
                    TeacherAssignment.subject_id == record.subject_id,
                    TeacherAssignment.end_date.is_(None),
                )
            )).scalars().all()
            if not teacher_ids:
                continue

            student = await db.get(User, record.student_id)
            student_name = student.name if student else record.student_id
            grade = student.grade if student else None

            alert_text = await _compose_alert(
                student_name=student_name, topic=record.topic, mastery_score=record.mastery_score,
                grade=grade, school_id=record.school_id, student_id=record.student_id,
            )

            confidence = round(1 - record.mastery_score / settings.INSIGHT_STRUGGLE_THRESHOLD, 2)
            action = await propose_agent_action(
                db, school_id=record.school_id, agent_name="insight_agent",
                action_type="struggling_student_alert",
                payload={
                    "student_id": record.student_id, "student_name": student_name, "topic": record.topic,
                    "subject_id": record.subject_id, "class_id": enrollment.class_id,
                    "mastery_score": record.mastery_score, "alert_text": alert_text,
                },
                confidence=confidence,
            )
            action.status = AgentActionStatus.auto_applied
            db.add(action)
            already_alerted.add((record.student_id, record.topic))

            for teacher_id in teacher_ids:
                await notify(
                    db, user_id=teacher_id, school_id=record.school_id, type="insight_alert",
                    title="Student may need support", body=alert_text,
                    link=f"/teacher/classes/{enrollment.class_id}/progress",
                )

            if student is not None:
                parent_links = (await db.execute(
                    select(ParentStudentLink).where(ParentStudentLink.student_id == record.student_id)
                )).scalars().all()
                await communication.propose_at_risk_message(
                    db, school_id=record.school_id, student=student, parent_links=parent_links,
                    topic=record.topic, mastery_score=record.mastery_score, alert_text=alert_text,
                )

            await record_audit(
                db, action="INSIGHT_ALERT", actor=None, school_id=record.school_id,
                target_type="agent_action", target_id=action.id,
                payload={"student_id": record.student_id, "topic": record.topic},
            )
            created += 1

    return created
