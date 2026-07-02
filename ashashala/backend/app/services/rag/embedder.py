"""Embedding router for RAG.

English -> Gemini text-embedding-004 (768). Indic -> NVIDIA nv-embedqa-e5-v5
(1024). Returns the vectors AND the Qdrant named-vector space they belong to,
so ingestion/retrieval upsert/query the matching space.
"""

from __future__ import annotations

from app.services.gemini_client import get_gemini_client
from app.services.nvidia_client import get_nvidia_client
from app.services.rag.store import VECTOR_GEMINI, vector_name_for_lang


async def embed_texts(
    texts: list[str],
    lang: str,
    school_id: str | None = None,
    user_id: str | None = None,
) -> tuple[list[list[float]], str]:
    """Return (vectors, vector_name) for the given language."""
    vector_name = vector_name_for_lang(lang)
    if vector_name == VECTOR_GEMINI:
        vectors = await get_gemini_client().embed(texts, school_id=school_id, user_id=user_id)
    else:
        vectors = await get_nvidia_client().embed(
            texts, role="embeddings", school_id=school_id, user_id=user_id
        )
    return vectors, vector_name
