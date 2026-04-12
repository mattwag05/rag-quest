"""Ollama LLM provider."""

from typing import Optional

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

    def close(self):
        """Close the HTTP client."""
        self.client.close()
