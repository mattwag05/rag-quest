"""Shared Server-Sent Events helpers for OpenAI-compatible streaming.

Both `OpenAIProvider` and `OpenRouterProvider` speak the same
`/chat/completions?stream=true` protocol: a stream of `data: { ... }`
lines terminated by `data: [DONE]`. This module factors the parsing
into one place so the two providers share one tested implementation.
"""

from __future__ import annotations

import json
from typing import Iterator

import httpx

_DONE_SENTINEL = "[DONE]"


def stream_openai_chat(client: httpx.Client, path: str, payload: dict) -> Iterator[str]:
    """Issue a streaming POST and yield text deltas from the SSE response.

    `payload` should already have `"stream": True` set. The function:
      1. Opens the response via `client.stream("POST", path, json=payload)`
      2. Iterates `response.iter_lines()`
      3. Parses each `data: <json>` event
      4. Pulls `choices[0].delta.content` and yields non-empty deltas
      5. Stops on `data: [DONE]` or a `finish_reason`

    Malformed data lines are skipped silently (OpenRouter occasionally
    emits keep-alive comments). Empty deltas (role-only events) are
    skipped. Callers join the yielded strings to reconstruct the full
    content.
    """
    with client.stream("POST", path, json=payload) as response:
        response.raise_for_status()
        for raw_line in response.iter_lines():
            if not raw_line or not raw_line.startswith("data:"):
                continue
            data = raw_line[len("data:") :].strip()
            if not data or data == _DONE_SENTINEL:
                if data == _DONE_SENTINEL:
                    return
                continue
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = event.get("choices") or []
            if not choices:
                continue
            choice = choices[0]
            delta = choice.get("delta") or {}
            content = delta.get("content")
            if content:
                yield content
            if choice.get("finish_reason"):
                return
