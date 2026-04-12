"""Tests for POST /session/{id}/turn (non-streaming).

Covers:
- happy path: calls narrator.process_action, increments turn_number,
  serializes state_change via dataclasses.asdict, returns to_dict()
- 404 when the session id is unknown
- 400 when the input is empty or whitespace-only
- state_change is an empty dict when narrator.last_change is None
- narrator.process_action's own fallback path still yields a 200
"""

from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

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
