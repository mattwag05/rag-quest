"""Tests for GET /session/{id}/turn/stream (SSE streaming turn).

Covers:
- happy path: yields chunk events and a terminal done event with
  state_change + state, increments turn_number
- 404 when the session id is unknown (no stream opens)
- 400 when the input query param is empty/whitespace (no stream)
- done event still fires when the underlying stream raises mid-way
  (exception is swallowed via log_swallowed_exc and the done payload
  reflects whatever state the narrator ended up in)
- skips empty chunks that the narrator yields
"""

import json

import pytest

pytest.importorskip("fastapi")

from unittest.mock import MagicMock  # noqa: E402

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


def _parse_sse_events(raw_body: str) -> list[dict]:
    """Parse an SSE response body into a list of decoded JSON payloads."""
    events = []
    for block in raw_body.strip().split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data:"):
                data = line[len("data:") :].strip()
                events.append(json.loads(data))
    return events


def _game_state_with_streaming_narrator(
    *,
    chunks: list[str],
    state_change: StateChange | None = None,
    state_dict: dict | None = None,
    turn_number: int = 0,
    raise_mid: bool = False,
) -> MagicMock:
    gs = MagicMock(name="game_state")
    gs.turn_number = turn_number
    gs.narrator = MagicMock(name="narrator")
    gs.narrator.last_change = state_change
    gs.to_dict.return_value = state_dict or {"turn_number": turn_number + 1}

    def _streamer(_input):
        for i, chunk in enumerate(chunks):
            if raise_mid and i == len(chunks) // 2:
                raise RuntimeError("simulated mid-stream failure")
            yield chunk

    gs.narrator.stream_action.side_effect = _streamer
    return gs


def test_stream_happy_path(client):
    change = StateChange(location="Deep Woods", items_gained=["Map"])
    gs = _game_state_with_streaming_narrator(
        chunks=["You walk", " into the", " deep woods."],
        state_change=change,
        state_dict={"turn_number": 1, "loc": "Deep Woods"},
        turn_number=0,
    )
    app.state.sessions.put("alpha", gs)

    response = client.get("/session/alpha/turn/stream", params={"input": "go forest"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse_events(response.text)
    chunk_events = [e for e in events if e["type"] == "chunk"]
    done_events = [e for e in events if e["type"] == "done"]

    assert [e["text"] for e in chunk_events] == [
        "You walk",
        " into the",
        " deep woods.",
    ]
    assert len(done_events) == 1
    done = done_events[0]
    assert done["state_change"]["location"] == "Deep Woods"
    assert done["state_change"]["items_gained"] == ["Map"]
    assert done["state"] == {"turn_number": 1, "loc": "Deep Woods"}

    gs.narrator.stream_action.assert_called_once_with("go forest")
    assert gs.turn_number == 1  # incremented after stream


def test_stream_404_for_unknown_session(client):
    response = client.get("/session/nope/turn/stream", params={"input": "look"})
    assert response.status_code == 404


def test_stream_400_for_empty_input(client):
    gs = _game_state_with_streaming_narrator(chunks=["hello"])
    app.state.sessions.put("alpha", gs)

    response = client.get("/session/alpha/turn/stream", params={"input": ""})
    assert response.status_code == 400

    response_ws = client.get("/session/alpha/turn/stream", params={"input": "  \t "})
    assert response_ws.status_code == 400

    gs.narrator.stream_action.assert_not_called()


def test_stream_swallows_mid_stream_failure_and_still_emits_done(client):
    gs = _game_state_with_streaming_narrator(
        chunks=["First chunk.", " CRASH point.", " Should never emit."],
        raise_mid=True,
        turn_number=5,
    )
    app.state.sessions.put("alpha", gs)

    response = client.get("/session/alpha/turn/stream", params={"input": "x"})
    assert response.status_code == 200

    events = _parse_sse_events(response.text)
    chunk_events = [e for e in events if e["type"] == "chunk"]
    done_events = [e for e in events if e["type"] == "done"]

    # Only chunks emitted before the raise should appear.
    assert [e["text"] for e in chunk_events] == ["First chunk."]
    # done event still fires — clients can always rely on it arriving.
    assert len(done_events) == 1
    assert gs.turn_number == 6  # turn still incremented


def test_stream_skips_empty_chunks(client):
    gs = _game_state_with_streaming_narrator(
        chunks=["real", "", "   ", "also real"],
    )
    app.state.sessions.put("alpha", gs)

    response = client.get("/session/alpha/turn/stream", params={"input": "go"})
    assert response.status_code == 200

    events = _parse_sse_events(response.text)
    chunk_texts = [e["text"] for e in events if e["type"] == "chunk"]
    # Empty strings are skipped; whitespace-only chunks still come
    # through because the narrator's contract treats them as meaningful.
    assert "" not in chunk_texts
    assert "real" in chunk_texts
    assert "also real" in chunk_texts
