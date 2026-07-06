"""Ingestion orchestrator (runs in FastAPI BackgroundTasks).

Flow: extract -> detect language -> chunk -> embed (named vector) -> upsert to
Qdrant + mirror Chunk rows in Postgres -> set Document.status. Opens its own DB
session because the request's session is already closed by the time this runs.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.document import Chunk, DocStatus, Document, SourceType
from app.services.ingestion import extractors
from app.services.lang_detect import detect_lang
from app.services.ocr_service import ocr_image
from app.services.rag.chunker import Segment, chunk_segments
from app.services.rag.embedder import embed_texts
from app.services.rag.store import get_qdrant_store

logger = logging.getLogger(__name__)


def _segments_for(source_type: SourceType, *, data: bytes | None, ref: str | None) -> list[Segment]:
    if source_type == SourceType.pdf:
        return extractors.extract_pdf(data or b"")
    if source_type == SourceType.docx:
        return extractors.extract_docx(data or b"")
    if source_type == SourceType.txt:
        return extractors.extract_txt(data or b"")
    if source_type == SourceType.url:
        return extractors.extract_url(ref or "")
    if source_type == SourceType.youtube:
        return extractors.extract_youtube(ref or "")
    if source_type == SourceType.image:
        return []  # handled by the async OCR path in ingest_document
    return []


async def _ocr_scanned_pdf_pages(
    data: bytes, *, doc_id: str, db: AsyncSession, school_id: str,
) -> list[Segment]:
    """OCR pages of a scanned/photographed PDF that have no selectable text.

    pypdf exposes each page's embedded raster images, so a photographed page
    (one big image) can be OCR'd without a PDF-render dependency (poppler etc.).
    """
    try:
        from pypdf import PdfReader
    except Exception:  # noqa: BLE001
        return []

    import io

    segments: list[Segment] = []
    reader = PdfReader(io.BytesIO(data))
    for i, page in enumerate(reader.pages, start=1):
        if (page.extract_text() or "").strip():
            continue  # already covered by extract_pdf
        images = list(getattr(page, "images", []) or [])
        if not images:
            continue
        img = max(images, key=lambda im: len(im.data))
        mime = "image/png"
        name = (getattr(img, "name", "") or "").lower()
        if name.endswith((".jpg", ".jpeg")):
            mime = "image/jpeg"
        text = await ocr_image(img.data, mime, doc_id=doc_id, page=i, db=db, school_id=school_id)
        if text.strip():
            segments.append(Segment(text=text, page_or_ts=f"p. {i}"))
    return segments


async def ingest_document(
    *,
    doc_id: str,
    school_id: str,
    class_id: str,
    subject_id: str | None,
    source_type: SourceType,
    data: bytes | None = None,
    source_ref: str | None = None,
    content_type: str | None = None,
) -> None:
    """Extract → (OCR if scanned) → chunk → embed → store. Updates Document.status."""
    async with async_session_factory() as session:
        doc = await session.get(Document, doc_id)
        if doc is None:
            logger.error("ingest: document %s not found", doc_id)
            return
        try:
            if source_type == SourceType.image:
                # Phone photo / scanned image → OCR the whole image as page 1.
                text = await ocr_image(
                    data or b"", content_type or "image/png",
                    doc_id=doc_id, page=1, db=session, school_id=school_id,
                )
                segments = [Segment(text=text, page_or_ts="p. 1")] if text.strip() else []
            else:
                segments = [s for s in _segments_for(source_type, data=data, ref=source_ref) if s.text.strip()]
                if source_type == SourceType.pdf and data:
                    # Add OCR for any image-only (scanned) pages.
                    segments.extend(await _ocr_scanned_pdf_pages(
                        data, doc_id=doc_id, db=session, school_id=school_id,
                    ))

            if not segments:
                doc.status = DocStatus.failed
                doc.error_msg = "No extractable text (empty or unreadable image)"
                await session.commit()
                return

            full_text = " ".join(s.text for s in segments)
            lang = detect_lang(full_text)
            chunks = chunk_segments(segments, lang)

            texts = [c.text for c in chunks]
            vectors, vector_name = await embed_texts(texts, lang, school_id=school_id)

            point_ids = [str(uuid.uuid4()) for _ in chunks]
            payloads = [
                {
                    "doc_id": doc_id,
                    "class_id": class_id,
                    "subject_id": subject_id,
                    "source_type": source_type.value,
                    "source_ref": doc.source_ref,
                    "page_or_ts": c.page_or_ts,
                    "lang": c.lang,
                    "r2_url": doc.storage_url,
                    "text": c.text,
                }
                for c in chunks
            ]
            await get_qdrant_store().upsert_vectors(
                school_id=school_id, vectors=vectors, payloads=payloads,
                vector_name=vector_name, ids=point_ids,
            )

            for c, pid in zip(chunks, point_ids, strict=False):
                session.add(Chunk(
                    doc_id=doc_id, school_id=school_id, class_id=class_id,
                    subject_id=subject_id, page_or_ts=c.page_or_ts, lang=c.lang,
                    qdrant_point_id=pid, vector_name=vector_name,
                ))

            doc.status = DocStatus.indexed
            doc.error_msg = None
            doc.page_count = len({s.page_or_ts for s in segments if s.page_or_ts}) or len(segments)
            await session.commit()
            logger.info("Indexed document %s (%d chunks, %s)", doc_id, len(chunks), vector_name)
        except Exception as e:  # noqa: BLE001
            await session.rollback()
            doc = await session.get(Document, doc_id)
            if doc is not None:
                doc.status = DocStatus.failed
                doc.error_msg = str(e)[:500]
                await session.commit()
            logger.exception("Ingestion failed for %s: %s", doc_id, e)
