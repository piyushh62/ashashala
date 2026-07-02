"""Documents, chunks, and the OCR cache."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SQLEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TenantScoped, UUIDPk, utcnow


class SourceType(str, enum.Enum):
    pdf = "pdf"
    docx = "docx"
    txt = "txt"
    url = "url"
    youtube = "youtube"
    image = "image"


class DocStatus(str, enum.Enum):
    pending = "pending"
    indexed = "indexed"
    failed = "failed"


class Document(Base, UUIDPk, TenantScoped):
    __tablename__ = "documents"

    class_id: Mapped[str] = mapped_column(String(36), index=True)
    subject_id: Mapped[str | None] = mapped_column(String(36), index=True, default=None)
    uploaded_by_teacher_id: Mapped[str] = mapped_column(String(36), index=True)

    filename: Mapped[str] = mapped_column(String(512))
    storage_url: Mapped[str | None] = mapped_column(String(1024), default=None)  # R2 URL
    source_type: Mapped[SourceType] = mapped_column(SQLEnum(SourceType, name="source_type"))
    source_ref: Mapped[str | None] = mapped_column(String(1024), default=None)   # filename or URL
    status: Mapped[DocStatus] = mapped_column(
        SQLEnum(DocStatus, name="doc_status"), default=DocStatus.pending
    )
    error_msg: Mapped[str | None] = mapped_column(Text, default=None)


class Chunk(Base, UUIDPk, TenantScoped):
    __tablename__ = "chunks"

    doc_id: Mapped[str] = mapped_column(String(36), index=True)
    class_id: Mapped[str] = mapped_column(String(36), index=True)
    subject_id: Mapped[str | None] = mapped_column(String(36), index=True, default=None)
    page_or_ts: Mapped[str | None] = mapped_column(String(64), default=None)  # page number or "1m24s"
    lang: Mapped[str] = mapped_column(String(8), default="en")
    qdrant_point_id: Mapped[str] = mapped_column(String(36), index=True)
    vector_name: Mapped[str] = mapped_column(String(32), default="gemini_768")


class OcrCache(Base):
    """OCR results cached forever, keyed by (doc_id, page)."""

    __tablename__ = "ocr_cache"

    doc_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    page: Mapped[int] = mapped_column(primary_key=True)
    model: Mapped[str] = mapped_column(String(128))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
