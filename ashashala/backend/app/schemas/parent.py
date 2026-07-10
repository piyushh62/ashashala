"""Parent schemas (messages, notification preferences)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.communication import MessageSenderRole


class ParentMessageOut(BaseModel):
    id: str
    student_id: str
    parent_id: str
    teacher_id: str
    sender_role: MessageSenderRole
    body: str
    created_at: datetime
    read_at: datetime | None

    model_config = {"from_attributes": True}


class ParentMessageCreate(BaseModel):
    student_id: str
    teacher_id: str
    body: str = Field(min_length=1, max_length=4000)


class NotificationPreferenceOut(BaseModel):
    in_app_enabled: bool
    sms_enabled: bool
    whatsapp_enabled: bool
    email_enabled: bool

    model_config = {"from_attributes": True}


class NotificationPreferencePatch(BaseModel):
    in_app_enabled: bool | None = None
    sms_enabled: bool | None = None
    whatsapp_enabled: bool | None = None
    email_enabled: bool | None = None
