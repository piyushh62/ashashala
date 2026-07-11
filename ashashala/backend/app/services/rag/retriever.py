"""Retrieval — top-k similarity filtered by class_id (the security boundary).

The class_id payload filter is what stops a student seeing another class's
material; the per-school collection stops cross-school access. Always pass
class_id.
"""

from __future__ import annotations

from app.services.rag.embedder import embed_texts
from app.services.rag.store import get_qdrant_store


async def retrieve(
    *,
    school_id: str,
    class_id: str,
    query: str,
    lang: str = "en",
    subject_id: str | None = None,
    doc_id: str | None = None,
    limit: int = 20,
    score_threshold: float | None = None,
) -> list[dict]:
    vectors, vector_name = await embed_texts([query], lang, school_id=school_id)
    filters: dict = {"class_id": class_id}
    if subject_id:
        filters["subject_id"] = subject_id
    if doc_id:
        # Strict single-document grounding (e.g. "generate a quiz from this
        # material") — chunks already carry a doc_id payload field (see
        # store.delete_by_doc), so this is just one more equality filter.
        filters["doc_id"] = doc_id
    return await get_qdrant_store().search(
        school_id=school_id,
        query_vector=vectors[0],
        vector_name=vector_name,
        limit=limit,
        score_threshold=score_threshold,
        filter_conditions=filters,
    )
