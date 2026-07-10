"""AgentAction — the generalized approval queue for proactive agent output.

Generalizes the `FlaggedAnswer` pattern (a single-purpose grading-review queue)
into one inbox every agent proposal flows through: scheduling picks, fee
reminders, at-risk alerts, etc. `FlaggedAnswer`/the Evaluator flow is
untouched — this table has no producer yet (agents land in Phase 3+); Phase 1
only adds the table, the approval routes, and `propose_agent_action()`.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SQLEnum, Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantScoped, UUIDPk


class AgentActionStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    auto_applied = "auto_applied"


class AgentAction(Base, UUIDPk, TenantScoped):
    __tablename__ = "agent_actions"

    agent_name: Mapped[str] = mapped_column(String(64), index=True)
    action_type: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float | None] = mapped_column(Float, default=None)

    status: Mapped[AgentActionStatus] = mapped_column(
        SQLEnum(AgentActionStatus, name="agent_action_status"), default=AgentActionStatus.pending
    )
    reviewed_by_user_id: Mapped[str | None] = mapped_column(String(36), default=None)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
