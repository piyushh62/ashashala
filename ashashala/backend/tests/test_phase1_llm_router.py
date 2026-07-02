"""Phase 1 — LLM router routing table (spec Section 3 + Section 14 tests).

The four Section 14 cases:
  (a) English question        -> Gemini fast_chat (gemini-2.5-flash-lite)
  (b) Gujarati (lang_hint=gu) -> NVIDIA Sarvam-M (multilingual_indic), no Gemini
  (c) Gemini 429              -> falls back to NVIDIA fast_chat
  (d) task="evaluate"         -> Gemini reasoning; on 429 -> NVIDIA reasoning
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.llm_router import INDIC_LANGS, LLMRouter
from app.services.model_registry import list_roles, model_for, validate_registry

MSGS = [{"role": "user", "content": "Explain photosynthesis"}]


def _mock_clients(gemini_chat=None, nvidia_chat=None):
    """Patch get_gemini_client/get_nvidia_client in the router module."""
    gemini = AsyncMock()
    gemini.chat = gemini_chat or AsyncMock(return_value="gemini-answer")
    nvidia = AsyncMock()
    nvidia.chat = nvidia_chat or AsyncMock(return_value="nvidia-answer")
    return (
        patch("app.services.llm_router.get_gemini_client", return_value=gemini),
        patch("app.services.llm_router.get_nvidia_client", return_value=nvidia),
        gemini,
        nvidia,
    )


class TestRoutingSection14:
    @pytest.mark.asyncio
    async def test_a_english_goes_to_gemini_fast_chat(self):
        gp, np_, gemini, nvidia = _mock_clients()
        with gp, np_:
            router = LLMRouter()
            out = await router.route("explain", MSGS, lang_hint="en")
        assert out == "gemini-answer"
        assert gemini.chat.await_args.kwargs["role"] == "fast_chat"
        nvidia.chat.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_b_gujarati_goes_to_nvidia_sarvam_no_gemini(self):
        gp, np_, gemini, nvidia = _mock_clients()
        with gp, np_:
            router = LLMRouter()
            out = await router.route("explain", MSGS, lang_hint="gu")
        assert out == "nvidia-answer"
        gemini.chat.assert_not_awaited()
        assert nvidia.chat.await_args.kwargs["role"] == "multilingual_indic"

    @pytest.mark.asyncio
    async def test_c_gemini_429_falls_back_to_nvidia_fast_chat(self):
        gemini_chat = AsyncMock(side_effect=Exception("429 rate limit"))
        gp, np_, gemini, nvidia = _mock_clients(gemini_chat=gemini_chat)
        with gp, np_:
            router = LLMRouter()
            out = await router.route("explain", MSGS, lang_hint="en")
        assert out == "nvidia-answer"
        gemini.chat.assert_awaited_once()
        assert nvidia.chat.await_args.kwargs["role"] == "fast_chat"

    @pytest.mark.asyncio
    async def test_d_evaluate_uses_reasoning_then_nvidia_reasoning(self):
        # primary path: Gemini reasoning
        gp, np_, gemini, nvidia = _mock_clients()
        with gp, np_:
            router = LLMRouter()
            out = await router.route("evaluate", MSGS, lang_hint="en")
        assert out == "gemini-answer"
        assert gemini.chat.await_args.kwargs["role"] == "reasoning"

        # 429 path: falls back to NVIDIA reasoning
        gemini_chat = AsyncMock(side_effect=Exception("429 rate limit"))
        gp, np_, gemini, nvidia = _mock_clients(gemini_chat=gemini_chat)
        with gp, np_:
            router = LLMRouter()
            out = await router.route("evaluate", MSGS, lang_hint="en")
        assert out == "nvidia-answer"
        assert nvidia.chat.await_args.kwargs["role"] == "reasoning"

    @pytest.mark.asyncio
    async def test_both_providers_fail_raises(self):
        fail = AsyncMock(side_effect=Exception("boom"))
        gp, np_, gemini, nvidia = _mock_clients(gemini_chat=fail, nvidia_chat=fail)
        with gp, np_:
            router = LLMRouter()
            with pytest.raises(Exception):
                await router.route("explain", MSGS, lang_hint="en")


class TestRoutingChain:
    def test_indic_langs_set(self):
        assert {"gu", "hi", "mr", "ta", "te", "bn", "kn", "ml", "pa", "ur"} == INDIC_LANGS

    def test_get_routing_info_english(self):
        gp, np_, _, _ = _mock_clients()
        with gp, np_:
            info = LLMRouter().get_routing_info("explain", "en")
        assert info["chain"][0]["provider"] == "gemini"
        assert info["chain"][0]["role"] == "fast_chat"

    def test_get_routing_info_gujarati(self):
        gp, np_, _, _ = _mock_clients()
        with gp, np_:
            info = LLMRouter().get_routing_info("explain", "gu")
        assert info["chain"][0]["provider"] == "nvidia"
        assert info["chain"][0]["role"] == "multilingual_indic"


class TestModelRegistry:
    def test_fast_chat_gemini_is_flash_lite(self):
        assert model_for("fast_chat", "gemini") == "gemini-2.5-flash-lite"

    def test_reasoning_gemini_is_flash(self):
        assert model_for("reasoning", "gemini") == "gemini-2.5-flash"

    def test_fast_chat_nvidia_fallback(self):
        assert model_for("fast_chat", "nvidia") == "meta/llama-3.1-8b-instruct"

    def test_indic_nvidia_primary_is_sarvam(self):
        assert model_for("multilingual_indic", "nvidia") == "sarvamai/sarvam-m"

    def test_no_gemini_2_0_or_pro_anywhere(self):
        from app.services.model_registry import get_registry

        for role, cfg in get_registry().items():
            gem = cfg.get("gemini", "")
            assert "2.0-flash" not in gem, f"{role} uses shut-down gemini-2.0-flash"
            assert gem != "gemini-2.5-pro", f"{role} uses paid gemini-2.5-pro"

    def test_unknown_role_raises(self):
        with pytest.raises(ValueError):
            model_for("nope", "gemini")

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError):
            model_for("fast_chat", "martian")

    def test_list_roles(self):
        roles = list_roles()
        for r in ["fast_chat", "reasoning", "multilingual_indic", "vision",
                  "ocr", "asr", "embeddings", "safety_jailbreak"]:
            assert r in roles

    def test_validate_registry_returns_list(self):
        assert isinstance(validate_registry(), list)
