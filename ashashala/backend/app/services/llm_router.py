"""LLM Router — implements the routing table from PROJECT_PROMPT.md Section 3.

Routing rules (in order):
  1. Indic language (lang_hint in INDIC_LANGS) -> NVIDIA multilingual_indic
     (Sarvam-M primary -> Maverick fallback). No Gemini call.
  2. task == "evaluate" -> Gemini reasoning (2.5-flash) -> NVIDIA reasoning.
  3. task == "vision"   -> Gemini vision   (2.5-flash) -> NVIDIA vision.
  4. default            -> Gemini fast_chat (2.5-flash-lite) -> NVIDIA fast_chat.

Every call is logged to the LlmUsage table when a DB session is supplied.
"""

import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ExternalServiceError, ValidationError
from app.services.gemini_client import get_gemini_client
from app.services.model_registry import get_registry, model_for
from app.services.nvidia_client import get_nvidia_client

logger = logging.getLogger(__name__)


# ISO 639-1 codes that route NVIDIA-direct (Sarvam-M), bypassing Gemini.
INDIC_LANGS = {"gu", "hi", "mr", "ta", "te", "bn", "kn", "ml", "pa", "ur"}

# task -> (primary_provider, primary_role, fallback_provider, fallback_role)
ROUTING_TABLE: dict[str, tuple[str, str, str, str]] = {
    "evaluate": ("gemini", "reasoning", "nvidia", "reasoning"),
    "vision": ("gemini", "vision", "nvidia", "vision"),
    # Scheduling needs constraint-following (pick only from supplied free
    # slots), not just fluent prose — routed like evaluate.
    "schedule": ("gemini", "reasoning", "nvidia", "reasoning"),
    # Everything else is fast_chat (explain / chat / classify / default).
    "explain": ("gemini", "fast_chat", "nvidia", "fast_chat"),
    "chat": ("gemini", "fast_chat", "nvidia", "fast_chat"),
    "classify": ("gemini", "fast_chat", "nvidia", "fast_chat"),
}
DEFAULT_ROUTE: tuple[str, str, str, str] = ("gemini", "fast_chat", "nvidia", "fast_chat")


