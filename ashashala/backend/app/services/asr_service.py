"""ASR (Automatic Speech Recognition) service using NVIDIA NIM."""

from __future__ import annotations

import base64
import logging
from typing import Optional

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.services.nvidia_client import get_nvidia_client

logger = logging.getLogger(__name__)


async def transcribe_audio(
    audio_bytes: bytes,
    content_type: str,
    language: str = "en",
    school_id: str | None = None,
    user_id: str | None = None,
) -> str:
    """
    Transcribe audio to text using NVIDIA ASR model.
    
    Args:
        audio_bytes: Raw audio data
        content_type: MIME type (e.g., "audio/wav", "audio/mp3", "audio/webm")
        language: Language hint (ISO 639-1 code)
        school_id: School ID for usage logging
        user_id: User ID for usage logging
        
    Returns:
        Transcribed text
        
    Raises:
        ExternalServiceError: On API errors
    """
    if settings.MOCK_EXTERNAL_SERVICES:
        return "[MOCK] Transcribed text from audio"
    
    client = get_nvidia_client()
    
    # Encode audio as base64 for the API
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    # NVIDIA ASR expects a specific format
    # Using the chat completions API with audio input
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Transcribe this audio to text. Language: {language}"},
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": audio_b64,
                        "format": content_type.split("/")[-1]  # e.g., "wav", "mp3", "webm"
                    }
                }
            ]
        }
    ]
    
    try:
        # Use the ASR role from model registry
        text = await client.chat(
            messages=messages,
            role="asr",
            school_id=school_id,
            user_id=user_id,
            task="asr",
        )
        return text.strip()
    except Exception as e:
        logger.error("ASR transcription failed: %s", e)
        raise ExternalServiceError("NVIDIA ASR", str(e))


async def health_check() -> bool:
    """Check if ASR service is accessible."""
    if settings.MOCK_EXTERNAL_SERVICES:
        return True
    try:
        client = get_nvidia_client()
        model_id = client._get_model_id("asr")
        if not model_id:
            return False
        # Simple health check - just verify model is configured
        return True
    except Exception as e:
        logger.error("ASR health check failed: %s", e)
        return False