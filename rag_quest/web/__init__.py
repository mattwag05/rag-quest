"""FastAPI web wrapper around the RAG-Quest engine.

Optional, gated behind the ``[web]`` extras. Launch via
``rag-quest serve [--host 127.0.0.1] [--port 8000]``.
"""

from .app import SessionStore, app

__all__ = ["SessionStore", "app"]
