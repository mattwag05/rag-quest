"""Tests for v0.8.3 web command menus.

Covers three new endpoints and the static HTML extension:

- POST /session/{id}/save       — write game_state to disk
- POST /session/{id}/bookmark   — capture narrator.last_response as a Bookmark
- GET  /session/{id}/notes      — read notetaker entries
- static HTML — command bar + panel modal + contextual visibility hooks
"""

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

# rag_quest/web/__init__.py re-exports ``app`` (the FastAPI instance) as
# an attribute, which shadows the ``rag_quest.web.app`` submodule name.
# ``importlib.import_module`` bypasses the ambiguity and gives us the
# module object — the one we want for monkeypatching module-level
# helpers like ``_resolve_save_path``.
web_app = importlib.import_module("rag_quest.web.app")
from rag_quest.web.app import SessionStore, app  # noqa: E402


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture(autouse=True)
def _isolate_session_store():
    app.state.sessions = SessionStore()
    yield
    app.state.sessions = SessionStore()


# ---------------------------------------------------------------------------
# POST /session/{id}/save
# ---------------------------------------------------------------------------


def _make_saveable_game_state(*, to_dict_payload: dict | None = None) -> MagicMock:
    gs = MagicMock(name="game_state")
    gs.turn_number = 7
    gs.world = SimpleNamespace(name="Ashfall")
    gs.to_dict.return_value = to_dict_payload or {
        "turn_number": 7,
        "character": {"name": "Hero"},
        "world": {"name": "Ashfall"},
    }
    return gs


def test_save_endpoint_writes_game_state_to_resolved_path(
    client, tmp_path, monkeypatch
):
    gs = _make_saveable_game_state()
    app.state.sessions.put("Ashfall", gs)

    target = tmp_path / "Ashfall.json"
    monkeypatch.setattr(
        web_app, "_resolve_save_path", lambda session_id, game_state: target
    )

    response = client.post("/session/Ashfall/save")

    assert response.status_code == 200
    body = response.json()
    assert body["saved"] is True
    assert body["session_id"] == "Ashfall"
    assert body["turn"] == 7
    assert body["path"].endswith("Ashfall.json")

    assert target.exists()
    on_disk = json.loads(target.read_text())
    assert on_disk == gs.to_dict.return_value


def test_save_endpoint_404_for_unknown_session(client):
    response = client.post("/session/nope/save")
    assert response.status_code == 404
    assert "nope" in response.json()["detail"]


def test_save_endpoint_500_bubbles_to_user_friendly_error(
    client, tmp_path, monkeypatch
):
    gs = _make_saveable_game_state()
    app.state.sessions.put("Ashfall", gs)

    def _boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(
        web_app,
        "_resolve_save_path",
        lambda session_id, game_state: tmp_path / "x.json",
    )
    monkeypatch.setattr(web_app, "_write_save_file", _boom)

    response = client.post("/session/Ashfall/save")
    assert response.status_code == 500
    assert "disk full" in response.json()["detail"]


def test_resolve_save_path_prefers_existing_flat_file(tmp_path, monkeypatch):
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir()
    flat = saves_dir / "Ashfall.json"
    flat.write_text("{}")

    monkeypatch.setattr(web_app, "_web_saves_dir", lambda: saves_dir)

    gs = _make_saveable_game_state()
    path = web_app._resolve_save_path("Ashfall", gs)
    assert path == flat


def test_resolve_save_path_prefers_existing_slot_dir(tmp_path, monkeypatch):
    saves_dir = tmp_path / "saves"
    slot_dir = saves_dir / "abc-123"
    slot_dir.mkdir(parents=True)
    (slot_dir / "state.json").write_text("{}")

    monkeypatch.setattr(web_app, "_web_saves_dir", lambda: saves_dir)

    gs = _make_saveable_game_state()
    path = web_app._resolve_save_path("abc-123", gs)
    assert path == slot_dir / "state.json"


