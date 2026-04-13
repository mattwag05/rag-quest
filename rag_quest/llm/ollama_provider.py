"""Ollama LLM provider."""

import json
import re
from typing import Iterator, Optional

import httpx

from .base import BaseLLMProvider, LLMConfig

# ---------------------------------------------------------------------------
# Thinking / chain-of-thought stripping
# ---------------------------------------------------------------------------
#
# Several models embed reasoning directly in the content field rather than
# in the structured ``thinking`` field, even when ``think=False`` is set.
#
# Known patterns
# ~~~~~~~~~~~~~~
# Qwen 3.5 / DeepSeek-R1 / QwQ:
#     <think>...reasoning...</think>answer
#     <reasoning>...reasoning...</reasoning>answer
#
# Gemma 4 E2B / E4B (thought-channel format):
#     <|channel>thought\n...reasoning...\n<channel|>answer
#
#   The ``<|channel>thought`` token opens the thought channel and
#   ``<channel|>`` closes it.  Everything between is internal reasoning.
#   See https://ai.google.dev/gemma/docs/capabilities/thinking
#
# For **non-streaming** (complete): we strip after the full response
# arrives, so a single regex pass handles everything.
#
# For **streaming** (stream_complete): the delimiter tokens arrive mid-
# stream.  We detect the ``<|channel>thought`` opener (or ``<think>`` /
# ``<reasoning>`` tags) in early tokens and buffer until the matching
# closer, then yield only the clean narrative that follows.

_THINK_TAG_RE = re.compile(
    r"<(?:think|reasoning)>.*?</(?:think|reasoning)>",
    re.DOTALL | re.IGNORECASE,
)

# Gemma 4 thought-channel: everything from ``<|channel>thought`` up to
# and including ``<channel|>``.  The ``<|channel>thought`` marker may be
# followed by a newline or whitespace before the reasoning body.
_THOUGHT_CHANNEL_RE = re.compile(
    r"<\|channel>thought.*?<channel\|>",
    re.DOTALL,
)

# Fallback: bare ``<channel|>`` without a matching ``<|channel>thought``
# opener — strip everything before the delimiter.  This catches cases
# where Ollama strips the opener but leaves the closer.
_BARE_CHANNEL_CLOSE_RE = re.compile(r".*?<channel\|>", re.DOTALL)

# Streaming opener detection: does the text contain a thinking-block
# start marker?  Used to decide whether to enter full-buffer mode.
_STREAM_OPENER_RE = re.compile(
    r"<\|channel>thought|<think|<reasoning",
    re.IGNORECASE,
)


def _strip_thinking(text: str) -> str:
    """Remove embedded thinking / reasoning blocks from LLM output.

    Handles Qwen/DeepSeek ``<think>`` tags, Gemma 4 thought-channel
    blocks, and bare ``<channel|>`` fallback.
    """
    text = _THINK_TAG_RE.sub("", text)
    text = _THOUGHT_CHANNEL_RE.sub("", text)
    # If a bare ``<channel|>`` remains (no matching opener was found),
    # strip everything before it.
    text = _BARE_CHANNEL_CLOSE_RE.sub("", text)
    return text.strip()


def _has_thinking_markers(text: str) -> bool:
    """Return True if *text* contains any thinking/delimiter patterns."""
    return bool(
        _THINK_TAG_RE.search(text)
        or _THOUGHT_CHANNEL_RE.search(text)
        or _BARE_CHANNEL_CLOSE_RE.search(text)
    )


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
        JSON object with ``message.content`` holding the next token chunk.
        The final object has ``done: true`` with empty content.

        **Thinking-strip state machine** — models like Gemma 4 E2B may
        ignore ``think=False`` and emit a thought-channel block::

            <|channel>thought\\n...reasoning...\\n<channel|>narrative

        The streamer detects the opener token (``<|channel>thought``,
        ``<think>``, or ``<reasoning>``) within the first few tokens and
        buffers everything until the matching closer (``<channel|>``,
        ``</think>``, ``</reasoning>``).  Only the clean narrative after
        the closer is yielded.  If no opener is detected within the first
        ``_DETECTION_LIMIT`` tokens, the content is assumed clean and
        streamed directly.

        Same thinking-model safety net as ``complete()``: if the model
        emits a reasoning block with empty content, we fall back to the
        trailing paragraph of the thinking text.
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
        # Phase 1 ("detection"): buffer the first tokens while we decide
        #   whether the model is emitting chain-of-thought.
        #   • If an opener token (<|channel>thought, <think>, <reasoning>)
        #     is detected → enter phase 2 (full-buffer).
        #   • If a closer appears in the same window → strip and flush,
        #     go to phase 3 (passthrough).
        #   • If _DETECTION_LIMIT tokens pass with no opener → content is
        #     clean; flush buffer and go to phase 3.
        #
        # Phase 2 ("full_buffer"): opener was found, waiting for closer.
        #   Buffer indefinitely until <channel|> / </think> / </reasoning>
        #   appears.  On closer, strip the thinking block from the joined
        #   buffer, yield whatever clean text remains, and go to phase 3.
        #
        # Phase 3 ("passthrough"): thinking is resolved.  Yield every
        #   subsequent token directly.

        content_buffer: list[str] = []
        phase = "detection"  # "detection" | "full_buffer" | "passthrough"
        _DETECTION_LIMIT = 10  # tokens to inspect before deciding

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

                        # Check for a completed thinking block (opener +
                        # closer both present) — strip and flush.
                        if _has_thinking_markers(joined):
                            cleaned = _strip_thinking(joined)
                            phase = "passthrough"
                            if cleaned:
                                yielded_any_content = True
                                yield cleaned
                            content_buffer.clear()
                            continue

                        if phase == "detection":
                            # Look for an opener token to commit to
                            # full buffering.
                            if _STREAM_OPENER_RE.search(joined):
                                phase = "full_buffer"
                            elif len(content_buffer) >= _DETECTION_LIMIT:
                                # No opener found — clean narrative.
                                phase = "passthrough"
                                yielded_any_content = True
                                yield joined
                                content_buffer.clear()
                        # phase == "full_buffer": keep accumulating
                        # until the closer arrives.

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
