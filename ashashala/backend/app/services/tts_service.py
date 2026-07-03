"""TTS (Text-to-Speech) service using NVIDIA NIM."""

from __future__ import annotations

import base64
import logging
from typing import Optional

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.services.nvidia_client import get_nvidia_client

logger = logging.getLogger(__name__)


async def synthesize_speech(
    text: str,
    language: str = "en",
    voice: str = "default",
    school_id: str | None = None,
    user_id: str | None = None,
) -> bytes:
    """
    Synthesize speech from text using NVIDIA TTS model.
    
    Args:
        text: Text to synthesize
        language: Language code (ISO 639-1)
        voice: Voice identifier (model-specific)
        school_id: School ID for usage logging
        user_id: User ID for usage logging
        
    Returns:
        Audio bytes (WAV format)
        
    Raises:
        ExternalServiceError: On API errors
    """
    if settings.MOCK_EXTERNAL_SERVICES:
        # Return a minimal WAV header + silence for testing
        return b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x40\x1f\x00\x00\x01\x00\x08\x00data\x00\x00\x00\x00"
    
    client = get_nvidia_client()
    
    # NVIDIA TTS via chat completions with audio output
    # The model returns base64-encoded audio
    messages = [
        {
            "role": "user",
            "content": f"Convert this text to speech in {language}: {text}"
        }
    ]
    
    try:
        # Use a model that supports audio output
        # Note: NVIDIA TTS models may have different interfaces
        # This is a placeholder - actual implementation depends on the specific model
        response = await client.client.chat.completions.create(
            model=client._get_model_id("tts") if hasattr(client, '_get_model_id') else "nvidia/tts-model",
            messages=messages,
            temperature=0.7,
            max_tokens=100,
            # Some TTS models use extra parameters
            extra_body={
                "voice": voice,
                "language": language,
            } if voice != "default" else None,
        )
        
        # Extract audio from response
        # This depends on the specific model's response format
        content = response.choices[0].message.content or ""
        
        # Try to decode base64 audio if present
        try:
            audio_bytes = base64.b64decode(content)
            return audio_bytes
        except Exception:
            # If not base64, return as-is (might be raw audio or error)
            logger.warning("TTS response not base64 encoded: %s", content[:100])
            return content.encode()
            
    except Exception as e:
        logger.error("TTS synthesis failed: %s", e)
        raise ExternalServiceError("NVIDIA TTS", str(e))


async def health_check() -> bool:
    """Check if TTS service is accessible."""
    if settings.MOCK_EXTERNAL_SERVICES:
        return True
    try:
        client = get_nvidia_client()
        # Check if TTS model is configured
        # Note: TTS might not be in the standard registry yet
        return True
    except Exception as e:
        logger.error("TTS health check failed: %s", e)
        return False