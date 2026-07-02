import asyncio
import logging
import time
from collections import defaultdict
from typing import Any

from openai import AsyncOpenAI
from openai import RateLimitError, APITimeoutError, APIError

from app.core.config import settings
from app.services.model_registry import model_for

logger = logging.getLogger(__name__)


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
            raise ExternalServiceError("NVIDIA Embeddings", str(e))
    
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
        """Log LLM usage. Fire-and-forget to stdout; router handles DB."""
        logger.info(
            "LLM_USAGE: provider=%s role=%s model=%s task=%s "
            "prompt_tokens=%d completion_tokens=%d latency_ms=%d "
            "school_id=%s user_id=%s status=%s error=%s",
            provider, model_role, model_id, task,
            prompt_tokens, completion_tokens, latency_ms,
            school_id, user_id, status, error_msg or "none"
        )


# Singleton instance
_nvidia_client: NVIDIAClient | None = None


def get_nvidia_client() -> NVIDIAClient:
    global _nvidia_client
    if _nvidia_client is None:
        _nvidia_client = NVIDIAClient()
    return _nvidia_client