"""Direct parent<->teacher message thread (human-authored, not agent output)."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SQLEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantScoped, UUIDPk


class MessageSenderRole(str, enum.Enum):
    teacher = "teacher"
    parent = "parent"


class ParentMessage(Base, UUIDPk, TenantScoped):
    __tablename__ = "parent_messages"

    student_id: Mapped[str] = mapped_column(String(36), index=True)
    parent_id: Mapped[str] = mapped_column(String(36), index=True)
    teacher_id: Mapped[str] = mapped_column(String(36), index=True)
    sender_role: Mapped[MessageSenderRole] = mapped_column(
        SQLEnum(MessageSenderRole, name="message_sender_role")
    )
    body: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
