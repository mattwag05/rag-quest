"""Ollama LLM provider."""

import json
from typing import Iterator, Optional

import httpx

from .base import BaseLLMProvider, LLMConfig


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
                    yielded_any_content = True
                    yield content
                if thinking:
                    thinking_buffer.append(thinking)
                if chunk.get("done"):
                    break

        if not yielded_any_content and thinking_buffer:
            combined = "".join(thinking_buffer)
            paragraphs = [p.strip() for p in combined.split("\n\n") if p.strip()]
            if paragraphs:
                yield paragraphs[-1]

    def close(self):
        """Close the HTTP client."""
        self.client.close()
