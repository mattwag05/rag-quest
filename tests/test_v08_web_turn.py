"""Tests for POST /session/{id}/turn (non-streaming).

Covers:
- happy path: calls narrator.process_action, increments turn_number,
  serializes state_change via dataclasses.asdict, returns to_dict()
- 404 when the session id is unknown
- 400 when the input is empty or whitespace-only
- state_change is an empty dict when narrator.last_change is None
- narrator.process_action's own fallback path still yields a 200
- parity with the CLI loop: world events, party departures, timeline
  recording, module gating, achievement unlocks all surface via the
  web endpoint so a browser player doesn't silently miss them
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

from conftest import wire_turn_subsystems  # noqa: E402

from rag_quest.engine.state_parser import StateChange  # noqa: E402
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


def _game_state_with_narrator(
    *,
    response: str = "You look around.",
    state_change: StateChange | None = None,
    state_dict: dict | None = None,
    turn_number: int = 0,
) -> MagicMock:
    gs = MagicMock(name="game_state")
    gs.turn_number = turn_number
    gs.narrator = MagicMock(name="narrator")
    gs.narrator.process_action.return_value = response
    gs.narrator.last_change = state_change
    gs.to_dict.return_value = state_dict or {
        "turn_number": turn_number + 1,
        "character": {"name": "Hero"},
    }
    wire_turn_subsystems(gs)
    return gs


def test_turn_happy_path(client):
    change = StateChange(
        location="Forest Path",
        damage_taken=0,
        items_gained=["Rusty Key"],
    )
    gs = _game_state_with_narrator(
        response="You walk to the forest.",
        state_change=change,
        turn_number=3,
    )
    app.state.sessions.put("alpha", gs)

    response = client.post("/session/alpha/turn", json={"input": "go forest"})
    assert response.status_code == 200
    body = response.json()

    assert body["response"] == "You walk to the forest."
    assert body["state_change"]["location"] == "Forest Path"
    assert body["state_change"]["items_gained"] == ["Rusty Key"]
    assert body["state_change"]["damage_taken"] == 0
    assert body["state"] == {"turn_number": 4, "character": {"name": "Hero"}}

    gs.narrator.process_action.assert_called_once_with("go forest")
    assert gs.turn_number == 4  # incremented


def test_turn_404_for_unknown_session(client):
    response = client.post("/session/nope/turn", json={"input": "look"})
    assert response.status_code == 404
    assert "nope" in response.json()["detail"]


def test_turn_400_for_empty_input(client):
    gs = _game_state_with_narrator()
    app.state.sessions.put("alpha", gs)

    response = client.post("/session/alpha/turn", json={"input": ""})
    assert response.status_code == 400

    response_ws = client.post("/session/alpha/turn", json={"input": "   \n\t "})
    assert response_ws.status_code == 400

    gs.narrator.process_action.assert_not_called()


def test_turn_with_no_state_change_returns_empty_dict(client):
    gs = _game_state_with_narrator(response="Nothing much happens.", state_change=None)
    app.state.sessions.put("alpha", gs)

    response = client.post("/session/alpha/turn", json={"input": "wait"})
    assert response.status_code == 200
    assert response.json()["state_change"] == {}


def test_turn_preserves_narrator_fallback_output(client):
    fallback = "[System] The dungeon master pauses..."
    gs = _game_state_with_narrator(response=fallback, state_change=None, turn_number=9)
    app.state.sessions.put("alpha", gs)

    response = client.post("/session/alpha/turn", json={"input": "x"})
    assert response.status_code == 200
    assert response.json()["response"] == fallback
    # turn_number increments even when the narrator falls back
    assert gs.turn_number == 10


# ----- CLI parity: POST /turn must mirror every run_game side effect -------


def test_turn_surfaces_new_world_event(client):
    """A new world event rolled during pre-turn must appear in the
    response so the browser can render a banner — same way the CLI
    prints ``[bold cyan]WORLD EVENT:[/bold cyan] ...``."""
    fake_event = SimpleNamespace(
        name="Goblin Raid",
        description="Goblins pour out of the hills.",
    )
    gs = _game_state_with_narrator(turn_number=4)
    gs.events.check_for_events.return_value = fake_event
    app.state.sessions.put("alpha", gs)

    response = client.post("/session/alpha/turn", json={"input": "look"})
    assert response.status_code == 200
    body = response.json()

    assert body["pre_turn"]["new_event"] == {
        "name": "Goblin Raid",
        "description": "Goblins pour out of the hills.",
    }
    # event_chance stays at the CLI default so pacing matches
    call = gs.events.check_for_events.call_args
    assert call.kwargs.get("event_chance") == 0.08


def test_turn_reports_expired_events_and_party_departures(client):
    gs = _game_state_with_narrator()
    gs.events.expire_events.return_value = ["Festival of Light"]
    gs.party.check_loyalty_departures.return_value = ["Bob"]
    app.state.sessions.put("alpha", gs)

    response = client.post("/session/alpha/turn", json={"input": "camp"})
    assert response.status_code == 200
    body = response.json()

    assert body["pre_turn"]["expired_events"] == ["Festival of Light"]
    assert body["pre_turn"]["departed_party_members"] == ["Bob"]


def test_turn_records_timeline_entry_from_state_change(client):
    change = StateChange(location="Forest Path", items_gained=["Rusty Key"])
    gs = _game_state_with_narrator(state_change=change, turn_number=2)
    app.state.sessions.put("alpha", gs)

    response = client.post("/session/alpha/turn", json={"input": "go forest"})
    assert response.status_code == 200

    gs.timeline.record_from_state_change.assert_called_once()
    kwargs = gs.timeline.record_from_state_change.call_args.kwargs
    assert kwargs["turn"] == 3  # post-increment
    assert kwargs["change"] is change
    assert kwargs["player_input"] == "go forest"
    assert kwargs["location"] == "Town Square"


def test_turn_surfaces_module_transitions(client):
    unlocked_module = SimpleNamespace(
        id="tomb",
        title="The Lost Tomb",
        status=SimpleNamespace(value="available"),
    )
    gs = _game_state_with_narrator()
    gs.world.module_registry.reevaluate.return_value = [unlocked_module]
    app.state.sessions.put("alpha", gs)

    response = client.post("/session/alpha/turn", json={"input": "ask about tomb"})
    assert response.status_code == 200

    transitions = response.json()["post_turn"]["module_transitions"]
    assert transitions == [
        {"id": "tomb", "title": "The Lost Tomb", "status": "available"}
    ]
    gs.world.module_registry.reevaluate.assert_called_once_with(gs.quest_log)


def test_turn_surfaces_achievement_unlocks(client):
    unlocked = SimpleNamespace(id="explorer", name="Explorer", icon="🗺️")
    gs = _game_state_with_narrator()
    gs.achievements.check_achievements.return_value = [unlocked]
    app.state.sessions.put("alpha", gs)

    response = client.post("/session/alpha/turn", json={"input": "travel north"})
    assert response.status_code == 200

    achievements = response.json()["post_turn"]["achievements_unlocked"]
    assert achievements == [{"id": "explorer", "name": "Explorer", "icon": "🗺️"}]
    # achievements receive the serialized post-turn state dict
    gs.achievements.check_achievements.assert_called_once_with(gs.to_dict())


def test_turn_pre_post_payload_is_empty_when_nothing_happens(client):
    """No event, no departures, no module changes, no achievements.
    The payload shape stays stable — clients should be able to blindly
    render ``body["pre_turn"]["expired_events"]`` without null checks."""
    gs = _game_state_with_narrator()
    app.state.sessions.put("alpha", gs)

    response = client.post("/session/alpha/turn", json={"input": "wait"})
    assert response.status_code == 200
    body = response.json()

    assert body["pre_turn"] == {
        "new_event": None,
        "expired_events": [],
        "departed_party_members": [],
    }
    assert body["post_turn"] == {
        "module_transitions": [],
        "achievements_unlocked": [],
    }
