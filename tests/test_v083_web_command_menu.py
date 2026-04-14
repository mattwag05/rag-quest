"""Tests for v0.8.3 web command menus.

Covers three new endpoints and the static HTML extension:

- POST /session/{id}/save       — write game_state to disk
- POST /session/{id}/bookmark   — capture narrator.last_response as a Bookmark
- GET  /session/{id}/notes      — read notetaker entries
- static HTML — command bar + panel modal + contextual visibility hooks
"""

import importlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

# rag_quest/web/__init__.py re-exports ``app`` (the FastAPI instance) as
# an attribute, which shadows the ``rag_quest.web.app`` submodule name.
# ``importlib.import_module`` bypasses the ambiguity and gives us the
# module object — the one we want for monkeypatching ``SaveManager``.
web_app = importlib.import_module("rag_quest.web.app")
from rag_quest.saves.manager import SaveManager, SaveSlot  # noqa: E402
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


def _make_saveable_game_state(
    *,
    slot_id: str | None = "slot-uuid-1",
    to_dict_payload: dict | None = None,
) -> MagicMock:
    gs = MagicMock(name="game_state")
    gs.turn_number = 7
    gs.world = SimpleNamespace(name="Ashfall")
    gs.slot_id = slot_id
    gs.to_dict.return_value = to_dict_payload or {
        "turn_number": 7,
        "character": {"name": "Hero"},
        "world": {"name": "Ashfall"},
    }
    return gs


def test_save_endpoint_routes_through_save_manager(client, tmp_path, monkeypatch):
    """POST /save calls SaveManager.save_game(slot_id=...) for the session.

    This is the core dbs regression guard — the endpoint must use the
    unified slot layout instead of writing directly to a flat path.
    """
    gs = _make_saveable_game_state(slot_id="slot-uuid-1")
    app.state.sessions.put("Ashfall", gs)

    captured: dict = {}

    def _fake_save_game(self, state_dict, slot_id=None, **kwargs):
        captured["state_dict"] = state_dict
        captured["slot_id"] = slot_id
        return SaveSlot(
            slot_id=slot_id,
            name="Hero - Ashfall",
            character_name="Hero",
            character_level=1,
            world_name="Ashfall",
            turn_number=7,
            created_at="2026-04-13T00:00:00",
            updated_at="2026-04-13T00:00:07",
            playtime_seconds=0.0,
        )

    monkeypatch.setattr(SaveManager, "save_game", _fake_save_game)
    monkeypatch.setattr(
        SaveManager,
        "save_paths_for",
        lambda self, sid: SimpleNamespace(
            slot_dir=tmp_path / sid,
            state=tmp_path / sid / "state.json",
            metadata=tmp_path / sid / "metadata.json",
            world_db=tmp_path / sid / "world.db",
        ),
    )

    response = client.post("/session/Ashfall/save")

    assert response.status_code == 200
    body = response.json()
    assert body["saved"] is True
    assert body["session_id"] == "Ashfall"
    assert body["slot_id"] == "slot-uuid-1"
    assert body["turn"] == 7
    assert body["path"].endswith(str(tmp_path / "slot-uuid-1" / "state.json"))

    # The endpoint must pass the slot_id kwarg so SaveManager updates in
    # place instead of minting a fresh UUID.
    assert captured["slot_id"] == "slot-uuid-1"
    assert captured["state_dict"] == gs.to_dict.return_value


def test_save_endpoint_404_for_unknown_session(client):
    response = client.post("/session/nope/save")
    assert response.status_code == 404
    assert "nope" in response.json()["detail"]


def test_save_endpoint_500_when_session_missing_slot_id(client):
    """A session in the store without a slot_id is an inconsistent state."""
    gs = _make_saveable_game_state(slot_id=None)
    app.state.sessions.put("Ashfall", gs)

    response = client.post("/session/Ashfall/save")
    assert response.status_code == 500
    assert "slot_id" in response.json()["detail"]


def test_save_endpoint_500_bubbles_disk_errors(client, monkeypatch):
    """OSError from SaveManager surfaces as a 500 with the error text."""
    gs = _make_saveable_game_state(slot_id="slot-uuid-1")
    app.state.sessions.put("Ashfall", gs)

    def _boom(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(SaveManager, "save_game", _boom)

    response = client.post("/session/Ashfall/save")
    assert response.status_code == 500
    assert "disk full" in response.json()["detail"]


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
