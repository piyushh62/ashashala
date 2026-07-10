"""Scheduled-Learning Agent output — one daily explainer per Timetable entry."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantScoped, UUIDPk


class LearningFeedItem(Base, UUIDPk, TenantScoped):
    __tablename__ = "learning_feed_items"

    timetable_id: Mapped[str] = mapped_column(String(36), index=True)
    class_id: Mapped[str] = mapped_column(String(36), index=True)
    subject_id: Mapped[str] = mapped_column(String(36))
    topic: Mapped[str] = mapped_column(String(255))
    explainer: Mapped[str] = mapped_column(Text)
    questions_json: Mapped[list] = mapped_column(JSON, default=list)
    feed_date: Mapped[date] = mapped_column(Date, index=True)
