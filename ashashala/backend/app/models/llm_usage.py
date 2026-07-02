"""LlmUsage model — one row per LLM/embedding call.

Written by the LLM router (and clients) so the platform can surface per-school
token spend and latency (Section 10 of PROJECT_PROMPT.md, extended with
`model_id` + `error_message` for debugging). Not tenant-filtered by the event
listener: super-admin dashboards read across schools, and `school_id` is
nullable for super-admin / system calls.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LlmUsage(Base):
    __tablename__ = "llm_usage"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )

    # Nullable for super-admin / system calls (school_id = NULL).
    school_id: Mapped[str | None] = mapped_column(String(36), index=True, default=None)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True, default=None)

    provider: Mapped[str] = mapped_column(String(32))          # "gemini" | "nvidia"
    model_role: Mapped[str] = mapped_column(String(64))        # registry role
    model_id: Mapped[str | None] = mapped_column(String(128), default=None)
    task: Mapped[str] = mapped_column(String(64), index=True)

    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(BigInteger, default=0)

    status: Mapped[str] = mapped_column(String(16), default="success")  # success|error
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    def __repr__(self) -> str:  # pragma: no cover - debug convenience
        return (
            f"<LlmUsage {self.provider}/{self.model_role} task={self.task} "
            f"status={self.status}>"
        )
