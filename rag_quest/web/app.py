"""FastAPI app instance + in-memory SessionStore for the web wrapper.

FastAPI is an optional dependency (``pip install '.[web]'``). Importing
this module with the extras missing leaves ``app`` as ``None``; the
``SessionStore`` dataclass itself has no FastAPI dependency and remains
usable. ``run(host, port)`` raises ``ImportError`` with a clear install
hint if the user tries to launch the server without the extras.

Note: do NOT add ``from __future__ import annotations`` to this file.
FastAPI's body-parameter detection needs real Pydantic classes at
runtime, not string forward references. Engine types (``GameState``,
``FastAPI``) use explicit string literals so the file stays
TYPE_CHECKING-only for engine imports without the future import.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from .. import __version__
from .._debug import debug_enabled

if TYPE_CHECKING:
    from fastapi import FastAPI

    from ..engine.game import GameState


_INSTALL_HINT = (
    "rag-quest web features require the optional [web] extras. "
    "Install with: pip install -e '.[web]'"
)


def _require_fastapi() -> None:
    from importlib.util import find_spec

    if find_spec("fastapi") is None:
        raise ImportError(_INSTALL_HINT)


@dataclass
class SessionStore:
    """In-memory registry of loaded campaigns keyed by save name.

    Single-user app: re-loading a save under the same name closes the
    previous session first so shared resources (``WorldRAG``, the LLM
    provider) are released cleanly instead of leaking.
    """

    _sessions: dict[str, "GameState"] = field(default_factory=dict)

    def get(self, save_name: str) -> Optional["GameState"]:
        return self._sessions.get(save_name)

    def put(self, save_name: str, game_state: "GameState") -> None:
        existing = self._sessions.get(save_name)
        if existing is not None:
            self._close_game_state(existing)
        self._sessions[save_name] = game_state

    def close(self, save_name: str) -> bool:
        existing = self._sessions.pop(save_name, None)
        if existing is None:
            return False
        self._close_game_state(existing)
        return True

    def list_names(self) -> list[str]:
        return sorted(self._sessions.keys())

    @staticmethod
    def _close_game_state(game_state: "GameState") -> None:
        from .._debug import log_swallowed_exc

        try:
            game_state.world_rag.close()
        except Exception:
            log_swallowed_exc("web.session.world_rag")
        try:
            game_state.llm.close()
        except Exception:
            log_swallowed_exc("web.session.llm")


def _build_app() -> "FastAPI":
    _require_fastapi()
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    instance = FastAPI(
        title="RAG-Quest",
        version=__version__,
        description="Thin HTTP surface over the CLI engine.",
    )
    instance.state.sessions = SessionStore()

    class LoadSessionRequest(BaseModel):
        slot_id: str

    @instance.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok", "version": __version__}

    @instance.get("/saves")
    def list_saves() -> list[dict]:
        # Lazy re-import inside the handler so test monkeypatching of
        # `rag_quest.web.sessions.list_save_slots` actually takes effect.
        from . import sessions as _s

        return _s.list_save_slots()

    @instance.post("/session/load")
    def load_session(payload: LoadSessionRequest) -> dict:
        from . import sessions as _s

        try:
            game_state = _s.load_session_from_slot(payload.slot_id)
        except _s.SessionLoadError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        store: SessionStore = instance.state.sessions
        store.put(payload.slot_id, game_state)
        return {
            "session_id": payload.slot_id,
            "world": game_state.world.name,
            "character": game_state.character.name,
            "turn_number": game_state.turn_number,
        }

    @instance.get("/session/{session_id}/state")
    def get_session_state(session_id: str) -> dict:
        store: SessionStore = instance.state.sessions
        game_state = store.get(session_id)
        if game_state is None:
            raise HTTPException(
                status_code=404, detail=f"No active session with id {session_id!r}"
            )
        return game_state.to_dict()

    return instance


try:
    app = _build_app()
except ImportError:
    app = None  # type: ignore[assignment]


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Launch uvicorn on the FastAPI app.

    Raises ``ImportError`` with the canonical install hint if the
    ``[web]`` extras are missing. Honors ``RAG_QUEST_DEBUG=1`` by
    bumping uvicorn's log level from ``info`` to ``debug``.
    """
    _require_fastapi()
    try:
        import uvicorn
    except ImportError as exc:
        raise ImportError(_INSTALL_HINT) from exc

    if app is None:
        raise RuntimeError(
            "rag_quest.web.app.app is None — did fastapi import fail at startup?"
        )
    log_level = "debug" if debug_enabled() else "info"
    uvicorn.run(app, host=host, port=port, log_level=log_level)