def test_resolve_save_path_falls_back_to_flat_by_world_name(tmp_path, monkeypatch):
    saves_dir = tmp_path / "saves"

    monkeypatch.setattr(web_app, "_web_saves_dir", lambda: saves_dir)

    gs = _make_saveable_game_state()
    path = web_app._resolve_save_path("brand-new-session-id", gs)
    # Neither flat nor slot dir exists: fall back to flat-by-world-name
    # since that's the onboarding layout used for fresh sessions.
    assert path == saves_dir / "Ashfall.json"


# ---------------------------------------------------------------------------
# POST /session/{id}/bookmark
# ---------------------------------------------------------------------------


def _make_bookmarkable_game_state(
    *, last_response: str = "The dragon roars."
) -> MagicMock:
    gs = MagicMock(name="game_state")
    gs.turn_number = 12
    gs.character = SimpleNamespace(location="Ember Hall")
    gs.narrator = MagicMock(name="narrator")
    gs.narrator.last_response = last_response
    gs.timeline = MagicMock(name="timeline")
    gs.timeline.bookmarks = []

    def _add(bm):
        gs.timeline.bookmarks.append(bm)

    gs.timeline.add_bookmark.side_effect = _add
    return gs


def test_bookmark_endpoint_happy_path(client):
    gs = _make_bookmarkable_game_state(last_response="You find a hidden door.")
    app.state.sessions.put("Ashfall", gs)

    response = client.post("/session/Ashfall/bookmark", json={"note": "hidden door"})
    assert response.status_code == 200
    body = response.json()

    assert body["bookmark"]["turn"] == 12
    assert body["bookmark"]["note"] == "hidden door"
    assert body["bookmark"]["narrator_prose"] == "You find a hidden door."
    assert body["bookmark"]["location"] == "Ember Hall"

    gs.timeline.add_bookmark.assert_called_once()
    added = gs.timeline.add_bookmark.call_args.args[0]
    assert added.turn == 12
    assert added.note == "hidden door"


def test_bookmark_endpoint_accepts_empty_note(client):
    gs = _make_bookmarkable_game_state()
    app.state.sessions.put("Ashfall", gs)

    response = client.post("/session/Ashfall/bookmark", json={})
    assert response.status_code == 200
    assert response.json()["bookmark"]["note"] == ""


def test_bookmark_endpoint_400_when_no_narrator_response(client):
    gs = _make_bookmarkable_game_state(last_response="")
    app.state.sessions.put("Ashfall", gs)

    response = client.post("/session/Ashfall/bookmark", json={"note": "early"})
    assert response.status_code == 400
    assert "turn" in response.json()["detail"].lower()
    gs.timeline.add_bookmark.assert_not_called()


