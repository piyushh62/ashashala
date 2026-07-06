"""ASR (speech-to-text) — server-side fallback for the student voice input.

The browser Web Speech API is the primary path (see the frontend); this endpoint
is the fallback when the browser lacks it. Implemented with Gemini audio
transcription: `gemini-2.5-flash` accepts audio parts, giving a real, free STT
path. (PROJECT_PROMPT assigns ASR to NVIDIA, but the OpenAI-compatible NVIDIA
endpoint doesn't cleanly expose ASR; Gemini audio is the reliable free option.)

Usage is logged to the `llm_usage` table by the Gemini client on every call.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.services.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)


async def transcribe_audio(
    audio_bytes: bytes,
    content_type: str,
    language: str = "en",
    school_id: str | None = None,
    user_id: str | None = None,
) -> str:
    """Transcribe uploaded audio to text. Raises ExternalServiceError on failure."""
    if settings.MOCK_EXTERNAL_SERVICES:
        return "[MOCK] Transcribed text from audio"

    mime = content_type if content_type.startswith("audio/") else "audio/wav"
    try:
        return await get_gemini_client().transcribe(
            audio_bytes, mime=mime, language=language,
            school_id=school_id, user_id=user_id,
        )
    except Exception as e:  # noqa: BLE001
        logger.error("ASR transcription failed: %s", e)
        raise ExternalServiceError("ASR", str(e)) from e


async def health_check() -> bool:
    """ASR is available whenever the Gemini vision/audio model is configured."""
    if settings.MOCK_EXTERNAL_SERVICES:
        return True
    try:
        from app.services.model_registry import model_for
        return bool(model_for("vision", "gemini"))
    except Exception as e:  # noqa: BLE001
        logger.error("ASR health check failed: %s", e)
        return False
