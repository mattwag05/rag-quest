"""Integration test: StateChange → collect_post_turn_effects → WorldDB.

Exercises the v0.9 Phase 1 shadow-write hook in
``rag_quest.engine.turn.collect_post_turn_effects``. No LLM, no LightRAG,
no network — a ``MagicMock``-wired GameState with a real WorldDB attached,
a handcrafted ``StateChange`` on the narrator, and a single call into the
shared turn helper.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from conftest import wire_turn_subsystems  # noqa: E402

from rag_quest.engine.state_parser import StateChange  # noqa: E402
from rag_quest.engine.turn import collect_post_turn_effects  # noqa: E402
from rag_quest.knowledge.world_db import WorldDB  # noqa: E402


@pytest.fixture()
def world_db(tmp_path) -> WorldDB:
    db = WorldDB(tmp_path / "integration.db")
    yield db
    db.close()


def _wired_game_state(world_db: WorldDB, *, turn: int = 42) -> MagicMock:
    gs = MagicMock(name="game_state")
    wire_turn_subsystems(gs)
    gs.character = SimpleNamespace(location="Millhaven")
    gs.turn_number = turn
    gs.world_db = world_db
    return gs


def test_shadow_write_populates_entities_and_events(world_db):
    gs = _wired_game_state(world_db)

    change = StateChange(
        location="Iron Forge",
        damage_taken=5,
        items_gained=["Sword of Flames"],
        quest_offered="Recover the Lost Shipment",
        npc_met="Gareth",
        npc_relationship_change={"Gareth": -20},
    )
    gs.narrator = SimpleNamespace(last_change=change)

    post = collect_post_turn_effects(gs, player_input="attack the forge")

    # Sanity: the helper still populates the usual post-turn bookkeeping.
    assert post.state_change is change

    # Entities upserted via the shadow-write path.
    assert world_db.get_entity("Iron Forge", "location") is not None
    assert world_db.get_entity("Sword of Flames", "item") is not None
    assert world_db.get_entity("Gareth", "npc") is not None
    # The relationship write auto-creates the player entity.
    assert world_db.get_entity("player", "npc") is not None

    # Events recorded, ordered newest-first.
    events = world_db.get_recent_events(20)
    assert len(events) >= 5
    summaries = {e["summary"] for e in events}
    assert "Travelled to Iron Forge" in summaries
    assert "Took 5 damage" in summaries
    assert "Obtained Sword of Flames" in summaries
    assert "Quest offered: Recover the Lost Shipment" in summaries
    assert "Met Gareth" in summaries

    # Combat event is flagged notable; the healing path would not be.
    combat_events = world_db.get_events_by_type("combat")
    assert any(e["is_notable"] for e in combat_events)

    # Relationship delta folded into the canonical absolute `disposition`
    # row via read-modify-write (rag-quest-678). With no prior row the
    # baseline is 0.0, so a -20 delta normalizes to -0.4.
    rel = world_db.get_relationship("player", "Gareth", "disposition")
    assert rel is not None
    assert pytest.approx(rel["value"], abs=1e-6) == -0.4
    # The old split rel_type must not exist any more.
    assert world_db.get_relationship("player", "Gareth", "disposition_delta") is None


def test_shadow_write_no_op_when_change_is_none(world_db):
    gs = _wired_game_state(world_db)
    gs.narrator = SimpleNamespace(last_change=None)

    collect_post_turn_effects(gs, player_input="look around")

    assert world_db.get_recent_events(5) == []


def test_shadow_write_survives_db_failure(world_db, monkeypatch):
    """A broken WorldDB method must not kill the turn helper."""
    gs = _wired_game_state(world_db)

    # Sabotage the record_event path — the swallow block in turn.py should
    # log-and-continue. The caller still gets a valid PostTurnEffects.
    def broken(*args, **kwargs):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(world_db, "record_event", broken)

    change = StateChange(location="Doomed Keep")
    gs.narrator = SimpleNamespace(last_change=change)

    post = collect_post_turn_effects(gs, player_input="enter")
    assert post.state_change is change
    # Entity upserts are on a separate call so they still land.
    assert world_db.get_entity("Doomed Keep", "location") is not None
