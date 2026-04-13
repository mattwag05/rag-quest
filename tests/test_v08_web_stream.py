"""Tests for GET /session/{id}/turn/stream (SSE streaming turn).

Covers:
- happy path: yields pre_turn + chunk + done events, increments turn_number
- 404 when the session id is unknown (no stream opens)
- 400 when the input query param is empty/whitespace (no stream)
- done event still fires when the underlying stream raises mid-way
  (exception is swallowed via log_swallowed_exc and the done payload
  reflects whatever state the narrator ended up in)
- skips empty chunks that the narrator yields
- parity with the CLI: pre_turn carries world events, post_turn carries
  module transitions + achievements, timeline is recorded
"""

import json
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")

from unittest.mock import MagicMock  # noqa: E402

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
    wire_turn_subsystems(gs)

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


# ----- CLI parity: SSE must carry the same side effects as POST /turn -----


def test_stream_emits_pre_turn_event_before_chunks(client):
    fake_event = SimpleNamespace(
        name="Dark Storm",
        description="A storm rolls in from the east.",
    )
    gs = _game_state_with_streaming_narrator(chunks=["You", " look."])
    gs.events.check_for_events.return_value = fake_event
    gs.events.expire_events.return_value = ["Festival of Light"]
    gs.party.check_loyalty_departures.return_value = ["Gus"]
    app.state.sessions.put("alpha", gs)

    response = client.get("/session/alpha/turn/stream", params={"input": "look"})
    assert response.status_code == 200

    events = _parse_sse_events(response.text)
    pre_events = [e for e in events if e["type"] == "pre_turn"]
    chunk_events = [e for e in events if e["type"] == "chunk"]
    done_events = [e for e in events if e["type"] == "done"]

    assert len(pre_events) == 1
    pre = pre_events[0]
    assert pre["new_event"] == {
        "name": "Dark Storm",
        "description": "A storm rolls in from the east.",
    }
    assert pre["expired_events"] == ["Festival of Light"]
    assert pre["departed_party_members"] == ["Gus"]

    # ordering: pre_turn arrives before any chunks and before done
    all_types = [e["type"] for e in events]
    assert all_types.index("pre_turn") < all_types.index("chunk")
    assert all_types.index("chunk") < all_types.index("done")
    assert len(chunk_events) == 2
    assert len(done_events) == 1


def test_stream_done_payload_carries_module_and_achievement_transitions(client):
    unlocked_module = SimpleNamespace(
        id="tomb",
        title="The Lost Tomb",
        status=SimpleNamespace(value="available"),
    )
    unlocked_ach = SimpleNamespace(id="explorer", name="Explorer", icon="🗺️")

    change = StateChange(location="Deep Woods")
    gs = _game_state_with_streaming_narrator(chunks=["You go."], state_change=change)
    gs.world.module_registry.reevaluate.return_value = [unlocked_module]
    gs.achievements.check_achievements.return_value = [unlocked_ach]
    app.state.sessions.put("alpha", gs)

    response = client.get("/session/alpha/turn/stream", params={"input": "go"})
    assert response.status_code == 200

    events = _parse_sse_events(response.text)
    done = next(e for e in events if e["type"] == "done")

    assert done["post_turn"]["module_transitions"] == [
        {"id": "tomb", "title": "The Lost Tomb", "status": "available"}
    ]
    assert done["post_turn"]["achievements_unlocked"] == [
        {"id": "explorer", "name": "Explorer", "icon": "🗺️"}
    ]
    assert done["state_change"]["location"] == "Deep Woods"
    gs.timeline.record_from_state_change.assert_called_once()


def test_stream_post_turn_still_fires_when_narrator_crashes(client):
    """Mid-stream crash swallowed via log_swallowed_exc — post-turn
    subsystems (module gating, achievements) must still run so a web
    player doesn't lose progress on a flaky LLM."""
    gs = _game_state_with_streaming_narrator(
        chunks=["A", "B", "C"], raise_mid=True, turn_number=0
    )
    unlocked_module = SimpleNamespace(
        id="m", title="m", status=SimpleNamespace(value="completed")
    )
    gs.world.module_registry.reevaluate.return_value = [unlocked_module]
    app.state.sessions.put("alpha", gs)

    response = client.get("/session/alpha/turn/stream", params={"input": "x"})
    assert response.status_code == 200

    events = _parse_sse_events(response.text)
    done = next(e for e in events if e["type"] == "done")
    assert done["post_turn"]["module_transitions"] == [
        {"id": "m", "title": "m", "status": "completed"}
    ]
    gs.world.module_registry.reevaluate.assert_called_once()
