"""Tests for v0.8 streaming narrator responses.

Covers:
  - BaseLLMProvider.stream_complete default fallback (yields single chunk
    from .complete())
  - OllamaProvider.stream_complete parses line-delimited JSON correctly
  - _sse.stream_openai_chat parses OpenAI-compatible SSE correctly
  - Narrator.stream_action yields chunks AND applies state changes after
    the stream is exhausted
"""

from __future__ import annotations

import json
from typing import Iterator

import httpx
import pytest

from rag_quest.engine.character import Character, CharacterClass, Race
from rag_quest.engine.narrator import Narrator
from rag_quest.engine.world import World
from rag_quest.llm._sse import stream_openai_chat
from rag_quest.llm.base import BaseLLMProvider, LLMConfig

# ---------------------------------------------------------------------------
# BaseLLMProvider default fallback
# ---------------------------------------------------------------------------


class _StaticProvider(BaseLLMProvider):
    """Minimal concrete provider that doesn't override stream_complete."""

    def complete(
        self,
        messages,
        temperature=None,
        max_tokens=None,
        **kwargs,
    ) -> str:
        return "the whole response"


def test_base_stream_complete_fallback_yields_single_chunk():
    provider = _StaticProvider(LLMConfig(provider="static", model="x"))
    chunks = list(provider.stream_complete([{"role": "user", "content": "hi"}]))
    assert chunks == ["the whole response"]


