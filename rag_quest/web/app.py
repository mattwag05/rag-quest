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

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path
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


def _serialize_state_change(change) -> dict:
    """Safely turn a StateChange into a JSON-friendly dict.

    Returns ``{}`` when there is no change — matches the pre-v0.8 wire
    format so existing clients/tests stay green."""
    if change is None:
        return {}
    try:
        return dataclasses.asdict(change)
    except TypeError:
        # Not a dataclass instance (e.g. test mock) — fall back to a
        # best-effort dict view so the payload stays serializable.
        return dict(getattr(change, "__dict__", {}))


def _serialize_pre_turn(pre) -> dict:
    """Serialize PreTurnEffects for the wire.

    ``new_event`` is a ``WorldEvent`` (or ``None``); we surface only the
    name + description because those are all the web client needs to
    render a banner. Full event state is available via
    ``game_state.events`` if a caller needs it.
    """
    event = pre.new_event
    new_event = None
    if event is not None:
        new_event = {
            "name": event.name,
            "description": event.description,
        }
    return {
        "new_event": new_event,
        "expired_events": list(pre.expired_events),
        "departed_party_members": list(pre.departed_party_members),
    }


def _serialize_post_turn(post) -> dict:
    """Serialize PostTurnEffects for the wire.

    Modules and achievements are projected to the minimum fields a
    client needs — the full state is always available via
    ``/session/{id}/state`` if a UI wants to drill in.
    """
    modules = []
    for m in post.module_transitions:
        modules.append(
            {
                "id": m.id,
                "title": m.title,
                "status": m.status.value,
            }
        )
    achievements = []
    for a in post.achievements_unlocked:
        achievements.append(
            {
                "id": a.id,
                "name": a.name,
                "icon": a.icon,
            }
        )
    return {
        "module_transitions": modules,
        "achievements_unlocked": achievements,
    }


def _require_fastapi() -> None:
    from importlib.util import find_spec

    if find_spec("fastapi") is None:
        raise ImportError(_INSTALL_HINT)


# ---------------------------------------------------------------------------
# Save path resolution (v0.8.3)
#
# The CLI and web onboarding write flat files to ``saves/{world_name}.json``
# while ``sessions.load_session_from_slot`` reads slot-dir layouts at
# ``saves/{uuid}/state.json`` via ``SaveManager``. The two layouts coexist
# today (tracked by rag-quest-dbs) — until that's unified, the /save endpoint
# has to detect which layout the session was loaded from and write back to
# whichever path exists. These module-level helpers are monkeypatched from
# tests to keep filesystem work injectable.
# ---------------------------------------------------------------------------


def _web_saves_dir() -> Path:
    """Directory where both save layouts live. Monkeypatched in tests."""
    return Path.home() / ".local" / "share" / "rag-quest" / "saves"


def _resolve_save_path(session_id: str, game_state) -> Path:
    """Pick the on-disk save path to use for this session.

    Priority:
      1. Flat file ``saves/{session_id}.json`` if it already exists
         (onboarding / CLI layout).
      2. Slot dir ``saves/{session_id}/state.json`` if it already exists
         (``/session/load`` layout).
      3. Fall back to flat file named after ``game_state.world.name`` —
         matches what the onboarding endpoint writes on first save.
    """
    saves_dir = _web_saves_dir()
    flat = saves_dir / f"{session_id}.json"
    if flat.exists():
        return flat
    slot_state = saves_dir / session_id / "state.json"
    if slot_state.exists():
        return slot_state
    world_name = getattr(getattr(game_state, "world", None), "name", None) or session_id
    return saves_dir / f"{world_name}.json"


