"""Tests for the v0.8 web read-path endpoints.

Covers:
- GET /saves delegates to ``sessions.list_save_slots``
- POST /session/load hydrates a GameState via
  ``sessions.load_session_from_slot`` and parks it in the SessionStore
- POST /session/load returns 400 when hydration raises
  ``SessionLoadError``
- GET /session/{id}/state serializes the stored GameState via to_dict
- GET /session/{id}/state returns 404 for an unknown session id

The endpoint handlers lazy-import ``rag_quest.web.sessions`` inside
their function bodies, so monkeypatching attributes on that module
takes effect for every request.
"""

from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

from rag_quest.web.app import SessionStore, app  # noqa: E402
from rag_quest.web.sessions import SessionLoadError  # noqa: E402


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture(autouse=True)
def _isolate_session_store():
    """Reset the module-level app's SessionStore between tests."""
    app.state.sessions = SessionStore()
    yield
    app.state.sessions = SessionStore()


def _fake_game_state(
    *,
    world_name: str = "Test World",
    character_name: str = "Hero",
    turn_number: int = 7,
    state_dict: dict | None = None,
) -> MagicMock:
    gs = MagicMock(name="game_state")
    gs.world = MagicMock()
    gs.world.name = world_name
    gs.character = MagicMock()
    gs.character.name = character_name
    gs.turn_number = turn_number
    gs.to_dict.return_value = state_dict or {
        "world": {"name": world_name},
        "character": {"name": character_name},
        "turn_number": turn_number,
    }
    return gs


def test_list_saves_delegates_to_list_save_slots(monkeypatch, client):
    sample = [
        {
            "slot_id": "abc",
            "name": "Hero - Level 3",
            "character_name": "Hero",
            "character_level": 3,
            "world_name": "Test World",
            "turn_number": 42,
            "created_at": "2026-04-12T00:00:00",
            "updated_at": "2026-04-12T01:00:00",
            "playtime_seconds": 120.0,
        }
    ]

    from rag_quest.web import sessions as _sessions

    monkeypatch.setattr(_sessions, "list_save_slots", lambda: sample)

    response = client.get("/saves")
    assert response.status_code == 200
    assert response.json() == sample


def test_load_session_puts_game_state_in_store(monkeypatch, client):
    fake_gs = _fake_game_state(
        world_name="Neverwinter", character_name="Aria", turn_number=12
    )
    captured = {}

    def fake_load(slot_id: str):
        captured["slot_id"] = slot_id
        return fake_gs

    from rag_quest.web import sessions as _sessions

    monkeypatch.setattr(_sessions, "load_session_from_slot", fake_load)

    response = client.post("/session/load", json={"slot_id": "slot-xyz"})
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "session_id": "slot-xyz",
        "world": "Neverwinter",
        "character": "Aria",
        "turn_number": 12,
    }
    assert captured["slot_id"] == "slot-xyz"
    assert app.state.sessions.get("slot-xyz") is fake_gs


def test_load_session_400_on_session_load_error(monkeypatch, client):
    def fake_load(slot_id: str):
        raise SessionLoadError(f"No save slot with id {slot_id!r}")

    from rag_quest.web import sessions as _sessions

    monkeypatch.setattr(_sessions, "load_session_from_slot", fake_load)

    response = client.post("/session/load", json={"slot_id": "nope"})
    assert response.status_code == 400
    assert "nope" in response.json()["detail"]


def test_load_session_replacing_same_slot_closes_previous(monkeypatch, client):
    first = _fake_game_state(world_name="World A")
    second = _fake_game_state(world_name="World B")
    call_count = {"n": 0}

    def fake_load(slot_id: str):
        call_count["n"] += 1
        return first if call_count["n"] == 1 else second

    from rag_quest.web import sessions as _sessions

    monkeypatch.setattr(_sessions, "load_session_from_slot", fake_load)

    client.post("/session/load", json={"slot_id": "slot-1"})
    client.post("/session/load", json={"slot_id": "slot-1"})

    first.world_rag.close.assert_called_once()
    first.llm.close.assert_called_once()
    assert app.state.sessions.get("slot-1") is second


def test_load_session_from_slot_rebinds_narrator_references(monkeypatch):
    """Regression: after GameState.from_dict re-hydrates character /
    world / inventory / quest_log, the narrator must point to those
    hydrated instances, not the preliminary ones we built to satisfy
    its constructor. Otherwise narrator-side mutations (take_damage,
    add_item, ...) never reach the GameState the web layer serializes.
    """
    from rag_quest.web import sessions as _sessions

    save_dict = {
        "save_version": 3,
        "character": {
            "name": "Hero",
            "race": "HUMAN",
            "character_class": "FIGHTER",
            "level": 1,
            "experience": 0,
            "location": "Starting Town",
        },
        "world": {"name": "Test World", "setting": "Fantasy", "tone": "Heroic"},
        "inventory": {"items": {}},
        "quest_log": {"quests": [], "completed": []},
        "turn_number": 0,
        "playtime_seconds": 0.0,
    }

    monkeypatch.setattr(
        _sessions,
        "_load_config_dict",
        lambda: {"llm": {"provider": "ollama", "model": "stub"}, "rag": {}},
    )

    class _FakeLLM:
        def close(self):
            pass

    class _FakeRAG:
        def __init__(self, *a, **kw):
            pass

        def close(self):
            pass

    from rag_quest import config as _config
    from rag_quest.knowledge import world_rag as _wr
    from rag_quest.saves import manager as _mgr

    monkeypatch.setattr(
        _mgr.SaveManager,
        "load_game",
        lambda self, slot_id_or_world=None, slot_number=None: save_dict,
    )
    monkeypatch.setattr(
        _config,
        "load_llm_provider",
        lambda cfg: (_FakeLLM(), MagicMock(name="llm_config")),
    )
    monkeypatch.setattr(_wr, "WorldRAG", _FakeRAG)

    game_state = _sessions.load_session_from_slot("fake-slot")

    assert game_state.narrator.character is game_state.character
    assert game_state.narrator.world is game_state.world
    assert game_state.narrator.inventory is game_state.inventory
    assert game_state.narrator.quest_log is game_state.quest_log


def test_get_session_state_404_for_unknown_id(client):
    response = client.get("/session/does-not-exist/state")
    assert response.status_code == 404
    assert "does-not-exist" in response.json()["detail"]


def test_get_session_state_returns_to_dict_for_known_id(client):
    fake_gs = _fake_game_state(state_dict={"hello": "world"})
    app.state.sessions.put("alpha", fake_gs)

    response = client.get("/session/alpha/state")
    assert response.status_code == 200
    assert response.json() == {"hello": "world"}
    fake_gs.to_dict.assert_called_once()