def test_base_stream_complete_joins_to_full_complete_result():
    provider = _StaticProvider(LLMConfig(provider="static", model="x"))
    full = "".join(provider.stream_complete([{"role": "user", "content": "hi"}]))
    assert full == provider.complete([{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# OllamaProvider.stream_complete: parse line-delimited JSON
# ---------------------------------------------------------------------------


class _MockStreamResponse:
    """Minimal stand-in for an httpx streaming response."""

    def __init__(self, lines: list[str]):
        self._lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        return None

    def iter_lines(self):
        yield from self._lines


def test_ollama_stream_parses_line_delimited_json(monkeypatch):
    from rag_quest.llm.ollama_provider import OllamaProvider

    provider = OllamaProvider(LLMConfig(provider="ollama", model="gemma3:4b"))

    lines = [
        json.dumps({"message": {"content": "You "}, "done": False}),
        json.dumps({"message": {"content": "push the "}, "done": False}),
        json.dumps({"message": {"content": "door open."}, "done": False}),
        json.dumps({"message": {"content": ""}, "done": True}),
    ]

    def fake_stream(method, url, json=None):
        assert method == "POST"
        assert json["stream"] is True
        return _MockStreamResponse(lines)

    monkeypatch.setattr(provider.client, "stream", fake_stream)

    chunks = list(provider.stream_complete([{"role": "user", "content": "open"}]))
    # Short clean content may be buffered by the thinking-strip logic and
    # flushed as fewer chunks, so assert on the joined result.
    joined = "".join(chunks)
    assert "You" in joined
    assert "push the" in joined
    assert "door open." in joined


def test_ollama_stream_skips_malformed_lines(monkeypatch):
    from rag_quest.llm.ollama_provider import OllamaProvider

    provider = OllamaProvider(LLMConfig(provider="ollama", model="gemma3:4b"))
    lines = [
        "",  # empty line
        "not json at all",  # malformed
        json.dumps({"message": {"content": "Hi"}, "done": False}),
        json.dumps({"message": {"content": ""}, "done": True}),
    ]
    monkeypatch.setattr(
        provider.client, "stream", lambda *a, **k: _MockStreamResponse(lines)
    )

    chunks = list(provider.stream_complete([{"role": "user", "content": "x"}]))
    assert chunks == ["Hi"]


def test_ollama_stream_thinking_fallback_when_no_content(monkeypatch):
    """If the model only emits `thinking` with empty content, fall back
    to the trailing paragraph so the stream never produces an empty turn."""
    from rag_quest.llm.ollama_provider import OllamaProvider

    provider = OllamaProvider(LLMConfig(provider="ollama", model="qwen3.5:4b"))
    lines = [
        json.dumps(
            {
                "message": {
                    "content": "",
                    "thinking": "Let me think...\n\nThe door swings open.",
                },
                "done": False,
            }
        ),
        json.dumps({"message": {"content": ""}, "done": True}),
    ]
    monkeypatch.setattr(
        provider.client, "stream", lambda *a, **k: _MockStreamResponse(lines)
    )
    chunks = list(provider.stream_complete([{"role": "user", "content": "x"}]))
    assert chunks == ["The door swings open."]


# ---------------------------------------------------------------------------
# stream_openai_chat SSE parser
# ---------------------------------------------------------------------------


class _FakeClient:
    """Pretend httpx.Client whose `stream()` returns canned SSE lines."""

    def __init__(self, lines: list[str]):
        self.lines = lines
        self.seen: list[tuple[str, str, dict]] = []

    def stream(self, method, path, json=None):
        self.seen.append((method, path, json))
        return _MockStreamResponse(self.lines)


def _sse_event(content: str, finish: str | None = None) -> str:
    """Build a `data: {...}` SSE line carrying a delta chunk."""
    payload = {
        "choices": [
            {"delta": {"content": content}, "finish_reason": finish},
        ]
    }
    return "data: " + json.dumps(payload)


def test_sse_helper_yields_content_deltas():
    client = _FakeClient(
        [
            _sse_event("You "),
            _sse_event("step "),
            _sse_event("forward."),
            _sse_event("", finish="stop"),
        ]
    )
    chunks = list(stream_openai_chat(client, "/chat/completions", {"stream": True}))
    assert chunks == ["You ", "step ", "forward."]


def test_sse_helper_stops_on_done_sentinel():
    client = _FakeClient(
        [
            _sse_event("First."),
            "data: [DONE]",
            _sse_event("Never seen."),  # after [DONE] — ignored
        ]
    )
    chunks = list(stream_openai_chat(client, "/chat/completions", {"stream": True}))
    assert chunks == ["First."]


def test_sse_helper_skips_keepalive_and_malformed_lines():
    client = _FakeClient(
        [
            "",  # empty
            ": keep-alive comment",  # SSE comment
            "data:",  # empty data
            "data: not-json",  # malformed
            _sse_event("Payload."),
            _sse_event("", finish="stop"),
        ]
    )
    chunks = list(stream_openai_chat(client, "/chat/completions", {"stream": True}))
    assert chunks == ["Payload."]


# ---------------------------------------------------------------------------
# Narrator.stream_action
# ---------------------------------------------------------------------------


class _StreamingLLM:
    """Test double: yields pre-recorded chunks from stream_complete,
    records messages for assertions."""

    def __init__(self, chunks: list[str]):
        self.chunks = chunks
        self.last_messages = None
        self.stream_called = 0

    def stream_complete(self, messages, **kwargs):
        self.last_messages = messages
        self.stream_called += 1
        for chunk in self.chunks:
            yield chunk

    # Provide a complete() fallback too, for the default path.
    def complete(self, messages, **kwargs):
        self.last_messages = messages
        return "".join(self.chunks)

    def close(self):
        pass


class _NoRAG:
    def query_world(self, *a, **k):
        return ""


def _make_streaming_narrator(chunks: list[str]) -> Narrator:
    return Narrator(
        llm=_StreamingLLM(chunks),
        world_rag=_NoRAG(),
        character=Character(
            name="Hero",
            race=Race.HUMAN,
            character_class=CharacterClass.FIGHTER,
            location="Stonebridge",
        ),
        world=World(name="Test", setting="Fantasy", tone="Heroic"),
    )


def test_stream_action_yields_chunks_in_order():
    narrator = _make_streaming_narrator(["You push ", "the door ", "open."])
    chunks = list(narrator.stream_action("open the door"))
    assert chunks == ["You push ", "the door ", "open."]


def test_stream_action_populates_last_response_after_exhaustion():
    narrator = _make_streaming_narrator(["You push ", "the door ", "open."])
    list(narrator.stream_action("open the door"))  # exhaust generator
    assert narrator.last_response == "You push the door open."
    assert narrator.last_player_input == "open the door"


def test_stream_action_appends_to_conversation_history():
    narrator = _make_streaming_narrator(["Ok.", " Done."])
    list(narrator.stream_action("wait"))
    # user + assistant message appended.
    assert narrator.conversation_history[-2] == {
        "role": "user",
        "content": "wait",
    }
    assert narrator.conversation_history[-1] == {
        "role": "assistant",
        "content": "Ok. Done.",
    }


def test_stream_action_runs_state_parser_on_full_concatenated_text():
    """State parser must see the joined response, not individual chunks."""
    narrator = _make_streaming_narrator(
        [
            "You ",
            "meet Captain ",
            "Mira ",  # "meet Captain Mira" triggers npc_met detection
            "in the marketplace.",
        ]
    )
    list(narrator.stream_action("greet"))
    assert narrator.last_change is not None
    # npc_met should fire on the joined string, not chunk-by-chunk.
    assert narrator.last_change.npc_met is not None


def test_stream_action_with_service_context_injects_addendum():
    narrator = _make_streaming_narrator(["Ready to help."])
    narrator.service_context = "=== BASE CONVERSATION ===\nTest addendum."
    list(narrator.stream_action("hi"))
    messages = narrator.llm.last_messages
    assert messages is not None
    assert "BASE CONVERSATION" in messages[0]["content"]
    assert "Test addendum" in messages[0]["content"]


def test_ui_stream_narrator_response_returns_joined_text():
    """ui.stream_narrator_response should accumulate the full text from
    the iterator and return it, regardless of whether Rich Live renders."""
    from rag_quest import ui

    def chunks():
        yield "You "
        yield "open "
        yield "the door."

    result = ui.stream_narrator_response(chunks())
    assert result == "You open the door."


def test_ui_stream_narrator_response_skips_empty_chunks():
    from rag_quest import ui

    def chunks():
        yield ""
        yield "ok"
        yield None  # defensive — should not crash
        yield " done."

    # Some iterators may yield None; the helper should tolerate it.
    try:
        result = ui.stream_narrator_response(chunks())
    except TypeError:
        pytest.fail("stream_narrator_response should tolerate None chunks")
    assert "ok" in result
    assert "done" in result


def test_stream_action_recovers_from_llm_exception():
    class BrokenLLM:
        def stream_complete(self, messages, **kwargs):
            raise RuntimeError("boom")
            yield  # make this a generator so hasattr works

        def complete(self, messages, **kwargs):
            return "fallback"

        def close(self):
            pass

    narrator = Narrator(
        llm=BrokenLLM(),
        world_rag=_NoRAG(),
        character=Character(
            name="Hero",
            race=Race.HUMAN,
            character_class=CharacterClass.FIGHTER,
        ),
        world=World(name="Test", setting="Fantasy", tone="Heroic"),
    )
    chunks = list(narrator.stream_action("anything"))
    # When streaming raises, the narrator falls back to the canned
    # _generate_response path (which calls .complete) — we should get
    # at least one non-empty chunk back.
    assert chunks
    assert "".join(chunks).strip()
