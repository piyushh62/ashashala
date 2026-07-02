"""RAG ingestion — a TXT document is chunked, embedded, and stored."""

import pytest
from sqlalchemy import select

from app.db.tenant_filter import tenant_bypass
from app.models.document import Chunk, Document, DocStatus, SourceType
from app.services.ingestion import pipeline
from tests.conftest import make_school


async def _pending_doc(db, school_id: str, source_type=SourceType.txt, source_ref=None) -> Document:
    with tenant_bypass():
        doc = Document(school_id=school_id, class_id="c1", uploaded_by_teacher_id="t1",
                       filename="notes.txt", source_type=source_type, source_ref=source_ref,
                       status=DocStatus.pending)
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
    return doc


def _patch_pipeline(monkeypatch, session_factory):
    async def fake_embed(texts, lang, **kw):
        return [[0.0] * 768 for _ in texts], "gemini_768"

    class _Store:
        async def upsert_vectors(self, **kw):
            return len(kw.get("ids", []))

    monkeypatch.setattr(pipeline, "async_session_factory", session_factory)
    monkeypatch.setattr(pipeline, "embed_texts", fake_embed)
    monkeypatch.setattr(pipeline, "get_qdrant_store", lambda: _Store())


@pytest.mark.asyncio
async def test_txt_ingestion_indexes_and_chunks(db, session_factory, monkeypatch):
    school = await make_school(db)
    doc = await _pending_doc(db, school.id)
    _patch_pipeline(monkeypatch, session_factory)

    text = ("Photosynthesis is how plants make food. " * 60).encode()
    await pipeline.ingest_document(doc_id=doc.id, school_id=school.id, class_id="c1",
                                   subject_id=None, source_type=SourceType.txt, data=text)

    db.expire_all()
    refreshed = await db.get(Document, doc.id)
    assert refreshed.status == DocStatus.indexed

    chunks = (await db.execute(select(Chunk).where(Chunk.doc_id == doc.id))).scalars().all()
    assert len(chunks) >= 1
    assert all(c.vector_name == "gemini_768" for c in chunks)
