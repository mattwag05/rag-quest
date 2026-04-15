"""LightRAG wrapper for world knowledge."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from lightrag import LightRAG, QueryParam

from ..llm import BaseLLMProvider, LLMConfig
from .chunking import RAGProfileConfig


class WorldRAG:
    """Manages world knowledge using LightRAG with configurable profiles."""

    def __init__(
        self,
        world_name: str,
        llm_config: LLMConfig,
        llm_provider: BaseLLMProvider,
        rag_profile: str = "balanced",
    ):
        self.world_name = world_name
        self.llm_config = llm_config
        self.llm_provider = llm_provider
        self.rag_profile = rag_profile
        self.profile_config = RAGProfileConfig(rag_profile)

        # Set up working directory
        self.data_dir = Path.home() / ".local/share/rag-quest/worlds" / world_name
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Cache directory for file hashes
        self.cache_dir = self.data_dir / ".ingestion_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

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
        @wrap_embedding_func_with_attrs(
            embedding_dim=768, model_name="nomic-embed-text-v2-moe"
        )
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
                            json={
                                "model": "nomic-embed-text-v2-moe:latest",
                                "prompt": text,
                            },
                        )
                        response.raise_for_status()
                        embedding = response.json()["embedding"]
                        embeddings.append(embedding)
                    except Exception:
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
        """Ingest text into the knowledge graph with profile-aware chunking."""
        if not self.initialized:
            self.initialize()

        # Split text into chunks appropriate for the profile
        from .chunking import TextChunker

        chunker = TextChunker(self.rag_profile)
        chunks = chunker.chunk_text(text)

        # Ingest each chunk
        for i, chunk in enumerate(chunks):
            try:
                # Run insert asynchronously in thread
                self._run_async(self.rag.ainsert(chunk))
            except Exception as e:
                # Log but don't crash on chunk ingestion failure
                print(f"[!] Warning: Failed to ingest chunk {i} from {source}: {e}")
                continue

    def ingest_file(self, path: str) -> None:
        """Ingest a file into the knowledge graph with caching and smart chunking."""
        from .ingest import ingest_file as process_file
        from .ingest import (
            save_ingest_hash,
            should_re_ingest,
        )

        # Check if file has changed since last ingestion
        if not should_re_ingest(path, self.cache_dir):
            print(
                f"[*] Skipping {Path(path).name} (already ingested, no changes detected)"
            )
            return

        print(f"[*] Ingesting {Path(path).name} with {self.rag_profile} profile...")
        text = process_file(path, profile=self.rag_profile)
        self.ingest_text(text, source=Path(path).name)

        # Save hash for future change detection
        save_ingest_hash(path, self.cache_dir)

    def query_world(
        self, question: str, context: str = "", param: Optional[str] = None
    ) -> str:
        """Query the world knowledge graph with profile-optimized settings."""
        if not self.initialized:
            self.initialize()

        # Use profile's preferred query mode if not specified
        if param is None:
            param = self.profile_config.get_query_mode()

        full_query = question
        if context:
            full_query = f"{context}\n\nQuestion: {question}"

        # Create QueryParam with profile-optimized settings
        query_param = QueryParam(
            mode=param,
            top_k=self.profile_config.get_top_k(),
            chunk_top_k=self.profile_config.get_chunk_top_k(),
        )

        # Run query asynchronously in thread
        try:
            result = self._run_async(self.rag.aquery(full_query, param=query_param))
            return result
        except Exception as e:
            # Graceful fallback if query fails
            print(f"[!] Warning: RAG query failed: {e}")
            return ""

    def close(self) -> None:
        """Clean up resources."""
        if self.rag:
            try:
                self._run_async(self.rag.finalize_storages())
            except Exception as e:
                # Finalization failure is non-fatal at shutdown, but we log it
                # so that reproducible tear-down bugs aren't invisible.
                print(f"[!] WorldRAG.close: finalize_storages failed: {e}")
        self.executor.shutdown(wait=True)
        self.initialized = False
