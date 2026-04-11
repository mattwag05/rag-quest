"""LightRAG wrapper for world knowledge."""

import json
import os
from pathlib import Path
from typing import Optional

from lightrag import LightRAG

from ..llm import BaseLLMProvider, LLMConfig


class WorldRAG:
    """Manages world knowledge using LightRAG."""

    def __init__(
        self, world_name: str, llm_config: LLMConfig, llm_provider: BaseLLMProvider
    ):
        self.world_name = world_name
        self.llm_config = llm_config
        self.llm_provider = llm_provider

        # Set up working directory
        self.data_dir = Path.home() / ".local/share/rag-quest/worlds" / world_name
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.rag: Optional[LightRAG] = None
        self.initialized = False

    async def initialize(self) -> None:
        """Initialize LightRAG instance."""
        if self.initialized:
            return

        self.rag = LightRAG(
            working_dir=str(self.data_dir),
            llm_model_func=self.llm_provider.lightrag_complete_func(),
        )
        self.initialized = True

    async def ingest_text(self, text: str, source: str = "lore") -> None:
        """Ingest text into the knowledge graph."""
        if not self.initialized:
            await self.initialize()

        await self.rag.ainsert(
            text,
            metadata={
                "source": source,
            },
        )

    async def ingest_file(self, path: str) -> None:
        """Ingest a file into the knowledge graph."""
        from .ingest import ingest_file as process_file

        text = await process_file(path)
        await self.ingest_text(text, source=Path(path).name)

    async def query_world(
        self, question: str, context: str = "", param: str = "hybrid"
    ) -> str:
        """Query the world knowledge graph."""
        if not self.initialized:
            await self.initialize()

        full_query = question
        if context:
            full_query = f"{context}\n\nQuestion: {question}"

        result = await self.rag.aquery(full_query, param=param)
        return result

    async def record_event(self, event: str) -> None:
        """Record a new game event in the knowledge graph."""
        if not self.initialized:
            await self.initialize()

        await self.rag.ainsert(
            f"GAME EVENT: {event}",
            metadata={
                "source": "game_event",
                "type": "event",
            },
        )

    async def close(self) -> None:
        """Clean up resources."""
        if self.rag:
            # LightRAG doesn't require explicit cleanup
            pass
        self.initialized = False
