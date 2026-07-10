"""Reporting Agent.

Weekly/monthly cron that builds a per-student parent-facing progress report:
mastery snapshot + quiz score trend are collected deterministically in Python
(no history table exists, so "mastery trend" is a current-snapshot, not a
time series — same limitation already accepted for the Insight Agent); only
the narrative paragraph is LLM-composed, with a templated fallback so an LLM
outage never blocks report generation.

Governance: a school's `features_json["reports_auto_approve"]` flag (default
False) controls whether a generated report is immediately sent or queued as a
pending AgentAction for a teacher to review first (Part 5.2: "Teacher reviews
before send (first few cycles), then auto-send once trusted").
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import communication
from app.agents.json_utils import extract_json
from app.agents.prompts.reporting_prompt import build_report_prompt
from app.db.tenant_filter import tenant_bypass
from app.models.agent_action import AgentActionStatus
from app.models.learning import ProgressRecord, QuizAttempt
from app.models.report import Report, ReportStatus
from app.models.school import School
from app.models.structure import Enrollment, ParentStudentLink
from app.models.user import User
from app.services.audit_service import record_audit
from app.services.llm_router import chat as llm_chat
from app.services.rbac_service import propose_agent_action

logger = logging.getLogger(__name__)


def _fallback_narrative(student_name: str, mastery_snapshot: list[dict], quiz_trend: list[dict]) -> str:
    if mastery_snapshot:
        topics = ", ".join(m["topic"] for m in mastery_snapshot[:3])
        mastery_line = f"is currently working on {topics}"
    else:
        mastery_line = "has no recorded topic progress this period"
    scores = [q["score"] for q in quiz_trend if q.get("score") is not None]
    quiz_line = f" and completed {len(scores)} quiz attempt(s)" if scores else ""
    return f"{student_name} {mastery_line}{quiz_line} this period. Check the app for full details."


async def _compose_narrative(
    *, student_name: str, mastery_snapshot: list[dict], quiz_trend: list[dict],
    teacher_notes: str | None, period_start: date, period_end: date,
    school_id: str, student_id: str,
) -> str:
    try:
        prompt = build_report_prompt(
            student_name=student_name, mastery_snapshot=mastery_snapshot, quiz_trend=quiz_trend,
            teacher_notes=teacher_notes, period_start=period_start.isoformat(), period_end=period_end.isoformat(),
        )
        raw = await llm_chat(
            messages=[{"role": "user", "content": prompt}], task="explain",
            school_id=school_id, user_id=student_id,
        )
        parsed = extract_json(raw)
        narrative = str(parsed.get("narrative", "")).strip() if isinstance(parsed, dict) else ""
        if narrative:
            return narrative
    except Exception as e:  # noqa: BLE001 — never let report generation block on LLM failure
        logger.warning("Reporting agent narrative composition failed, using fallback: %s", e)
    return _fallback_narrative(student_name, mastery_snapshot, quiz_trend)


async def _reports_auto_approve(db: AsyncSession, school_id: str) -> bool:
    school = await db.get(School, school_id)
    return bool(school and school.features_json.get("reports_auto_approve", False))


async def generate_reports(db: AsyncSession, *, period_start: date, period_end: date) -> int:
    """Generate one Report per enrolled+parent-linked student for the given
    period. Returns the number of reports created."""
    created = 0
    with tenant_bypass():
        enrollments = (await db.execute(
            select(Enrollment).where(Enrollment.end_date.is_(None))
        )).scalars().all()
        seen_students = {e.student_id for e in enrollments}

        for student_id in seen_students:
            has_parent = (await db.execute(
                select(ParentStudentLink.id).where(ParentStudentLink.student_id == student_id)
            )).first()
            if has_parent is None:
                continue

            already_exists = (await db.execute(
                select(Report.id).where(
                    Report.student_id == student_id, Report.period_start == period_start,
                    Report.period_end == period_end,
                )
            )).first()
            if already_exists is not None:
                continue

            student = await db.get(User, student_id)
            if student is None:
                continue

            progress = (await db.execute(
                select(ProgressRecord).where(ProgressRecord.student_id == student_id)
            )).scalars().all()
            mastery_snapshot = [{"topic": p.topic, "score": p.mastery_score} for p in progress]

            attempts = (await db.execute(
                select(QuizAttempt).where(
                    QuizAttempt.student_id == student_id,
                    QuizAttempt.attempted_at >= period_start, QuizAttempt.attempted_at <= period_end,
                )
            )).scalars().all()
            quiz_trend = [
                {"quiz_id": a.quiz_id, "score": a.score, "attempted_at": a.attempted_at.isoformat()}
                for a in attempts
            ]

            narrative = await _compose_narrative(
                student_name=student.name, mastery_snapshot=mastery_snapshot, quiz_trend=quiz_trend,
                teacher_notes=None, period_start=period_start, period_end=period_end,
                school_id=student.school_id, student_id=student_id,
            )

            report = Report(
                school_id=student.school_id, student_id=student_id,
                period_start=period_start, period_end=period_end,
                mastery_snapshot_json=mastery_snapshot, quiz_score_trend_json=quiz_trend,
                narrative=narrative, status=ReportStatus.draft,
            )
            db.add(report)
            await db.flush()

            action = await propose_agent_action(
                db, school_id=student.school_id, agent_name="reporting_agent", action_type="report_ready",
                payload={
                    "report_id": report.id, "student_id": student_id,
                    "period_start": period_start.isoformat(), "period_end": period_end.isoformat(),
                },
            )

            if await _reports_auto_approve(db, student.school_id):
                action.status = AgentActionStatus.auto_applied
                db.add(action)
                await communication.send_report_message(db, report=report, actor=None)

            await record_audit(
                db, action="REPORT_GENERATED", actor=None, school_id=student.school_id,
                target_type="report", target_id=report.id,
                payload={"student_id": student_id, "period_start": period_start.isoformat()},
            )
            created += 1

    return created
