"""TTS (text-to-speech) — server-side fallback for spoken tutor answers.

The browser SpeechSynthesis API is the primary path (see the frontend); this
endpoint is the fallback. Delegates to the NVIDIA client's speech endpoint,
which logs usage to `llm_usage` and raises ExternalServiceError when TTS isn't
available — the frontend then falls back to browser speech.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.services.nvidia_client import _SILENT_WAV, get_nvidia_client

logger = logging.getLogger(__name__)


async def synthesize_speech(
    text: str,
    language: str = "en",
    voice: str = "default",
    school_id: str | None = None,
    user_id: str | None = None,
) -> bytes:
    """Return WAV audio bytes for `text`. Raises ExternalServiceError on failure."""
    if settings.MOCK_EXTERNAL_SERVICES:
        return _SILENT_WAV

    return await get_nvidia_client().synthesize(
        text=text, voice=voice, language=language,
        school_id=school_id, user_id=user_id,
    )


async def health_check() -> bool:
    """TTS is available when a TTS model id is configured in the registry."""
    if settings.MOCK_EXTERNAL_SERVICES:
        return True
    try:
        return bool(get_nvidia_client()._get_model_id("tts"))
    except Exception as e:  # noqa: BLE001
        logger.error("TTS health check failed: %s", e)
        return False
