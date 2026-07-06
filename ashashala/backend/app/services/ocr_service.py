"""OCR for scanned / photographed pages.

Uses a vision-language model to read text off an image (Gemini `gemini-2.5-flash`
primary → NVIDIA vision fallback). A VLM is more robust than a classic OCR model
for phone photos and handwriting, and both providers are catalog-verified.

Results are cached forever in OcrCache keyed by (doc_id, page) so re-ingestion
never re-spends a vision call on the same page.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import OcrCache
from app.services.gemini_client import get_gemini_client
from app.services.model_registry import model_for
from app.services.nvidia_client import get_nvidia_client

logger = logging.getLogger(__name__)

_OCR_PROMPT = (
    "Extract ALL text from this image exactly as written, preserving line breaks "
    "and reading order. Do not summarize, translate, or add commentary. If the "
    "image contains no readable text, reply with an empty response."
)


async def _cached_text(db: AsyncSession, doc_id: str, page: int) -> str | None:
    row = await db.get(OcrCache, (doc_id, page))
    return row.text if row is not None else None


async def _store_text(db: AsyncSession, doc_id: str, page: int, model: str, text: str) -> None:
    if await db.get(OcrCache, (doc_id, page)) is not None:
        return
    db.add(OcrCache(doc_id=doc_id, page=page, model=model, text=text))
    await db.flush()


async def ocr_image(
    image_bytes: bytes,
    mime: str = "image/png",
    *,
    doc_id: str | None = None,
    page: int | None = None,
    db: AsyncSession | None = None,
    school_id: str | None = None,
    user_id: str | None = None,
) -> str:
    """Return the text extracted from an image.

    When (db, doc_id, page) are supplied the result is read from / written to
    OcrCache. Tries Gemini vision first, falls back to NVIDIA vision; returns ""
    if both providers fail.
    """
    if db is not None and doc_id is not None and page is not None:
        cached = await _cached_text(db, doc_id, page)
        if cached is not None:
            return cached

    text = ""
    model_used = ""
    try:
        text = await get_gemini_client().vision(
            _OCR_PROMPT, image_bytes, mime=mime, school_id=school_id, user_id=user_id, task="ocr",
        )
        model_used = model_for("vision", "gemini")
    except Exception as e:  # noqa: BLE001 — fall through to NVIDIA
        logger.warning("Gemini OCR failed, trying NVIDIA vision: %s", e)
        try:
            text = await get_nvidia_client().vision(
                _OCR_PROMPT, image_bytes, mime=mime, school_id=school_id, user_id=user_id, task="ocr",
            )
            model_used = "nvidia:vision"
        except Exception as e2:  # noqa: BLE001
            logger.error("NVIDIA OCR also failed: %s", e2)
            return ""

    text = (text or "").strip()
    if db is not None and doc_id is not None and page is not None and text:
        await _store_text(db, doc_id, page, model_used or "vision", text)
    return text
