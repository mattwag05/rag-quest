"""Regression tests for rag-quest-rkg: ``?fields=`` query-param projection
on both the streaming and non-streaming turn endpoints.

Contract:

- Default requests (no ``fields`` param) return the full state dict —
  backwards compatible with existing clients.
- ``?fields=a,b,c`` returns only those top-level keys from the state
  dict, skipping missing ones silently.
- Projection applies to the ``state`` field only. ``state_change``,
  ``pre_turn``, and ``post_turn`` are untouched.
- Empty / whitespace-only / duplicate fields are cleaned up by the
  parser.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

from conftest import wire_turn_subsystems  # noqa: E402

from rag_quest.engine.state_parser import StateChange  # noqa: E402
from rag_quest.web.app import (  # noqa: E402
    SessionStore,
    _parse_fields,
    _project_state,
    app,
)

# ---- Unit tests for the helpers ----------------------------------------------


def test_parse_fields_none_returns_none() -> None:
    assert _parse_fields(None) is None
    assert _parse_fields("") is None


def test_parse_fields_splits_and_strips() -> None:
    assert _parse_fields("a,b,c") == ["a", "b", "c"]
    assert _parse_fields(" a , b , c ") == ["a", "b", "c"]


def test_parse_fields_drops_empties_and_dedups() -> None:
    assert _parse_fields("a,,b,a,,c") == ["a", "b", "c"]


def test_parse_fields_only_empties_is_none() -> None:
    assert _parse_fields(",,,") is None


def test_project_state_none_returns_unchanged() -> None:
    state = {"character": {}, "world": {}, "inventory": {}}
    assert _project_state(state, None) is state


def test_project_state_returns_subset() -> None:
    state = {"character": "c", "world": "w", "inventory": "i", "turn_number": 7}
    projected = _project_state(state, ["character", "turn_number"])
    assert projected == {"character": "c", "turn_number": 7}


def test_project_state_silently_skips_missing_keys() -> None:
    state = {"character": "c"}
    assert _project_state(state, ["character", "missing"]) == {"character": "c"}


# ---- HTTP tests for both endpoints -------------------------------------------


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture(autouse=True)
def _isolate_session_store():
    app.state.sessions = SessionStore()
    yield
    app.state.sessions = SessionStore()


def _make_stub(state_dict: dict) -> MagicMock:
    """A MagicMock GameState that returns a stable state_dict via to_dict."""
    gs = MagicMock(name="game_state")
    gs.turn_number = state_dict.get("turn_number", 0)
    gs.narrator = MagicMock(name="narrator")
    gs.narrator.process_action.return_value = "..."
    gs.narrator.stream_action.return_value = iter(["hi"])
    gs.narrator.last_change = StateChange()
    gs.to_dict.return_value = state_dict
    wire_turn_subsystems(gs)
    return gs


def test_post_turn_default_returns_full_state(client) -> None:
    full = {
        "character": {"name": "Hero"},
        "world": {"name": "Test"},
        "inventory": {"items": {}},
        "turn_number": 3,
    }
    app.state.sessions.put("alpha", _make_stub(full))

    resp = client.post("/session/alpha/turn", json={"input": "look"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == full


def test_post_turn_with_fields_projects_state(client) -> None:
    full = {
        "character": {"name": "Hero"},
        "world": {"name": "Test"},
        "inventory": {"items": {"sword": 1}},
        "quest_log": {"quests": []},
        "turn_number": 3,
    }
    app.state.sessions.put("alpha", _make_stub(full))

    resp = client.post(
        "/session/alpha/turn?fields=character,turn_number",
        json={"input": "look"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == {"character": {"name": "Hero"}, "turn_number": 3}
    # Non-state fields are never projected
    assert "state_change" in body
    assert "pre_turn" in body
    assert "post_turn" in body


def test_stream_turn_default_returns_full_state(client) -> None:
    full = {
        "character": {"name": "Hero"},
        "world": {"name": "Test"},
        "inventory": {"items": {}},
        "turn_number": 3,
    }
    app.state.sessions.put("alpha", _make_stub(full))

    with client.stream("GET", "/session/alpha/turn/stream?input=look") as resp:
        assert resp.status_code == 200
        body = b"".join(resp.iter_bytes()).decode()

    done_event = _extract_done_event(body)
    assert done_event["state"] == full


def test_stream_turn_with_fields_projects_state(client) -> None:
    full = {
        "character": {"name": "Hero"},
        "world": {"name": "Test"},
        "inventory": {"items": {}},
        "quest_log": {"quests": []},
        "turn_number": 5,
    }
    app.state.sessions.put("alpha", _make_stub(full))

    with client.stream(
        "GET",
        "/session/alpha/turn/stream?input=look&fields=character,turn_number",
    ) as resp:
        assert resp.status_code == 200
        body = b"".join(resp.iter_bytes()).decode()

    done_event = _extract_done_event(body)
    assert done_event["state"] == {
        "character": {"name": "Hero"},
        "turn_number": 5,
    }


def _extract_done_event(sse_body: str) -> dict:
    """Parse an SSE response body and return the `done` event payload."""
    for chunk in sse_body.split("\n\n"):
        chunk = chunk.strip()
        if not chunk.startswith("data: "):
            continue
        payload = json.loads(chunk[len("data: ") :])
        if payload.get("type") == "done":
            return payload
    raise AssertionError(f"no done event in SSE body: {sse_body!r}")
