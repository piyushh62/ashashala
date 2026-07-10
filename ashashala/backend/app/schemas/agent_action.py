"""Agent Action queue schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AgentActionOut(BaseModel):
    id: str
    agent_name: str
    action_type: str
    payload_json: dict
    confidence: float | None
    status: str
    reviewed_by_user_id: str | None
    reviewed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentActionReview(BaseModel):
    note: str | None = None
