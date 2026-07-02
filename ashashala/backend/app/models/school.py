"""School (tenant) model."""

from __future__ import annotations

from datetime import date

from sqlalchemy import JSON, Boolean, Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPk

DEFAULT_FEATURES = {"voice": True, "ocr": True, "quiz": True, "youtube": True}


class School(Base, UUIDPk):
    __tablename__ = "schools"

    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(512), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Feature flags (voice/ocr/quiz/youtube) — checked before invoking subsystems.
    features_json: Mapped[dict] = mapped_column(JSON, default=lambda: dict(DEFAULT_FEATURES))
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    academic_year_start: Mapped[date | None] = mapped_column(Date, default=None)
    academic_year_end: Mapped[date | None] = mapped_column(Date, default=None)
