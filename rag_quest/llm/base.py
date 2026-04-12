"""Abstract LLM provider base class."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Optional


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""

    provider: str  # "openai", "openrouter", "ollama"
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.8
    max_tokens: int = 1024


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    def complete(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Generate a completion from messages."""
        pass

    def stream_complete(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Iterator[str]:
        """Stream a completion as a generator of token/chunk strings.

        Default fallback: providers that haven't implemented real streaming
        produce a single-chunk iterator from `complete()`, so callers can
        always iterate without a type check. Real providers override this
        with native streaming (Ollama line-delimited JSON, OpenAI SSE).

        Callers MUST join the chunks to reconstruct the full response — the
        same state-parser pipeline runs on the concatenated output so
        mechanics stay deterministic regardless of which provider yielded
        the tokens.
        """
        full = self.complete(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        yield full

    def lightrag_complete_func(self):
        """Return a function compatible with LightRAG's llm_model_func."""

        async def func(
            prompt: str,
            system_prompt: Optional[str] = None,
            history_messages: Optional[list] = None,
            **kwargs,
        ) -> str:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if history_messages:
                messages.extend(history_messages)
            messages.append({"role": "user", "content": prompt})

            return self.complete(messages, **kwargs)

        return func
