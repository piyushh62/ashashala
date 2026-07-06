"""Real token streaming — router stream, provider routing, tutor stream."""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.tutor import tutor_agent_stream
from app.services.llm_router import chat_stream

MSGS = [{"role": "user", "content": "Explain fractions"}]


@pytest.mark.asyncio
async def test_router_stream_yields_multiple_tokens_english():
    tokens = [t async for t in chat_stream(messages=MSGS, task="explain", lang_hint="en")]
    assert len(tokens) > 1, "streaming should yield multiple deltas, not one blob"
    assert "".join(tokens).startswith("[MOCK] streamed gemini")


@pytest.mark.asyncio
async def test_router_stream_indic_routes_to_nvidia():
    tokens = [t async for t in chat_stream(messages=MSGS, task="explain", lang_hint="gu")]
    assert "nvidia" in "".join(tokens)  # Indic → NVIDIA-direct


@pytest.mark.asyncio
async def test_tutor_stream_emits_tokens_then_citations():
    with patch("app.agents.tutor.retrieve", new_callable=AsyncMock) as mock_retrieve:
        mock_retrieve.return_value = []
        events = [
            e async for e in tutor_agent_stream(
                student_id="s1", student_name="Asha", grade=6, subject="Mathematics",
                class_id="c1", school_id="sch1", question="What is a fraction?",
            )
        ]

    token_events = [e for e in events if e["type"] == "token"]
    citation_events = [e for e in events if e["type"] == "citations"]
    assert len(token_events) > 1
    assert len(citation_events) == 1
    # The citations event carries the fully-assembled answer.
    assert citation_events[0]["answer"] == "".join(e["content"] for e in token_events)
    assert citation_events[0]["lang"] == "en"
