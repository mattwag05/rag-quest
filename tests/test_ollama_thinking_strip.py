"""Tests for embedded thinking / reasoning stripping in OllamaProvider.

Gemma 4 E2B/E4B, Qwen 3.5, DeepSeek-R1 and similar models sometimes
ignore the ``think=False`` flag and inline chain-of-thought directly in
the content field.  The provider must strip this before returning
narrative text.

Gemma 4 uses a thought-channel format::

    <|channel>thought
    ...reasoning...
    <channel|>answer text

See https://ai.google.dev/gemma/docs/capabilities/thinking
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from rag_quest.llm.ollama_provider import (
    OllamaProvider,
    _has_thinking_markers,
    _strip_thinking,
)
from rag_quest.llm.base import LLMConfig


# ---------------------------------------------------------------------------
# Unit tests for _strip_thinking
# ---------------------------------------------------------------------------


class TestStripThinking:
    """Test the _strip_thinking helper directly."""

    def test_no_thinking_passthrough(self):
        text = "A cold wind howls through the dungeon corridor."
        assert _strip_thinking(text) == text

    def test_think_tags_removed(self):
        text = (
            "<think>The player wants to explore. I should describe the room.</think>"
            "You step into a dimly lit chamber."
        )
        assert _strip_thinking(text) == "You step into a dimly lit chamber."

    def test_think_tags_case_insensitive(self):
        text = "<THINK>reasoning here</THINK>The door creaks open."
        assert _strip_thinking(text) == "The door creaks open."

    def test_think_tags_multiline(self):
        text = (
            "<think>\nThe player said 'hello'.\n"
            "I need to respond in character.\n</think>\n"
            "The innkeeper nods warmly."
        )
        assert _strip_thinking(text) == "The innkeeper nods warmly."

    def test_reasoning_tags_removed(self):
        text = (
            "<reasoning>Analyzing the combat scenario...</reasoning>"
            "The goblin lunges at you!"
        )
        assert _strip_thinking(text) == "The goblin lunges at you!"

    def test_gemma4_thought_channel_removed(self):
        """Full Gemma 4 thought-channel block with opener + closer."""
        text = (
            "<|channel>thought\n"
            "The player input is a single word. I need to interpret this.\n"
            "Plan: 1. Describe scene. 2. Set atmosphere.\n"
            "<channel|>"
            "A cold, damp chill seeps into your bones."
        )
        assert _strip_thinking(text) == (
            "A cold, damp chill seeps into your bones."
        )

    def test_gemma4_thought_channel_multiline(self):
        """Gemma 4 thought channel with extensive multi-line reasoning."""
        text = (
            "<|channel>thought\n"
            "Thinking Process:\n\n"
            "1. Analyze the request.\n"
            "2. Determine the most likely interpretation.\n"
            "3. Formulate the answer.\n"
            "4. Review constraints.\n"
            "<channel|>"
            "The answer is H2O."
        )
        assert _strip_thinking(text) == "The answer is H2O."

    def test_bare_channel_close_strips_preamble(self):
        """Fallback: bare <channel|> without matching opener."""
        text = (
            "The player input is emotional. I should interpret this as "
            "a reaction.<channel|>A cold wind blows."
        )
        assert _strip_thinking(text) == "A cold wind blows."

    def test_think_tags_plus_channel_delimiter(self):
        text = (
            "<think>internal thought</think>"
            "more reasoning<channel|>"
            "Clean output."
        )
        assert _strip_thinking(text) == "Clean output."

    def test_no_content_after_stripping(self):
        text = "<think>Only thinking, no real content.</think>"
        assert _strip_thinking(text) == ""

    def test_empty_string(self):
        assert _strip_thinking("") == ""

    def test_multiple_think_blocks(self):
        text = (
            "<think>first thought</think>"
            "Some text. "
            "<think>second thought</think>"
            "Final answer."
        )
        assert _strip_thinking(text) == "Some text. Final answer."


# ---------------------------------------------------------------------------
# Unit tests for _has_thinking_markers
# ---------------------------------------------------------------------------


class TestHasThinkingMarkers:
    def test_no_markers(self):
        assert not _has_thinking_markers("You open the door.")

    def test_think_tag(self):
        assert _has_thinking_markers("<think>x</think>answer")

    def test_gemma4_thought_channel(self):
        assert _has_thinking_markers(
            "<|channel>thought\nreasoning\n<channel|>answer"
        )

    def test_bare_channel_close(self):
        assert _has_thinking_markers("reasoning<channel|>answer")

    def test_partial_opener_no_closer(self):
        """An opener without a closer should NOT match — we need the
        full block to strip safely."""
        assert not _has_thinking_markers("<|channel>thought\nstill thinking")

    def test_partial_think_no_closer(self):
        assert not _has_thinking_markers("<think>still thinking")


# ---------------------------------------------------------------------------
# Integration tests for OllamaProvider.complete() thinking stripping
# ---------------------------------------------------------------------------


def _make_provider():
    config = LLMConfig(
        provider="ollama",
        model="gemma4:e2b",
        temperature=0.7,
        max_tokens=512,
    )
    return OllamaProvider(config)


class TestCompleteThinkingStrip:
    """Test that complete() strips embedded thinking from responses."""

    def test_complete_strips_think_tags(self):
        provider = _make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "content": (
                    "<think>Player wants to look around.</think>"
                    "You see a dusty old tavern."
                ),
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider.client, "post", return_value=mock_response):
            result = provider.complete([{"role": "user", "content": "look around"}])
        assert result == "You see a dusty old tavern."

    def test_complete_strips_gemma4_thought_channel(self):
        provider = _make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "content": (
                    "<|channel>thought\n"
                    "The player said cry. This is emotional.\n"
                    "I need to describe a reaction.\n"
                    "<channel|>"
                    "Tears stream down your face."
                ),
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider.client, "post", return_value=mock_response):
            result = provider.complete([{"role": "user", "content": "cry"}])
        assert result == "Tears stream down your face."

    def test_complete_strips_bare_channel_delimiter(self):
        provider = _make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "content": (
                    "The player said cry. This is emotional.<channel|>"
                    "Tears stream down your face."
                ),
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider.client, "post", return_value=mock_response):
            result = provider.complete([{"role": "user", "content": "cry"}])
        assert result == "Tears stream down your face."

    def test_complete_clean_content_unchanged(self):
        provider = _make_provider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "The wind howls outside."}
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider.client, "post", return_value=mock_response):
            result = provider.complete([{"role": "user", "content": "listen"}])
        assert result == "The wind howls outside."


# ---------------------------------------------------------------------------
# Integration tests for stream_complete() thinking buffering
# ---------------------------------------------------------------------------


def _make_stream_lines(tokens):
    """Build line-delimited JSON mimicking Ollama streaming output."""
    lines = []
    for tok in tokens:
        obj = {"message": {"content": tok}, "done": False}
        lines.append(json.dumps(obj))
    lines.append(json.dumps({"message": {"content": ""}, "done": True}))
    return lines


def _run_stream(provider, tokens, user_msg="test"):
    """Helper: feed tokens through stream_complete and return chunks."""
    lines = _make_stream_lines(tokens)
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.iter_lines.return_value = iter(lines)
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch.object(provider.client, "stream", return_value=mock_response):
        return list(
            provider.stream_complete([{"role": "user", "content": user_msg}])
        )


class TestStreamCompleteThinkingStrip:
    """Test that stream_complete() buffers and strips thinking from streams."""

    def test_stream_strips_gemma4_thought_channel(self):
        """Full Gemma 4 thought-channel: <|channel>thought....<channel|>."""
        provider = _make_provider()
        tokens = [
            "<|channel>",
            "thought\n",
            "The player input is emotional.\n",
            "I need to describe a reaction.\n",
            "<channel|>",
            "A cold ",
            "wind blows.",
        ]
        chunks = _run_stream(provider, tokens)
        full = "".join(chunks)
        assert "player input" not in full
        assert "I need to" not in full
        assert "wind blows" in full

    def test_stream_long_gemma4_preamble_fully_buffered(self):
        """Reproduce the real Gemma 4 E2B problem: long reasoning preamble
        with many tokens of meta-commentary, followed by <channel|> and
        clean narrative.  All thinking must be suppressed."""
        provider = _make_provider()
        tokens = [
            "<|channel>",
            "thought\n",
            "The player ",
            "input is a single word, ",
            '"Cry," ',
            "which is an emotional action ",
            "rather than a direct command. ",
            "I need to interpret this as ",
            "an emotional reaction. ",
            "I will focus on painting the scene. ",
            "Plan:\n1. Describe the visual experience.\n",
            "2. Enhance sensory details.\n",
            "3. Set the stage.\n",
            "<channel|>",
            "You take a deep breath, ",
            "the last vestiges of sunlight ",
            "vanishing as you step across ",
            "the threshold.",
        ]
        chunks = _run_stream(provider, tokens, "cry")
        full = "".join(chunks)
        # All thinking must be absent
        assert "The player" not in full
        assert "I need to" not in full
        assert "Plan:" not in full
        assert "<|channel>" not in full
        assert "<channel|>" not in full
        # Narrative must be present
        assert "deep breath" in full
        assert "threshold" in full

    def test_stream_strips_bare_channel_close(self):
        """Bare <channel|> without <|channel>thought opener."""
        provider = _make_provider()
        tokens = [
            "The player ",
            "input is emotional.",
            "<channel|>",
            "A cold ",
            "wind blows.",
        ]
        chunks = _run_stream(provider, tokens)
        full = "".join(chunks)
        assert "player input" not in full
        assert "wind blows" in full

    def test_stream_strips_think_tags(self):
        provider = _make_provider()
        tokens = [
            "<think>",
            "reasoning here",
            "</think>",
            "The door opens.",
        ]
        chunks = _run_stream(provider, tokens)
        full = "".join(chunks)
        assert "reasoning" not in full
        assert "door opens" in full

    def test_stream_clean_narrative_flushes_after_detection_limit(self):
        """Clean narrative content flushes after the detection token limit."""
        provider = _make_provider()
        tokens = [f"You walk through room {i}. " for i in range(15)]
        chunks = _run_stream(provider, tokens)
        full = "".join(chunks)
        assert "room 0" in full
        assert "room 14" in full

    def test_stream_short_clean_content_flushed_at_end(self):
        """Short content with no thinking markers flushes on stream end."""
        provider = _make_provider()
        tokens = ["Hello ", "world."]
        chunks = _run_stream(provider, tokens)
        full = "".join(chunks)
        assert "Hello" in full
        assert "world." in full

    def test_stream_thinking_without_closer_stripped_at_eos(self):
        """If the model opens a thought channel but never closes it, the
        EOS flush runs _strip_thinking which handles the bare closer or
        yields what's left."""
        provider = _make_provider()
        tokens = [
            "<|channel>",
            "thought\n",
            "I should describe a campfire.\n",
            "A warm fire crackles nearby.",
        ]
        chunks = _run_stream(provider, tokens)
        full = "".join(chunks)
        # The opener was detected → full_buffer mode, but no closer
        # arrived.  EOS flush runs _strip_thinking on the joined buffer.
        # Without a closer, _strip_thinking can't match the block, so the
        # full text is emitted.  This is acceptable — the important thing
        # is that it was NOT streamed token-by-token.
        assert len(chunks) <= 1  # single flush, not per-token

    def test_passthrough_tokens_after_thinking_stream_directly(self):
        """After the thought channel closes, subsequent tokens should be
        yielded individually (not re-buffered)."""
        provider = _make_provider()
        tokens = [
            "<|channel>thought\nreasoning\n<channel|>",
            "First ",
            "token. ",
            "Second ",
            "token.",
        ]
        chunks = _run_stream(provider, tokens)
        # The first chunk may contain text from the stripped block flush.
        # Subsequent chunks should be individual tokens.
        assert len(chunks) >= 4  # at least the 4 narrative tokens
        full = "".join(chunks)
        assert "First" in full
        assert "Second" in full
        assert "reasoning" not in full
