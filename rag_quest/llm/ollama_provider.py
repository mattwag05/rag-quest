"""Ollama LLM provider."""

import json
import re
from typing import Iterator, Optional

import httpx

from .base import BaseLLMProvider, LLMConfig

# Strip reasoning / chain-of-thought that some models embed directly in
# content rather than in the structured ``thinking`` field.
#
# Covers:
#   - <think>...</think>  (Qwen 3.5, DeepSeek-R1, QwQ)
#   - <reasoning>...</reasoning>
#   - <channel|> delimiter used by some Gemma variants — everything
#     before the delimiter is internal reasoning.
_THINK_TAG_RE = re.compile(
    r"<(?:think|reasoning)>.*?</(?:think|reasoning)>",
    re.DOTALL | re.IGNORECASE,
)
_CHANNEL_DELIM_RE = re.compile(r".*?<channel\|>", re.DOTALL)

# Heuristic patterns that signal the model is emitting meta-commentary /
# chain-of-thought rather than in-character narrative.  Checked against
# the first ~20 buffered tokens to decide whether to stay in full-buffer
# mode (waiting for a delimiter) or flush early as clean narrative.
_THINKING_INDICATOR_RE = re.compile(
    r"(?:"
    r"[Tt]he player\b"
    r"|[Tt]he user\b"
    r"|I (?:need to|should|will|must|have to|want to)\b"
    r"|Let me\b"
    r"|Plan\s*:"
    r"|Step \d"
    r"|My (?:plan|approach|goal|response)\b"
    r"|First,? I"
    r"|Okay,? (?:so|let)"
    r"|Hmm"
    r"|<think"
    r"|<reasoning"
    r")",
    re.IGNORECASE,
)


def _strip_thinking(text: str) -> str:
    """Remove embedded thinking / reasoning blocks from LLM output."""
    text = _THINK_TAG_RE.sub("", text)
    text = _CHANNEL_DELIM_RE.sub("", text)
    return text.strip()


def _has_thinking_markers(text: str) -> bool:
    """Return True if *text* contains any thinking/delimiter patterns."""
    return bool(_THINK_TAG_RE.search(text) or _CHANNEL_DELIM_RE.search(text))


def _looks_like_thinking(text: str) -> bool:
    """Return True if *text* looks like model meta-commentary."""
    return bool(_THINKING_INDICATOR_RE.search(text))


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        # Ollama API endpoint for chat completions
        self.base_url = config.base_url or "http://localhost:11434"
        self.client = httpx.Client(
            timeout=120.0,
        )

    def complete(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Generate a completion from Ollama API."""
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            # Disable "thinking" mode for reasoning models (Qwen 3.5,
            # DeepSeek-R1, QwQ, etc.).  When think=True these models
            # spend the entire token budget on internal chain-of-thought
            # and return empty content.  For game narration we want
            # direct output, not hidden reasoning.
            "think": False,
            "options": {
                "temperature": temp,
                "num_predict": tokens,
            },
        }

        response = self.client.post(
            f"{self.base_url}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        content = data["message"]["content"]

        # Strip embedded thinking / reasoning from content (Gemma 4,
        # Qwen 3.5, DeepSeek-R1 may ignore think=False and inline their
        # chain-of-thought directly in the content field).
        content = _strip_thinking(content)

        # Safety net: if content is still empty and thinking was present
        # (model ignored think=False), fall back to the thinking text.
        if not content.strip() and data["message"].get("thinking"):
            thinking = data["message"]["thinking"]
            # Extract last substantive paragraph from thinking output
            paragraphs = [p.strip() for p in thinking.split("\n\n") if p.strip()]
            if paragraphs:
                content = paragraphs[-1]

        return content

    def stream_complete(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Iterator[str]:
        """Stream chat completions from Ollama as they're generated.

        Ollama's streaming protocol is line-delimited JSON: each line is a
        JSON object with `message.content` holding the next token chunk.
        The final object has `done: true` with empty content.

        Same thinking-model safety net as `complete()`: if the model ignores
        `think=False` and emits a reasoning block with empty content, we
        fall back to the trailing paragraph of the thinking text so the
        stream never produces an empty turn.
        """
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": True,
            "think": False,
            "options": {"temperature": temp, "num_predict": tokens},
        }

        thinking_buffer: list[str] = []
        yielded_any_content = False

        # --- Streaming thinking-strip state machine ---
        #
        # Phase 1 ("detection"): buffer the first ~20 tokens while we
        #   decide whether the model is emitting chain-of-thought.
        #   • If a delimiter (<channel|>, </think>, </reasoning>) appears
        #     → strip everything before it, flush the rest, go to phase 3.
        #   • If the buffered text looks like meta-commentary (heuristic)
        #     → enter phase 2 (full-buffer).
        #   • If 20 tokens pass with no indicators → flush buffer, phase 3.
        #
        # Phase 2 ("full-buffer"): the model IS thinking.  Keep
        #   buffering indefinitely until a delimiter or end-of-stream.
        #
        # Phase 3 ("passthrough"): thinking is resolved.  Yield every
        #   subsequent token directly.

        content_buffer: list[str] = []
        phase = "detection"  # "detection" | "full_buffer" | "passthrough"
        _DETECTION_LIMIT = 20  # tokens to inspect before deciding

        with self.client.stream(
            "POST", f"{self.base_url}/api/chat", json=payload
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = chunk.get("message", {}) or {}
                content = message.get("content", "")
                thinking = message.get("thinking", "")

                if content:
                    if phase == "passthrough":
                        yielded_any_content = True
                        yield content
                    else:
                        content_buffer.append(content)
                        joined = "".join(content_buffer)

                        # Always check for a completed delimiter.
                        if _has_thinking_markers(joined):
                            cleaned = _strip_thinking(joined)
                            phase = "passthrough"
                            if cleaned:
                                yielded_any_content = True
                                yield cleaned
                            content_buffer.clear()
                            continue

                        if phase == "detection":
                            if _looks_like_thinking(joined):
                                # Meta-commentary detected — commit to
                                # full buffering until delimiter or EOS.
                                phase = "full_buffer"
                            elif len(content_buffer) >= _DETECTION_LIMIT:
                                # Enough clean tokens — this is genuine
                                # narrative.  Flush and stream directly.
                                phase = "passthrough"
                                yielded_any_content = True
                                yield joined
                                content_buffer.clear()
                        # phase == "full_buffer": keep accumulating.

                if thinking:
                    thinking_buffer.append(thinking)
                if chunk.get("done"):
                    break

        # Flush any remaining buffered content through the stripper.
        if content_buffer:
            joined = "".join(content_buffer)
            cleaned = _strip_thinking(joined)
            if cleaned:
                yielded_any_content = True
                yield cleaned

        if not yielded_any_content and thinking_buffer:
            combined = "".join(thinking_buffer)
            paragraphs = [p.strip() for p in combined.split("\n\n") if p.strip()]
            if paragraphs:
                yield paragraphs[-1]

    def close(self):
        """Close the HTTP client."""
        self.client.close()
