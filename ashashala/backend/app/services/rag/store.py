"""Qdrant vector store — one collection per school, NAMED vectors per provider.

Because English embeds with Gemini (768 dims) and Indic with NVIDIA (1024 dims),
a single unnamed vector can't hold both. Each school collection therefore has two
named vector spaces:
    - "gemini_768"  : 768-dim, Cosine  (English / text-embedding-004)
    - "nvidia_1024" : 1024-dim, Cosine (Indic / nv-embedqa-e5-v5)
Retrieval queries the space that matches the query language.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    NamedVector,
    PointStruct,
    VectorParams,
)
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

VECTOR_GEMINI = "gemini_768"
VECTOR_NVIDIA = "nvidia_1024"

VECTOR_SPACES = {
    VECTOR_GEMINI: VectorParams(size=768, distance=Distance.COSINE),
    VECTOR_NVIDIA: VectorParams(size=1024, distance=Distance.COSINE),
}


def vector_name_for_lang(lang: str) -> str:
    """English -> Gemini space; every Indic language -> NVIDIA space."""
    return VECTOR_GEMINI if lang == "en" else VECTOR_NVIDIA


class QdrantStore:
    def __init__(self):
        if not settings.QDRANT_URL:
            raise RuntimeError("QDRANT_URL not set in environment")
        self.client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=settings.QDRANT_TIMEOUT,
        )
        self._collection_cache: set[str] = set()

    def _collection_name(self, school_id: str) -> str:
        return f"school_{school_id}"

    async def ensure_collection(self, school_id: str) -> None:
        """Create the per-school collection (both named vectors) if absent."""
        name = self._collection_name(school_id)
        if name in self._collection_cache:
            return
        try:
            await self.client.get_collection(name)
            self._collection_cache.add(name)
        except (UnexpectedResponse, ValueError):
            await self.client.create_collection(
                collection_name=name, vectors_config=dict(VECTOR_SPACES)
            )
            self._collection_cache.add(name)
            logger.info("Created Qdrant collection %s with named vectors", name)

    async def upsert_vectors(
        self,
        school_id: str,
        vectors: list[list[float]],
        payloads: list[dict],
        vector_name: str,
        ids: list[str],
    ) -> int:
        """Upsert points into a specific named vector space."""
        await self.ensure_collection(school_id)
        points = [
            PointStruct(id=pid, vector={vector_name: vec}, payload=payload)
            for pid, vec, payload in zip(ids, vectors, payloads)
        ]
        await self.client.upsert(collection_name=self._collection_name(school_id), points=points)
        return len(points)

    async def search(
        self,
        school_id: str,
        query_vector: list[float],
        vector_name: str,
        limit: int = 20,
        score_threshold: float | None = None,
        filter_conditions: dict | None = None,
    ) -> list[dict]:
        """Top-k search in one named vector space, filtered by payload (class_id)."""
        await self.ensure_collection(school_id)
        qdrant_filter = None
        if filter_conditions:
            qdrant_filter = Filter(must=[
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_conditions.items()
            ])
        results = await self.client.search(
            collection_name=self._collection_name(school_id),
            query_vector=NamedVector(name=vector_name, vector=query_vector),
            limit=limit,
            score_threshold=score_threshold,
            query_filter=qdrant_filter,
            with_payload=True,
        )
        return [{"id": h.id, "score": h.score, "payload": h.payload} for h in results]

    async def delete_by_doc(self, school_id: str, doc_id: str) -> None:
        """Delete every point belonging to a document."""
        await self.ensure_collection(school_id)
        await self.client.delete(
            collection_name=self._collection_name(school_id),
            points_selector=Filter(must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]),
        )

    async def get_collection_info(self, school_id: str) -> dict | None:
        try:
            info = await self.client.get_collection(self._collection_name(school_id))
            return {"points_count": info.points_count, "status": str(info.status)}
        except (UnexpectedResponse, ValueError):
            return None

    async def health_check(self) -> bool:
        if settings.MOCK_EXTERNAL_SERVICES:
            return True
        try:
            await self.client.get_collections()
            return True
        except Exception as e:  # noqa: BLE001
            logger.error("Qdrant health check failed: %s", e)
            return False


_qdrant_store: QdrantStore | None = None


def get_qdrant_store() -> QdrantStore:
    global _qdrant_store
    if _qdrant_store is None:
        _qdrant_store = QdrantStore()
    return _qdrant_store


@asynccontextmanager
async def qdrant_store_context() -> AsyncGenerator[QdrantStore, None]:
    yield get_qdrant_store()
