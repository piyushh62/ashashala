"""Best-effort persistence of LLM/embedding usage from any call path.

The provider clients call this so that EVERY external call — chat, streaming,
vision/OCR, embeddings, ASR, TTS — lands one `llm_usage` row, regardless of
whether it went through the router. Opens its own short-lived session (clients
are singletons without a request session) and never raises: usage accounting
must not break a student's answer.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.llm_usage import LlmUsage

logger = logging.getLogger(__name__)


async def record_llm_usage(
    *,
    provider: str,
    model_role: str,
    task: str,
    model_id: str | None = None,
    school_id: str | None = None,
    user_id: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: int = 0,
    status: str = "success",
    error_message: str | None = None,
) -> None:
    if settings.MOCK_EXTERNAL_SERVICES:
        return
    try:
        async with async_session_factory() as session:
            session.add(LlmUsage(
                provider=provider, model_role=model_role, model_id=model_id, task=task,
                school_id=school_id, user_id=user_id,
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                latency_ms=latency_ms, status=status,
                error_message=error_message[:2000] if error_message else None,
            ))
            await session.commit()
    except Exception as e:  # noqa: BLE001 — logging must never break the caller
        logger.warning("Failed to persist llm_usage row: %s", e)