def test_bookmark_endpoint_404_for_unknown_session(client):
    response = client.post("/session/nope/bookmark", json={"note": "x"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /session/{id}/notes
# ---------------------------------------------------------------------------


def test_notes_endpoint_returns_entries(client):
    gs = MagicMock(name="game_state")
    entry = MagicMock(name="entry")
    entry.to_dict.return_value = {
        "turn_range": "1-5",
        "session_summary": "Hero met the innkeeper.",
        "npc_notes": ["Innkeeper seemed nervous."],
        "open_hooks": ["What is the innkeeper hiding?"],
        "faction_shifts": [],
        "created_at": "2026-04-13T10:00:00",
        "canonized": False,
    }
    gs.notetaker = MagicMock(name="notetaker")
    gs.notetaker.entries = [entry]
    app.state.sessions.put("Ashfall", gs)

    response = client.get("/session/Ashfall/notes")
    assert response.status_code == 200
    body = response.json()
    assert len(body["entries"]) == 1
    assert body["entries"][0]["session_summary"] == "Hero met the innkeeper."


def test_notes_endpoint_empty_list_when_notetaker_missing(client):
    gs = MagicMock(name="game_state")
    gs.notetaker = None
    app.state.sessions.put("Ashfall", gs)

    response = client.get("/session/Ashfall/notes")
    assert response.status_code == 200
    assert response.json() == {"entries": []}


def test_notes_endpoint_404_for_unknown_session(client):
    response = client.get("/session/nope/notes")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Static HTML assertions
# ---------------------------------------------------------------------------


def _index_html_text() -> str:
    path = Path(web_app.__file__).parent / "static" / "index.html"
    return path.read_text()


def test_index_html_has_command_bar_toolbar():
    body = _index_html_text()
    assert 'id="command-bar"' in body
    assert 'role="toolbar"' in body
    assert 'aria-label="Game commands"' in body


def test_index_html_has_panel_modal_dialog():
    body = _index_html_text()
    assert 'id="panel-modal"' in body
    assert 'role="dialog"' in body
    assert 'aria-modal="true"' in body


@pytest.mark.parametrize(
    "panel",
    [
        "inventory",
        "stats",
        "quests",
        "party",
        "relationships",
        "timeline",
        "bookmarks",
        "lore",
        "achievements",
        "notes",
        "base",
        "modules",
        "help",
    ],
)
def test_index_html_has_panel_button(panel):
    body = _index_html_text()
    assert f'data-panel="{panel}"' in body, f"missing data-panel={panel}"


@pytest.mark.parametrize("action", ["save", "bookmark"])
def test_index_html_has_action_button(action):
    body = _index_html_text()
    assert f'data-action="{action}"' in body


def test_index_html_has_contextual_visibility_hooks():
    body = _index_html_text()
    assert 'data-requires="base"' in body
    assert 'data-requires="modules"' in body


def test_index_html_never_uses_inner_html():
    """The security hook blocks innerHTML in source files for XSS reasons.
    Regression guard: a future edit could re-introduce it. Every
    LLM/save-derived string must flow through textContent."""
    body = _index_html_text()
    assert (
        "innerHTML" not in body
    ), "index.html must not use innerHTML (use textContent)"


# ---------------------------------------------------------------------------
# Design regression guards (v0.8.3 Illuminated Terminal)
# ---------------------------------------------------------------------------
#
# These assertions are load-bearing. The aesthetic commitments in the plan
# ("IBM Plex Mono, Cormorant Garamond, wax + gold + vellum palette, no
# generic fonts") would otherwise drift over time into generic SaaS slop.
# Each failure is a signal that the Illuminated Terminal direction has
# been broken and should be restored or explicitly re-scoped.


@pytest.mark.parametrize(
    "token",
    [
        "--ink:",
        "--vellum:",
        "--wax:",
        "--gold:",
        "--rule:",
        "--font-mono:",
        "--font-serif:",
    ],
)
def test_index_html_has_design_token(token):
    assert token in _index_html_text(), f"missing design token {token}"


def test_index_html_loads_both_distinctive_fonts():
    body = _index_html_text()
    assert "IBM+Plex+Mono" in body
    assert "Cormorant+Garamond" in body
    assert "fonts.googleapis.com" in body


def test_index_html_honors_reduced_motion_preference():
    body = _index_html_text()
    assert "prefers-reduced-motion: reduce" in body


@pytest.mark.parametrize(
    "banned",
    ["Inter", "Roboto", "Arial", "Space Grotesk"],
)
def test_index_html_does_not_use_banned_generic_fonts(banned):
    """frontend-design skill: explicitly avoid these overused AI-slop fonts.

    IBM Plex Mono and Cormorant Garamond are load-bearing. If a future
    edit introduces one of the banned fonts, the Illuminated Terminal
    direction has been compromised.
    """
    import re

    body = _index_html_text()
    pattern = re.compile(r"\b" + re.escape(banned) + r"\b", re.IGNORECASE)
    assert not pattern.search(
        body
    ), f"{banned!r} is on the banned-font list for v0.8.3 Illuminated Terminal"


def test_command_bar_sigil_labels_are_uppercase():
    """Infocom-style abbreviated verbs — labels are UPPERCASE letters only."""
    import re

    body = _index_html_text()
    pattern = re.compile(
        r'<button[^>]*class="sigil[^"]*"[^>]*>\s*([^<]+?)\s*</button>',
        re.IGNORECASE,
    )
    labels = [m.group(1).strip() for m in pattern.finditer(body)]
    assert labels, "no sigil buttons found in command bar"
    for label in labels:
        assert re.fullmatch(
            r"[A-Z]+", label
        ), f"sigil label {label!r} must be uppercase letters only"
