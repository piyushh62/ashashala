"""OCR ingestion — a phone-photo/image upload is OCR'd, chunked, and cached.

Mirrors the RAG ingestion test harness (patched embed + Qdrant + session
factory). Under MOCK_EXTERNAL_SERVICES the vision OCR returns deterministic
mock text, so we can assert the full image → OcrCache → chunk path.
"""

import pytest
from sqlalchemy import select

from app.db.tenant_filter import tenant_bypass
from app.models.document import Chunk, Document, DocStatus, OcrCache, SourceType
from app.services.ingestion import pipeline
from tests.conftest import make_school
from tests.test_phase2_rag import _patch_pipeline


async def _image_doc(db, school_id: str) -> Document:
    with tenant_bypass():
        doc = Document(school_id=school_id, class_id="c1", uploaded_by_teacher_id="t1",
                       filename="notes.jpg", source_type=SourceType.image,
                       status=DocStatus.pending)
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
    return doc


@pytest.mark.asyncio
async def test_image_ingestion_ocrs_and_caches(db, session_factory, monkeypatch):
    school = await make_school(db, ocr=True)
    doc = await _image_doc(db, school.id)
    doc_id = doc.id
    _patch_pipeline(monkeypatch, session_factory)

    await pipeline.ingest_document(
        doc_id=doc_id, school_id=school.id, class_id="c1", subject_id=None,
        source_type=SourceType.image, data=b"\x89PNG fake image bytes",
        content_type="image/png",
    )

    db.expire_all()
    refreshed = await db.get(Document, doc_id)
    assert refreshed.status == DocStatus.indexed

    chunks = (await db.execute(select(Chunk).where(Chunk.doc_id == doc_id))).scalars().all()
    assert len(chunks) >= 1

    # OCR result is cached forever, keyed by (doc_id, page).
    cache = await db.get(OcrCache, (doc_id, 1))
    assert cache is not None
    assert cache.text.strip() != ""