def _write_save_file(path: Path, payload: dict) -> None:
    """Write a game_state dict to the resolved save path.

    Kept as a module-level helper so tests can monkeypatch it to simulate
    disk failures without touching the real filesystem.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


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

    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import StreamingResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel

    from ..engine.turn import (
        advance_one_turn,
        collect_post_turn_effects,
        collect_pre_turn_effects,
    )

    instance = FastAPI(
        title="RAG-Quest",
        version=__version__,
        description="Thin HTTP surface over the CLI engine.",
    )
    instance.state.sessions = SessionStore()

    class LoadSessionRequest(BaseModel):
        slot_id: str

    class TurnRequest(BaseModel):
        input: str

    class NewSessionRequest(BaseModel):
        character_name: str
        race: str
        character_class: str
        template_id: Optional[str] = None
        world_name: Optional[str] = None
        world_setting: Optional[str] = None
        world_tone: Optional[str] = None

    class BookmarkRequest(BaseModel):
        note: Optional[str] = ""

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

    @instance.post("/session/{session_id}/turn")
    def take_turn(session_id: str, payload: TurnRequest) -> dict:
        store: SessionStore = instance.state.sessions
        game_state = store.get(session_id)
        if game_state is None:
            raise HTTPException(
                status_code=404, detail=f"No active session with id {session_id!r}"
            )
        if not payload.input.strip():
            raise HTTPException(status_code=400, detail="Input cannot be empty")

        # Full parity with the CLI turn loop via the shared helper:
        # turn increment → event check/expire → party loyalty → narrator
        # → timeline → module gating → achievements. Narrator.process_action
        # swallows its own exceptions and returns a fallback string on
        # failure, so the web endpoint never sees a traceback and the
        # client always gets a valid response body.
        result = advance_one_turn(game_state, payload.input)

        # Reuse the state dict that ``collect_post_turn_effects`` already
        # serialized for ``check_achievements`` instead of calling
        # ``game_state.to_dict()`` a second time (rag-quest-dqr). Fall
        # back to a fresh serialization only if the cached dict failed.
        state_payload = result.post.state_dict
        if state_payload is None:
            state_payload = game_state.to_dict()

        return {
            "response": result.response,
            "state_change": _serialize_state_change(result.post.state_change),
            "pre_turn": _serialize_pre_turn(result.pre),
            "post_turn": _serialize_post_turn(result.post),
            "state": state_payload,
        }

    @instance.get("/session/{session_id}/turn/stream")
    def take_turn_stream(
        session_id: str,
        player_input: str = Query(..., alias="input"),
    ) -> "StreamingResponse":
        # GET + query-string so browser EventSource (which only speaks
        # GET) can consume the stream directly. Validation fires BEFORE
        # the generator starts so error responses stay synchronous HTTP
        # codes instead of partial event streams.
        store: SessionStore = instance.state.sessions
        game_state = store.get(session_id)
        if game_state is None:
            raise HTTPException(
                status_code=404, detail=f"No active session with id {session_id!r}"
            )
        if not player_input.strip():
            raise HTTPException(status_code=400, detail="Input cannot be empty")

        def _event_stream():
            # Pre-turn side effects fire before the first chunk so the
            # client can render world-event banners up top.
            pre = collect_pre_turn_effects(game_state)
            pre_payload = {"type": "pre_turn", **_serialize_pre_turn(pre)}
            yield f"data: {json.dumps(pre_payload)}\n\n"

            try:
                for chunk in game_state.narrator.stream_action(player_input):
                    if not chunk:
                        continue
                    yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
            except Exception:
                from .._debug import log_swallowed_exc

                log_swallowed_exc("web.turn.stream")

            # Post-turn runs whether or not the stream raised — matching
            # the CLI contract that timeline/module/achievement checks
            # are additive and never blocked by a flaky narrator.
            post = collect_post_turn_effects(game_state, player_input)
            # Same optimization as the non-streaming path: reuse the
            # state dict that post-turn effects already computed for
            # the achievements check (rag-quest-dqr).
            state_payload = post.state_dict
            if state_payload is None:
                state_payload = game_state.to_dict()
            done_payload = {
                "type": "done",
                "state_change": _serialize_state_change(post.state_change),
                "post_turn": _serialize_post_turn(post),
                "state": state_payload,
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        return StreamingResponse(_event_stream(), media_type="text/event-stream")

    # ---- Onboarding endpoints (new game creation) ----

    @instance.get("/onboarding/races")
    def list_races() -> list[dict]:
        from .onboarding import RACES

        return RACES

    @instance.get("/onboarding/classes")
    def list_classes() -> list[dict]:
        from .onboarding import CLASSES

        return CLASSES

    @instance.get("/onboarding/templates")
    def list_templates() -> list[dict]:
        from .onboarding import TEMPLATES

        return TEMPLATES

    @instance.post("/session/new")
    def create_session(payload: NewSessionRequest) -> dict:
        from .onboarding import OnboardingError, create_new_session

        try:
            game_state = create_new_session(
                character_name=payload.character_name,
                race=payload.race,
                character_class=payload.character_class,
                template_id=payload.template_id,
                world_name=payload.world_name,
                world_setting=payload.world_setting,
                world_tone=payload.world_tone,
            )
        except OnboardingError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        session_id = game_state.world.name
        store: SessionStore = instance.state.sessions
        store.put(session_id, game_state)
        return {
            "session_id": session_id,
            "world": game_state.world.name,
            "character": game_state.character.name,
            "turn_number": game_state.turn_number,
        }

    # --- v0.8.3: command-menu endpoints -------------------------------------
    # These are the only mutating actions surfaced by the new command bar.
    # Navigation panels read the cached state dict client-side, so they
    # don't need their own endpoints.

    @instance.post("/session/{session_id}/save")
    def save_session(session_id: str) -> dict:
        store: SessionStore = instance.state.sessions
        game_state = store.get(session_id)
        if game_state is None:
            raise HTTPException(
                status_code=404, detail=f"No active session with id {session_id!r}"
            )

        # Module-level indirection so tests can monkeypatch the resolver
        # and the write helper without touching the real filesystem.
        path = _resolve_save_path(session_id, game_state)
        try:
            _write_save_file(path, game_state.to_dict())
        except OSError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return {
            "saved": True,
            "session_id": session_id,
            "path": str(path),
            "turn": game_state.turn_number,
        }

    @instance.post("/session/{session_id}/bookmark")
    def add_session_bookmark(session_id: str, payload: BookmarkRequest) -> dict:
        store: SessionStore = instance.state.sessions
        game_state = store.get(session_id)
        if game_state is None:
            raise HTTPException(
                status_code=404, detail=f"No active session with id {session_id!r}"
            )

        prose = (
            getattr(getattr(game_state, "narrator", None), "last_response", "") or ""
        )
        if not prose:
            raise HTTPException(
                status_code=400,
                detail="Nothing to bookmark yet — take a turn first.",
            )

        from datetime import datetime

        from ..engine.timeline import Bookmark

        narrator = getattr(game_state, "narrator", None)
        location = getattr(getattr(game_state, "character", None), "location", "") or ""
        bm = Bookmark(
            turn=int(getattr(game_state, "turn_number", 0) or 0),
            timestamp=datetime.now().isoformat(timespec="seconds"),
            note=(payload.note or "").strip(),
            player_input=getattr(narrator, "last_player_input", "") or "",
            narrator_prose=prose,
            location=location,
        )
        game_state.timeline.add_bookmark(bm)
        return {"bookmark": bm.to_dict()}

    @instance.get("/session/{session_id}/notes")
    def get_session_notes(session_id: str) -> dict:
        store: SessionStore = instance.state.sessions
        game_state = store.get(session_id)
        if game_state is None:
            raise HTTPException(
                status_code=404, detail=f"No active session with id {session_id!r}"
            )

        notetaker = getattr(game_state, "notetaker", None)
        if notetaker is None:
            return {"entries": []}

        entries = []
        for entry in getattr(notetaker, "entries", []) or []:
            try:
                entries.append(entry.to_dict())
            except Exception:
                # Zero-traceback policy: a malformed entry degrades to
                # omission rather than a 500.
                continue
        return {"entries": entries}

    # Mount the static web client last so it cannot shadow API routes.
    # FastAPI matches routes in definition order, and StaticFiles with
    # ``html=True`` serves ``index.html`` at the mount point.
    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        instance.mount(
            "/",
            StaticFiles(directory=str(static_dir), html=True),
            name="static",
        )

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
