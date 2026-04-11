"""LightRAG wrapper for world knowledge."""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

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
        self.executor = ThreadPoolExecutor(max_workers=1)

    def _run_async(self, coro):
        """Run an async coroutine in the thread pool executor."""
        def run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        
        return self.executor.submit(run_in_thread).result()
    
    def initialize(self) -> None:
        """Initialize LightRAG instance."""
        if self.initialized:
            return

        import httpx
        import numpy as np
        from lightrag.utils import wrap_embedding_func_with_attrs
        
        # Create embedding function for Ollama's nomic embedding model
        @wrap_embedding_func_with_attrs(embedding_dim=768, model_name="nomic-embed-text-v2-moe")
        async def ollama_embed(texts, embedding_dim=768):
            """Embed texts using Ollama's nomic embedding model."""
            if isinstance(texts, str):
                texts = [texts]
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                embeddings = []
                
                for text in texts:
                    try:
                        response = await client.post(
                            "http://localhost:11434/api/embeddings",
                            json={"model": "nomic-embed-text-v2-moe:latest", "prompt": text}
                        )
                        response.raise_for_status()
                        embedding = response.json()["embedding"]
                        embeddings.append(embedding)
                    except Exception as e:
                        # Return zero vector on error
                        embeddings.append([0.0] * embedding_dim)
                
                return np.array(embeddings)
        
        self.rag = LightRAG(
            working_dir=str(self.data_dir),
            llm_model_func=self.llm_provider.lightrag_complete_func(),
            embedding_func=ollama_embed,
        )
        
        # Initialize storages in thread executor
        self._run_async(self.rag.initialize_storages())
        
        self.initialized = True

    def ingest_text(self, text: str, source: str = "lore") -> None:
        """Ingest text into the knowledge graph."""
        if not self.initialized:
            self.initialize()

        # Run insert asynchronously in thread
        self._run_async(self.rag.ainsert(text))

    def ingest_file(self, path: str) -> None:
        """Ingest a file into the knowledge graph."""
        from .ingest import ingest_file as process_file

        text = process_file(path)
        self.ingest_text(text, source=Path(path).name)

    def query_world(
        self, question: str, context: str = "", param: str = "hybrid"
    ) -> str:
        """Query the world knowledge graph."""
        if not self.initialized:
            self.initialize()

        full_query = question
        if context:
            full_query = f"{context}\n\nQuestion: {question}"

        # Run query asynchronously in thread
        result = self._run_async(self.rag.aquery(full_query, param=param))
        return result

    def record_event(self, event: str) -> None:
        """Record a new game event in the knowledge graph."""
        if not self.initialized:
            self.initialize()

        # Record game event in RAG system asynchronously
        self._run_async(self.rag.ainsert(f"GAME EVENT: {event}"))

    def close(self) -> None:
        """Clean up resources."""
        if self.rag:
            # Finalize storages if they need it
            try:
                self._run_async(self.rag.finalize_storages())
            except:
                pass
        self.executor.shutdown(wait=True)
        self.initialized = False
