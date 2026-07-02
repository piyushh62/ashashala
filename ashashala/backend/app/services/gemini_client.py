import asyncio
import logging
import time
from typing import Any

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from google.generativeai.types import HarmBlockThreshold, HarmCategory

from app.core.config import settings
from app.services.model_registry import model_for

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini API client with retry, backoff, timeout, and usage logging."""
    
    # Safety settings — allow educational content, block only severe harm
    SAFETY_SETTINGS = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }
    
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not set in environment")
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model_cache: dict[str, genai.GenerativeModel] = {}
    
    def _get_model(self, role: str) -> genai.GenerativeModel:
        """Get or create a GenerativeModel for the given role."""
        if role not in self._model_cache:
            model_id = model_for(role, "gemini")
            self._model_cache[role] = genai.GenerativeModel(
                model_id,
                safety_settings=self.SAFETY_SETTINGS,
            )
        return self._model_cache[role]
    
    async def chat(
        self,
        messages: list[dict[str, str]],
        role: str,
        school_id: str | None = None,
        user_id: str | None = None,
        task: str = "chat",
        **kwargs,
    ) -> str:
        """Send chat messages to Gemini with retry and timeout.
        
        Args:
            messages: List of {"role": "user|model", "parts": [text]} or similar
            role: Model role from registry (fast_chat, reasoning, vision, etc.)
            school_id: School ID for usage logging
            user_id: User ID for usage logging
            task: Task name for logging
            **kwargs: Additional generation config
            
        Returns:
            Response text
            
        Raises:
            ExternalServiceError: On API errors after retries exhausted
        """
        model = self._get_model(role)
        model_id = model_for(role, "gemini")
        
        # Convert messages to Gemini format
        gemini_messages = self._convert_messages(messages)
        
        start_time = time.perf_counter()
        last_error = None
        
        for attempt in range(3):  # 3 attempts = 2 retries
            try:
                # Apply timeout
                response = await asyncio.wait_for(
                    model.generate_content_async(
                        gemini_messages,
                        generation_config=genai.GenerationConfig(
                            temperature=kwargs.get("temperature", 0.7),
                            max_output_tokens=kwargs.get("max_tokens", 8192),
                            top_p=kwargs.get("top_p", 0.95),
                            top_k=kwargs.get("top_k", 40),
                        ),
                    ),
                    timeout=settings.GEMINI_TIMEOUT,
                )
                
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                
                # Extract text
                text = response.text if response.text else ""
                
                # Log usage
                await self._log_usage(
                    provider="gemini",
                    model_role=role,
                    model_id=model_id,
                    task=task,
                    prompt_tokens=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                    completion_tokens=response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                    latency_ms=latency_ms,
                    school_id=school_id,
                    user_id=user_id,
                    status="success",
                )
                
                logger.debug(
                    "Gemini call succeeded: role=%s, model=%s, latency=%dms, tokens=%d",
                    role, model_id, latency_ms,
                    (response.usage_metadata.prompt_token_count if response.usage_metadata else 0) +
                    (response.usage_metadata.candidates_token_count if response.usage_metadata else 0)
                )
                
                return text
                
            except asyncio.TimeoutError:
                last_error = f"Timeout after {settings.GEMINI_TIMEOUT}s"
                logger.warning("Gemini timeout (attempt %d/3): role=%s", attempt + 1, role)
                
            except google_exceptions.ResourceExhausted as e:
                last_error = f"Rate limited: {e}"
                logger.warning("Gemini rate limited (attempt %d/3): role=%s", attempt + 1, role)
                
            except google_exceptions.GoogleAPIError as e:
                last_error = f"API error: {e}"
                logger.error("Gemini API error (attempt %d/3): role=%s, error=%s", attempt + 1, role, e)
                
            except Exception as e:
                last_error = f"Unexpected error: {e}"
                logger.exception("Gemini unexpected error (attempt %d/3): role=%s", attempt + 1, role)
            
            # Exponential backoff with jitter: 1s, 2s, 4s
            if attempt < 2:
                wait_time = (2 ** attempt) + (0.1 * attempt)  # Simple jitter
                await asyncio.sleep(wait_time)
        
        # All retries exhausted
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        await self._log_usage(
            provider="gemini",
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
        raise ExternalServiceError("Gemini", last_error or "Max retries exceeded")
    
    async def embed(
        self,
        texts: list[str],
        school_id: str | None = None,
        user_id: str | None = None,
    ) -> list[list[float]]:
        """Generate embeddings using the registry's Gemini embeddings model."""
        # No hardcoded model names (global rule #4) — always resolve from registry.
        model_id = model_for("embeddings", "gemini")

        start_time = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                genai.embed_content_async(
                    model=model_id,
                    content=texts,
                    task_type="retrieval_document",
                ),
                timeout=settings.GEMINI_TIMEOUT,
            )
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            embeddings = result["embedding"]
            
            await self._log_usage(
                provider="gemini",
                model_role="embeddings",
                model_id=model_id,
                task="embedding",
                prompt_tokens=sum(len(t.split()) for t in texts),  # Approximate
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
                provider="gemini",
                model_role="embeddings",
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
            raise ExternalServiceError("Gemini Embeddings", str(e))
    
    async def health_check(self) -> bool:
        """Check if Gemini API is accessible."""
        if settings.MOCK_EXTERNAL_SERVICES:
            return True
        try:
            model = self._get_model("fast_chat")
            await asyncio.wait_for(
                model.generate_content_async("ping"),
                timeout=10,
            )
            return True
        except Exception as e:
            logger.error("Gemini health check failed: %s", e)
            return False
    
    def _convert_messages(self, messages: list[dict[str, str]]) -> list[dict]:
        """Convert standard messages to Gemini format."""
        gemini_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "") or msg.get("parts", [""])[0]
            
            if role == "system":
                # Gemini doesn't have system role, prepend to first user message
                if gemini_messages and gemini_messages[-1]["role"] == "user":
                    gemini_messages[-1]["parts"][0] = f"{content}\n\n{gemini_messages[-1]['parts'][0]}"
                else:
                    gemini_messages.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                gemini_messages.append({"role": "model", "parts": [content]})
            else:
                gemini_messages.append({"role": "user", "parts": [content]})
        
        return gemini_messages
    
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
        """Log LLM usage to database. Fire-and-forget."""
        # This will be called from the LLM router which has DB session
        # For now, just log to stdout; router will handle DB persistence
        logger.info(
            "LLM_USAGE: provider=%s role=%s model=%s task=%s "
            "prompt_tokens=%d completion_tokens=%d latency_ms=%d "
            "school_id=%s user_id=%s status=%s error=%s",
            provider, model_role, model_id, task,
            prompt_tokens, completion_tokens, latency_ms,
            school_id, user_id, status, error_msg or "none"
        )


# Singleton instance
_gemini_client: GeminiClient | None = None


def get_gemini_client() -> GeminiClient:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client