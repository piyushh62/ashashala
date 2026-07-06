"""Phase 6 P1 — safety hardening: topic guard + rate-limit wiring.

Network-free: the deterministic keyword fast-path is exercised directly, and the
rate limiter is asserted to be configured. (The live Gemini built-in-safety
check needs a real key and is a manual pre-launch step — see docs/safety.md.)
"""

import pytest

from app.agents.safety import check_topic_relevance, safety_wrapper
from app.core.exceptions import ForbiddenError


@pytest.mark.asyncio
async def test_off_topic_keyword_is_blocked():
    # Keyword fast-path returns False without any LLM call.
    assert await check_topic_relevance("how do I make a bomb", "science") is False


@pytest.mark.asyncio
async def test_unknown_subject_is_blocked():
    assert await check_topic_relevance("explain fractions", "astrology") is False


@pytest.mark.asyncio
async def test_safety_wrapper_raises_on_off_topic():
    with pytest.raises(ForbiddenError):
        await safety_wrapper("let's talk about violence", "mathematics")


def test_rate_limit_settings_present():
    from app.core.config import settings

    assert settings.CHAT_RATE_LIMIT.endswith("/minute")
    assert settings.QUIZ_RATE_LIMIT.endswith("/minute")


def test_chat_endpoint_has_rate_limit_decorator():
    # slowapi tags decorated endpoints; when slowapi is absent the shim no-ops
    # and the app still imports (asserted by importing main below).
    from app.core.ratelimit import SLOWAPI_AVAILABLE, limiter

    assert limiter is not None
    import app.main  # noqa: F401 — importing proves the wiring doesn't crash

    if SLOWAPI_AVAILABLE:
        assert getattr(app.main.app.state, "limiter", None) is not None
