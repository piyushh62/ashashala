"""YouTube ingestion — transcript timestamps survive into chunk metadata."""

import pytest
from sqlalchemy import select

from app.models.document import Chunk, Document, DocStatus, SourceType
from app.services.ingestion import extractors, pipeline
from app.services.rag.chunker import Segment
from tests.conftest import make_school
from tests.test_phase2_rag import _patch_pipeline, _pending_doc


def test_youtube_video_id_parsing():
    assert extractors.youtube_video_id("https://youtu.be/abcDEFghij1") == "abcDEFghij1"
    assert extractors.youtube_video_id("https://www.youtube.com/watch?v=abcDEFghij1") == "abcDEFghij1"


@pytest.mark.asyncio
async def test_youtube_ingestion_keeps_timestamps(db, session_factory, monkeypatch):
    school = await make_school(db)  # youtube feature defaults on
    doc = await _pending_doc(db, school.id, source_type=SourceType.youtube,
                             source_ref="https://youtu.be/abcDEFghij1")
    _patch_pipeline(monkeypatch, session_factory)

    monkeypatch.setattr(extractors, "extract_youtube", lambda url: [
        Segment(text="Intro to fractions " * 30, page_or_ts="0m5s"),
        Segment(text="Adding fractions " * 30, page_or_ts="1m24s"),
    ])

    await pipeline.ingest_document(doc_id=doc.id, school_id=school.id, class_id="c1",
                                   subject_id=None, source_type=SourceType.youtube,
                                   source_ref="https://youtu.be/abcDEFghij1")

    db.expire_all()
    assert (await db.get(Document, doc.id)).status == DocStatus.indexed
    chunks = (await db.execute(select(Chunk).where(Chunk.doc_id == doc.id))).scalars().all()
    stamps = {c.page_or_ts for c in chunks}
    assert "0m5s" in stamps and "1m24s" in stamps
