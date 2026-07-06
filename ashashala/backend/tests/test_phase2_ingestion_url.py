"""URL ingestion — trafilatura output is chunked and indexed."""

import pytest
from sqlalchemy import select

from app.models.document import Chunk, Document, DocStatus, SourceType
from app.services.ingestion import extractors, pipeline
from app.services.rag.chunker import Segment
from tests.conftest import make_school
from tests.test_phase2_rag import _patch_pipeline, _pending_doc


@pytest.mark.asyncio
async def test_url_ingestion(db, session_factory, monkeypatch):
    school = await make_school(db)
    doc = await _pending_doc(db, school.id, source_type=SourceType.url, source_ref="https://ex.com/a")
    _patch_pipeline(monkeypatch, session_factory)

    monkeypatch.setattr(
        extractors, "extract_url",
        lambda ref, **kw: [Segment(text="The water cycle moves water around the Earth. " * 40, page_or_ts=None)],
    )

    doc_id = doc.id
    await pipeline.ingest_document(doc_id=doc_id, school_id=school.id, class_id="c1",
                                   subject_id=None, source_type=SourceType.url,
                                   source_ref="https://ex.com/a")

    db.expire_all()
    assert (await db.get(Document, doc_id)).status == DocStatus.indexed
    chunks = (await db.execute(select(Chunk).where(Chunk.doc_id == doc_id))).scalars().all()
    assert len(chunks) >= 1
