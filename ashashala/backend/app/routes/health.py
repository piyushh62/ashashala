"""Health endpoint (moved out of main.py)."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.core.config import settings
from app.db.session import ping_db
from app.services.gemini_client import get_gemini_client
from app.services.nvidia_client import get_nvidia_client
from app.services.r2_client import get_storage_client
from app.services.rag.store import get_qdrant_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Health"])


async def _safe(coro) -> bool:
    try:
        return bool(await coro)
    except Exception as e:  # noqa: BLE001
        logger.warning("Health check error: %s", e)
        return False


@router.get("/health")
async def health() -> dict:
    checks = {
        "db": await _safe(ping_db()),
        "vector_db": await _safe(get_qdrant_store().health_check()),
        "r2": await _safe(get_storage_client().health_check()),
        "gemini": await _safe(get_gemini_client().health_check()),
        "nvidia_llm": await _safe(get_nvidia_client().health_check()),
    }
    checks["nvidia_ocr"] = checks["nvidia_llm"]  # same NVIDIA endpoint
    all_ok = all(checks.values())
    return {
        "status": "ok" if all_ok else "degraded",
        **{k: ("ok" if v else "error") for k, v in checks.items()},
        "version": settings.APP_VERSION,
    }
