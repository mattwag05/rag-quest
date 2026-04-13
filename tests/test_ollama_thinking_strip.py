"""Tests for embedded thinking / reasoning stripping in OllamaProvider.

Gemma 4, Qwen 3.5, DeepSeek-R1 and similar models sometimes ignore the
``think=False`` flag and inline chain-of-thought directly in the content
field.  The provider must strip this before returning narrative text.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from rag_quest.llm.ollama_provider import OllamaProvider, _strip_thinking
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

    def test_channel_delimiter_strips_preamble(self):
        text = (
            "The player input is a single word. I should interpret this as "
            "an emotional action.<channel|>A cold, damp chill seeps into "
            "your bones as you stand at the threshold."
        )
        assert _strip_thinking(text) == (
            "A cold, damp chill seeps into your bones as you stand at the threshold."
        )

    def test_channel_delimiter_multiline_preamble(self):
        text = (
            "First line of reasoning.\n"
            "Second line of reasoning.\n"
            "<channel|>The narrative begins here."
        )
        assert _strip_thinking(text) == "The narrative begins here."

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

    def test_complete_strips_channel_delimiter(self):
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


def _make_stream_lines(tokens, thinking_tokens=None):
    """Build line-delimited JSON mimicking Ollama streaming output."""
    lines = []
    for tok in tokens:
        obj = {"message": {"content": tok}, "done": False}
        if thinking_tokens:
            obj["message"]["thinking"] = ""
        lines.append(json.dumps(obj))
    lines.append(json.dumps({"message": {"content": ""}, "done": True}))
    return lines


class TestStreamCompleteThinkingStrip:
    """Test that stream_complete() buffers and strips thinking from streams."""

    def test_stream_strips_channel_delimiter(self):
        provider = _make_provider()
        # Simulate tokens: reasoning... <channel|> ...narrative
        tokens = [
            "The player ",
            "input is emotional.",
            "<channel|>",
            "A cold ",
            "wind blows.",
        ]
        lines = _make_stream_lines(tokens)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.iter_lines.return_value = iter(lines)
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.object(provider.client, "stream", return_value=mock_response):
            chunks = list(provider.stream_complete([{"role": "user", "content": "cry"}]))

        full_text = "".join(chunks)
        assert "player input" not in full_text
        assert "cold" in full_text or "wind" in full_text

    def test_stream_strips_think_tags(self):
        provider = _make_provider()
        tokens = [
            "<think>",
            "reasoning here",
            "</think>",
            "The door opens.",
        ]
        lines = _make_stream_lines(tokens)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.iter_lines.return_value = iter(lines)
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.object(provider.client, "stream", return_value=mock_response):
            chunks = list(
                provider.stream_complete([{"role": "user", "content": "open door"}])
            )

        full_text = "".join(chunks)
        assert "reasoning" not in full_text
        assert "door opens" in full_text

    def test_stream_clean_content_flushes_after_buffer_limit(self):
        """Content with no thinking markers flushes after the buffer cap."""
        provider = _make_provider()
        # 90 short tokens — exceeds the 80-token buffer threshold
        tokens = [f"word{i} " for i in range(90)]
        lines = _make_stream_lines(tokens)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.iter_lines.return_value = iter(lines)
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.object(provider.client, "stream", return_value=mock_response):
            chunks = list(
                provider.stream_complete([{"role": "user", "content": "go"}])
            )

        full_text = "".join(chunks)
        assert "word0" in full_text
        assert "word89" in full_text

    def test_stream_short_clean_content_flushed_at_end(self):
        """Short content with no thinking markers flushes on stream end."""
        provider = _make_provider()
        tokens = ["Hello ", "world."]
        lines = _make_stream_lines(tokens)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.iter_lines.return_value = iter(lines)
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.object(provider.client, "stream", return_value=mock_response):
            chunks = list(
                provider.stream_complete([{"role": "user", "content": "hi"}])
            )

        full = "".join(chunks)
        assert "Hello" in full
        assert "world." in full
