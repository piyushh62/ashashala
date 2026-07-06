"""Voice services — ASR transcription and TTS synthesis (mock-mode)."""

import pytest

from app.services.asr_service import transcribe_audio
from app.services.asr_service import health_check as asr_health
from app.services.tts_service import synthesize_speech
from app.services.tts_service import health_check as tts_health


@pytest.mark.asyncio
async def test_transcribe_audio_returns_text():
    text = await transcribe_audio(b"fake-audio", content_type="audio/webm", language="en")
    assert isinstance(text, str) and text.strip() != ""


@pytest.mark.asyncio
async def test_synthesize_speech_returns_wav_bytes():
    audio = await synthesize_speech("Hello there", language="en")
    assert isinstance(audio, (bytes, bytearray))
    assert audio[:4] == b"RIFF"  # valid WAV container


@pytest.mark.asyncio
async def test_voice_health_checks():
    assert await asr_health() is True
    assert await tts_health() is True