class LLMRouter:
    """Routes chat requests to the right provider/model with fallback + logging."""

    def __init__(self, db: AsyncSession | None = None):
        self.db = db
        self._gemini = get_gemini_client()
        self._nvidia = get_nvidia_client()
        self._provider_health: dict[str, bool] = {"gemini": True, "nvidia": True}

    def _resolve_chain(self, task: str, lang_hint: str) -> list[dict]:
        """Return the ordered [primary, fallback] steps for this task+language.

        Each step: {"provider", "role", "model_id" (override or None), "label"}.
        """
        # Rule 1 — Indic language wins over task-based routing.
        if lang_hint in INDIC_LANGS:
            indic = get_registry().get("multilingual_indic", {})
            return [
                {"provider": "nvidia", "role": "multilingual_indic",
                 "model_id": None, "label": "indic-primary"},
                {"provider": "nvidia", "role": "multilingual_indic",
                 "model_id": indic.get("nvidia_fallback") or None, "label": "indic-fallback"},
            ]

        pp, pr, fp, fr = ROUTING_TABLE.get(task, DEFAULT_ROUTE)
        return [
            {"provider": pp, "role": pr, "model_id": None, "label": "primary"},
            {"provider": fp, "role": fr, "model_id": None, "label": "fallback"},
        ]

    async def route(
        self,
        task: str,
        messages: list[dict[str, str]],
        lang_hint: str = "en",
        school_id: str | None = None,
        user_id: str | None = None,
        **kwargs,
    ) -> str:
        """Route a chat request through its provider chain, returning the text."""
        if not messages:
            raise ValidationError("messages must be a non-empty list")

        chain = self._resolve_chain(task, lang_hint)
        last_error: Exception | None = None

        for step in chain:
            try:
                text = await self._call_provider(step, messages, school_id, user_id, task, **kwargs)
                self._provider_health[step["provider"]] = True
                return text
            except Exception as e:  # noqa: BLE001 — fall through the chain
                last_error = e
                self._provider_health[step["provider"]] = False
                logger.warning(
                    "LLM step failed (task=%s, %s, provider=%s, role=%s): %s",
                    task, step["label"], step["provider"], step["role"], e,
                )

        raise ExternalServiceError("LLMRouter", f"All providers failed: {last_error}")

    async def route_stream(
        self,
        task: str,
        messages: list[dict[str, str]],
        lang_hint: str = "en",
        school_id: str | None = None,
        user_id: str | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream text deltas through the provider chain.

        Fallback is only possible before the first token is emitted — once a
        provider starts streaming to the client we can't rewind, so a mid-stream
        failure ends the answer (and is logged) rather than restarting.
        """
        if not messages:
            raise ValidationError("messages must be a non-empty list")

        chain = self._resolve_chain(task, lang_hint)
        last_error: Exception | None = None

        for step in chain:
            client = self._gemini if step["provider"] == "gemini" else self._nvidia
            gen_kwargs = dict(kwargs)
            if step["provider"] == "nvidia":
                gen_kwargs["model_id"] = step.get("model_id")
            started = False
            try:
                async for delta in client.chat_stream(
                    messages=messages, role=step["role"], school_id=school_id,
                    user_id=user_id, task=task, **gen_kwargs,
                ):
                    started = True
                    yield delta
                self._provider_health[step["provider"]] = True
                return
            except Exception as e:  # noqa: BLE001
                last_error = e
                self._provider_health[step["provider"]] = False
                if started:
                    logger.error("LLM stream failed mid-answer (%s): %s", step["label"], e)
                    raise
                logger.warning("LLM stream failed before first token (%s), trying next: %s",
                               step["label"], e)

        raise ExternalServiceError("LLMRouter", f"All providers failed: {last_error}")

    async def _call_provider(
        self,
        step: dict,
        messages: list[dict[str, str]],
        school_id: str | None,
        user_id: str | None,
        task: str,
        **kwargs,
    ) -> str:
        provider, role = step["provider"], step["role"]
        if provider == "gemini":
            return await self._gemini.chat(
                messages=messages, role=role, school_id=school_id,
                user_id=user_id, task=task, **kwargs,
            )
        if provider == "nvidia":
            return await self._nvidia.chat(
                messages=messages, role=role, school_id=school_id,
                user_id=user_id, task=task, model_id=step.get("model_id"), **kwargs,
            )
        raise ValidationError(f"Unknown provider: {provider}")

    async def embed(
        self,
        texts: list[str],
        school_id: str | None = None,
        user_id: str | None = None,
    ) -> list[list[float]]:
        """Embeddings — Gemini text-embedding-004 primary, NVIDIA fallback."""
        try:
            return await self._gemini.embed(texts, school_id, user_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("Gemini embeddings failed, trying NVIDIA: %s", e)
            self._provider_health["gemini"] = False
        try:
            return await self._nvidia.embed(texts, school_id=school_id, user_id=user_id)
        except Exception as e:  # noqa: BLE001
            logger.error("NVIDIA embeddings also failed: %s", e)
            self._provider_health["nvidia"] = False
            raise

    async def health_check(self) -> dict[str, bool]:
        """Check health of both providers."""
        results: dict[str, bool] = {}
        try:
            results["gemini"] = await self._gemini.health_check()
        except Exception:  # noqa: BLE001
            results["gemini"] = False
        try:
            results["nvidia"] = await self._nvidia.health_check()
        except Exception:  # noqa: BLE001
            results["nvidia"] = False
        self._provider_health.update(results)
        return results

    def get_routing_info(self, task: str, lang_hint: str = "en") -> dict:
        """Resolve the routing chain for a task+language (debug/UI)."""
        chain = self._resolve_chain(task, lang_hint)
        steps = []
        for step in chain:
            try:
                model_id = step.get("model_id") or model_for(step["role"], step["provider"])
            except Exception:  # noqa: BLE001
                model_id = step.get("model_id") or "?"
            steps.append({
                "label": step["label"],
                "provider": step["provider"],
                "role": step["role"],
                "model_id": model_id,
                "healthy": self._provider_health.get(step["provider"], True),
            })
        return {"task": task, "lang_hint": lang_hint, "chain": steps}


# --- Module-level convenience matching PROJECT_PROMPT.md Section 3 signature ---
async def chat(
    messages: list[dict[str, str]],
    task: str = "explain",
    lang_hint: str = "en",
    school_id: str | None = None,
    user_id: str | None = None,
    db: AsyncSession | None = None,
    **kwargs,
) -> str:
    """Route a chat request and return the model's text.

    Rules: Indic lang -> NVIDIA Sarvam-M; task="evaluate"/"vision" -> Gemini
    2.5-flash; default -> Gemini 2.5-flash-lite; each with NVIDIA fallback.
    """
    router = LLMRouter(db=db)
    return await router.route(
        task, messages, lang_hint=lang_hint, school_id=school_id, user_id=user_id, **kwargs
    )


async def chat_stream(
    messages: list[dict[str, str]],
    task: str = "explain",
    lang_hint: str = "en",
    school_id: str | None = None,
    user_id: str | None = None,
    db: AsyncSession | None = None,
    **kwargs,
) -> AsyncIterator[str]:
    """Stream a chat response through the routing chain, yielding text deltas."""
    router = LLMRouter(db=db)
    async for delta in router.route_stream(
        task, messages, lang_hint=lang_hint, school_id=school_id, user_id=user_id, **kwargs
    ):
        yield delta


async def get_llm_router(db: AsyncSession | None = None) -> LLMRouter:
    """FastAPI dependency for the LLM router."""
    return LLMRouter(db=db)
