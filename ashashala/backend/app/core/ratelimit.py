"""Shared rate limiter (slowapi) — protects the free Gemini/NVIDIA quotas.

Degrades gracefully: if slowapi isn't installed, `limiter.limit(...)` becomes a
no-op decorator so the app still imports and runs (tests, minimal installs).
Routes import `limiter` from here; main.py wires the exception handler +
middleware only when slowapi is actually available.
"""

from __future__ import annotations

try:  # pragma: no cover - import guard
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    SLOWAPI_AVAILABLE = True
except Exception:  # noqa: BLE001 - slowapi optional
    SLOWAPI_AVAILABLE = False

    class _NoopLimiter:
        """Fallback with the same .limit(...) decorator surface."""

        def limit(self, *_args, **_kwargs):
            def _decorator(func):
                return func

            return _decorator

    limiter = _NoopLimiter()  # type: ignore[assignment]
