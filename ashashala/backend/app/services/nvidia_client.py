import asyncio
import base64
import logging
import time
from collections import defaultdict
from collections.abc import AsyncIterator

from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.core.config import settings
from app.services.model_registry import function_id_for, model_for

logger = logging.getLogger(__name__)

# Minimal valid WAV (44-byte header + silence) returned in mock mode.
_SILENT_WAV = (
    b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
    b"\x40\x1f\x00\x00\x40\x1f\x00\x00\x01\x00\x08\x00data\x00\x00\x00\x00"
)


def _pcm16_to_wav(pcm_bytes: bytes, *, sample_rate_hz: int, channels: int = 1) -> bytes:
    """Wrap raw 16-bit PCM samples in a WAV container."""
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)  # 16-bit
        w.setframerate(sample_rate_hz)
        w.writeframes(pcm_bytes)
    return buf.getvalue()


class NVIDIAClient:
    """NVIDIA NIM client using OpenAI-compatible SDK.

    Features:
    - Per-model rate limiting (NVIDIA free tier: ~40 req/min)
    - Retry with exponential backoff
    - Timeout handling
    - Usage logging
    """

    def __init__(self):
        if not settings.NVIDIA_API_KEY:
            raise RuntimeError("NVIDIA_API_KEY not set in environment")

        self.client = AsyncOpenAI(
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_BASE_URL,
            timeout=settings.NVIDIA_TIMEOUT,
        )

        # Per-model rate limiting (requests per minute)
        # NVIDIA free tier: ~40 req/min across all models
        self._rate_limits: dict[str, int] = defaultdict(lambda: 40)
        self._request_times: dict[str, list[float]] = defaultdict(list)
        self._rate_limit_lock = asyncio.Lock()

    def _get_model_id(self, role: str) -> str:
        """Get model ID for role, preferring primary over fallback."""
        try:
            return model_for(role, "nvidia")
        except RuntimeError:
            # Try fallback explicitly
            registry = __import__("app.services.model_registry", fromlist=["get_registry"]).get_registry()
            role_config = registry.get(role, {})
            return role_config.get("nvidia_fallback", "") or role_config.get("nvidia_primary", "")

    async def _check_rate_limit(self, model_id: str) -> None:
        """Enforce per-model rate limit."""
        async with self._rate_limit_lock:
            now = time.time()
            limit = self._rate_limits.get(model_id, 40)

            # Clean old requests (> 60 seconds)
            self._request_times[model_id] = [
                t for t in self._request_times[model_id] if now - t < 60
            ]

            if len(self._request_times[model_id]) >= limit:
                # Wait until oldest request expires
                oldest = self._request_times[model_id][0]
                wait_time = 60 - (now - oldest) + 0.1
                if wait_time > 0:
                    logger.debug("Rate limit reached for %s, waiting %.1fs", model_id, wait_time)
                    await asyncio.sleep(wait_time)

            self._request_times[model_id].append(now)

    async def chat(
        self,
        messages: list[dict[str, str]],
        role: str,
        school_id: str | None = None,
        user_id: str | None = None,
        task: str = "chat",
        model_id: str | None = None,
        **kwargs,
    ) -> str:
        """Send chat messages to NVIDIA NIM with rate limiting and retry.

        Args:
            messages: List of {"role": "user|assistant|system", "content": text}
            role: Model role from registry
            school_id: School ID for usage logging
            user_id: User ID for usage logging
            task: Task name for logging
            **kwargs: Additional generation config (temperature, max_tokens, etc.)

        Returns:
            Response text

        Raises:
            ExternalServiceError: On API errors after retries exhausted
        """
        if settings.MOCK_EXTERNAL_SERVICES:
            return "[MOCK] nvidia response"

        # model_id override lets the router force a specific model (e.g. the
        # Indic Maverick fallback) without a separate registry role.
        model_id = model_id or self._get_model_id(role)
        if not model_id:
            from app.core.exceptions import ExternalServiceError
            raise ExternalServiceError("NVIDIA", f"No model configured for role={role}")

        await self._check_rate_limit(model_id)

        start_time = time.perf_counter()
        last_error = None

        for attempt in range(3):  # 3 attempts = 2 retries
            try:
                response = await self.client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    temperature=kwargs.get("temperature", 0.7),
                    max_tokens=kwargs.get("max_tokens", 8192),
                    top_p=kwargs.get("top_p", 0.95),
                )

                latency_ms = int((time.perf_counter() - start_time) * 1000)
                text = response.choices[0].message.content or ""

                # Log usage
                await self._log_usage(
                    provider="nvidia",
                    model_role=role,
                    model_id=model_id,
                    task=task,
                    prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                    completion_tokens=response.usage.completion_tokens if response.usage else 0,
                    latency_ms=latency_ms,
                    school_id=school_id,
                    user_id=user_id,
                    status="success",
                )

                logger.debug(
                    "NVIDIA call succeeded: role=%s, model=%s, latency=%dms, tokens=%d",
                    role, model_id, latency_ms,
                    (response.usage.prompt_tokens if response.usage else 0) +
                    (response.usage.completion_tokens if response.usage else 0)
                )

                return text

            except RateLimitError as e:
                last_error = f"Rate limited: {e}"
                logger.warning("NVIDIA rate limited (attempt %d/3): role=%s", attempt + 1, role)

            except APITimeoutError as e:
                last_error = f"Timeout: {e}"
                logger.warning("NVIDIA timeout (attempt %d/3): role=%s", attempt + 1, role)

            except APIError as e:
                last_error = f"API error: {e}"
                logger.error("NVIDIA API error (attempt %d/3): role=%s, error=%s", attempt + 1, role, e)

            except Exception as e:
                last_error = f"Unexpected error: {e}"
                logger.exception("NVIDIA unexpected error (attempt %d/3): role=%s", attempt + 1, role)

            # Exponential backoff with jitter: 1s, 2s, 4s
            if attempt < 2:
                wait_time = (2 ** attempt) + (0.1 * attempt)
                await asyncio.sleep(wait_time)

        # All retries exhausted
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        await self._log_usage(
            provider="nvidia",
            model_role=role,
            model_id=model_id,
            task=task,
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=latency_ms,
            school_id=school_id,
            user_id=user_id,
            status="error",
            error_msg=last_error,
        )

        from app.core.exceptions import ExternalServiceError
        raise ExternalServiceError("NVIDIA", last_error or "Max retries exceeded")

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        role: str,
        school_id: str | None = None,
        user_id: str | None = None,
        task: str = "chat",
        model_id: str | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream response text deltas from NVIDIA NIM (OpenAI-compatible SSE)."""
        if settings.MOCK_EXTERNAL_SERVICES:
            for piece in ("[MOCK] ", "streamed ", "nvidia ", "response."):
                yield piece
            return

        model_id = model_id or self._get_model_id(role)
        if not model_id:
            from app.core.exceptions import ExternalServiceError
            raise ExternalServiceError("NVIDIA", f"No model configured for role={role}")
        await self._check_rate_limit(model_id)

        start_time = time.perf_counter()
        try:
            stream = await self.client.chat.completions.create(
                model=model_id, messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 8192),
                top_p=kwargs.get("top_p", 0.95),
                stream=True,
            )
        except Exception as e:
            from app.core.exceptions import ExternalServiceError
            raise ExternalServiceError("NVIDIA", f"stream open failed: {e}") from e

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

        await self._log_usage(
            provider="nvidia", model_role=role, model_id=model_id, task=task,
            prompt_tokens=0, completion_tokens=0,
            latency_ms=int((time.perf_counter() - start_time) * 1000),
            school_id=school_id, user_id=user_id, status="success",
        )

    async def vision(
        self,
        prompt: str,
        image_bytes: bytes,
        mime: str = "image/png",
        role: str = "vision",
        school_id: str | None = None,
        user_id: str | None = None,
        task: str = "vision",
        **kwargs,
    ) -> str:
        """Send an image + text prompt to a NVIDIA vision-language model.

        Used as the OCR fallback: a VLM reading text off a scanned/photographed
        page is robust and uses a catalog-verified model. Image is passed as a
        base64 data URI per the OpenAI-compatible vision schema.
        """
        if settings.MOCK_EXTERNAL_SERVICES:
            return "[MOCK] extracted text from image"

        b64 = base64.b64encode(image_bytes).decode("utf-8")
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }]
        return await self.chat(messages, role=role, school_id=school_id,
                               user_id=user_id, task=task, **kwargs)

    # Riva TTS default voice per its NVCF-hosted model (community-documented
    # defaults; re-check available voices with SpeechSynthesisService.get_config()
    # before adding new languages — non-English voice IDs are not yet confirmed).
    _RIVA_VOICE = {
        "magpie": "Magpie-Multilingual.EN-US.Ray",
        "fastpitch": "English-US.Female-1",
    }

    def _riva_auth(self, function_id: str):
        import riva.client

        return riva.client.Auth(
            None, True, "grpc.nvcf.nvidia.com:443",
            [["function-id", function_id], ["authorization", f"Bearer {settings.NVIDIA_API_KEY}"]],
        )

    def _riva_synthesize_sync(self, text: str, function_id: str, voice: str, language: str) -> bytes:
        """Blocking Riva gRPC call — run via asyncio.to_thread from synthesize().
        Returns 16-bit mono PCM wrapped in a WAV container (wave module, not a
        speculative riva.client helper — LINEAR_PCM is exactly that format)."""
        import riva.client

        sample_rate = 22050
        service = riva.client.SpeechSynthesisService(self._riva_auth(function_id))
        resp = service.synthesize(
            text=text, voice_name=voice, language_code=language,
            encoding=riva.client.AudioEncoding.LINEAR_PCM, sample_rate_hz=sample_rate,
        )
        return _pcm16_to_wav(resp.audio, sample_rate_hz=sample_rate)

    async def synthesize(
        self,
        text: str,
        voice: str = "default",
        language: str = "en",
        school_id: str | None = None,
        user_id: str | None = None,
    ) -> bytes:
        """Text-to-speech via NVIDIA's Riva gRPC endpoint (NVCF-hosted, addressed
        by function-id — not the OpenAI REST API used elsewhere in this client).
        Tries the multilingual model first, then the English-only fallback.
        Raises ExternalServiceError if both fail, so the caller (and frontend)
        can fall back to browser SpeechSynthesis."""
        if settings.MOCK_EXTERNAL_SERVICES:
            return _SILENT_WAV

        from app.services.model_registry import get_registry
        tts_cfg = get_registry().get("tts", {})

        attempts = [
            ("magpie", tts_cfg.get("nvidia_primary", ""), function_id_for("tts")),
        ]
        try:
            attempts.append((
                "fastpitch", tts_cfg.get("nvidia_fallback", ""),
                function_id_for("tts", fallback=True),
            ))
        except Exception:  # noqa: BLE001 — fallback function_id optional
            pass

        last_error: Exception | None = None
        start_time = time.perf_counter()
        for label, model_id, function_id in attempts:
            try:
                voice_name = voice if voice != "default" else self._RIVA_VOICE.get(label, self._RIVA_VOICE["fastpitch"])
                audio = await asyncio.to_thread(self._riva_synthesize_sync, text, function_id, voice_name, language)
                await self._log_usage(
                    provider="nvidia", model_role="tts", model_id=model_id, task="tts",
                    prompt_tokens=len(text.split()), completion_tokens=0,
                    latency_ms=int((time.perf_counter() - start_time) * 1000),
                    school_id=school_id, user_id=user_id, status="success",
                )
                return audio
            except Exception as e:  # noqa: BLE001 — try the next voice, then give up
                last_error = e
                logger.warning("Riva TTS failed for %s: %s", label, e)

        await self._log_usage(
            provider="nvidia", model_role="tts", model_id=None, task="tts",
            prompt_tokens=len(text.split()), completion_tokens=0,
            latency_ms=int((time.perf_counter() - start_time) * 1000),
            school_id=school_id, user_id=user_id, status="error", error_msg=str(last_error),
        )
        from app.core.exceptions import ExternalServiceError
        raise ExternalServiceError("NVIDIA TTS", str(last_error) or "Riva synthesis failed")

    async def jailbreak_score(self, embedding: list[float]) -> bool:
        """NeMo-Guard jailbreak classifier. Consumes a pre-computed embedding
        (PROJECT_PROMPT §7) and returns True if the message is a jailbreak/
        prompt-injection attempt. Raises on any transport error (caller decides
        whether to fail open).

        Hosted on a different host/path (ai.api.nvidia.com/v1/security/...)
        than the OpenAI-compatible chat/embeddings base URL this client's SDK
        object is bound to, so this uses a plain httpx call instead of
        self.client.
        """
        import httpx

        model_id = self._get_model_id("safety_jailbreak")
        if not model_id:
            raise RuntimeError("safety_jailbreak model not configured")
        await self._check_rate_limit(model_id)

        async with httpx.AsyncClient(timeout=settings.NVIDIA_TIMEOUT) as http:
            resp = await http.post(
                f"https://ai.api.nvidia.com/v1/security/{model_id}",
                headers={"Authorization": f"Bearer {settings.NVIDIA_API_KEY}"},
                json={"input": embedding},
            )
            resp.raise_for_status()
            data = resp.json()
        # Response shape: {"jailbreak": true/false, "score": 0..1}
        return bool(data.get("jailbreak") or (data.get("score", 0) or 0) >= 0.5)

    async def embed(
        self,
        texts: list[str],
        role: str = "embeddings",
        school_id: str | None = None,
        user_id: str | None = None,
    ) -> list[list[float]]:
        """Generate embeddings using NVIDIA embedding model."""
        model_id = self._get_model_id(role)
        if not model_id:
            from app.core.exceptions import ExternalServiceError
            raise ExternalServiceError("NVIDIA", f"No embedding model configured for role={role}")

        await self._check_rate_limit(model_id)

        start_time = time.perf_counter()
        try:
            response = await self.client.embeddings.create(
                model=model_id,
                input=texts,
            )

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            embeddings = [d.embedding for d in response.data]

            await self._log_usage(
                provider="nvidia",
                model_role=role,
                model_id=model_id,
                task="embedding",
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=0,
                latency_ms=latency_ms,
                school_id=school_id,
                user_id=user_id,
                status="success",
            )

            return embeddings

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            await self._log_usage(
                provider="nvidia",
                model_role=role,
                model_id=model_id,
                task="embedding",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=latency_ms,
                school_id=school_id,
                user_id=user_id,
                status="error",
                error_msg=str(e),
            )
            from app.core.exceptions import ExternalServiceError
            raise ExternalServiceError("NVIDIA Embeddings", str(e)) from e

    async def health_check(self) -> bool:
        """Check if NVIDIA API is accessible."""
        if settings.MOCK_EXTERNAL_SERVICES:
            return True
        try:
            model_id = self._get_model_id("fast_chat")
            if not model_id:
                return False

            await self.client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True
        except Exception as e:
            logger.error("NVIDIA health check failed: %s", e)
            return False

    async def _log_usage(
        self,
        provider: str,
        model_role: str,
        model_id: str,
        task: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        school_id: str | None,
        user_id: str | None,
        status: str,
        error_msg: str | None = None,
    ) -> None:
        """Persist one usage row (best-effort) and echo to logs. Covers every
        NVIDIA path — chat, streaming, vision/OCR, embeddings, ASR, TTS."""
        logger.info(
            "LLM_USAGE: provider=%s role=%s model=%s task=%s "
            "prompt_tokens=%d completion_tokens=%d latency_ms=%d "
            "school_id=%s user_id=%s status=%s error=%s",
            provider, model_role, model_id, task,
            prompt_tokens, completion_tokens, latency_ms,
            school_id, user_id, status, error_msg or "none"
        )
        from app.services.usage import record_llm_usage
        await record_llm_usage(
            provider=provider, model_role=model_role, model_id=model_id, task=task,
            school_id=school_id, user_id=user_id, prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens, latency_ms=latency_ms,
            status=status, error_message=error_msg,
        )


# Singleton instance
_nvidia_client: NVIDIAClient | None = None


def get_nvidia_client() -> NVIDIAClient:
    global _nvidia_client
    if _nvidia_client is None:
        _nvidia_client = NVIDIAClient()
    return _nvidia_client
