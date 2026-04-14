"""Unit tests for ``rag_quest.knowledge.memory_assembler.MemoryAssembler``.

v0.9 Phase 2. Real on-disk ``WorldDB`` (per-test ``tmp_path``) so the
assembler exercises the actual SQL read API; ``WorldRAG`` is mocked
because its real implementation needs LightRAG + an embedding model
which we explicitly do not want under unit tests.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from rag_quest.knowledge.memory_assembler import (
    PROFILES,
    AssemblyProfile,
    MemoryAssembler,
)
from rag_quest.knowledge.world_db import EntityType, EventType, WorldDB

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def world_db(tmp_path):
    db = WorldDB(tmp_path / "world.db")
    yield db
    db.close()


@pytest.fixture
def mock_world_rag():
    rag = MagicMock()
    rag.query_world.return_value = "Millhaven sits at the river fork."
    return rag


def _fake_game_state(location: str = "Millhaven", hp: int = 22, max_hp: int = 30):
    """Minimal duck-typed GameState for assembler.assemble().

    The assembler only needs `.character.location`, `.character.current_hp`,
    `.character.max_hp`, and `.character.name` — keep this in sync with
    `MemoryAssembler._format_current_state`.
    """
    character = SimpleNamespace(
        name="Hero",
        location=location,
        current_hp=hp,
        max_hp=max_hp,
    )
    return SimpleNamespace(character=character, turn_number=10)


# ---------------------------------------------------------------------------
# Step 1: reference extraction
# ---------------------------------------------------------------------------


def test_extract_references_finds_seeded_npc(world_db, mock_world_rag):
    world_db.upsert_entity(EntityType.NPC.value, "Gareth", turn=1, location="Millhaven")
    assembler = MemoryAssembler(world_db, mock_world_rag, profile="balanced")

    refs = assembler._extract_entity_references("I greet Gareth")

    assert "gareth" in [r.lower() for r in refs]


def test_extract_references_returns_empty_for_no_matches(world_db, mock_world_rag):
    assembler = MemoryAssembler(world_db, mock_world_rag, profile="balanced")

    refs = assembler._extract_entity_references("I look around")

    assert refs == []


def test_extract_references_dedupes_canonical(world_db, mock_world_rag):
    world_db.upsert_entity(EntityType.NPC.value, "Gareth", turn=1)
    assembler = MemoryAssembler(world_db, mock_world_rag, profile="balanced")

    refs = assembler._extract_entity_references("Gareth! Gareth, please listen")

    assert len([r for r in refs if r.lower() == "gareth"]) == 1


# ---------------------------------------------------------------------------
# Step 2: entity snapshots
# ---------------------------------------------------------------------------


def test_assemble_with_empty_db_returns_structured_block(world_db, mock_world_rag):
    assembler = MemoryAssembler(world_db, mock_world_rag, profile="balanced")

    block = assembler.assemble("I look around", _fake_game_state())

    assert "## CURRENT STATE" in block
    assert "Millhaven" in block
    assert "## PLAYER ACTION" in block
    assert "I look around" in block


def test_assemble_renders_relationship_disposition(world_db, mock_world_rag):
    world_db.upsert_entity(EntityType.NPC.value, "Gareth", turn=1, location="Millhaven")
    world_db.set_relationship(
        "player", "Gareth", "disposition", -0.5, turn=2, cause="argued"
    )
    assembler = MemoryAssembler(world_db, mock_world_rag, profile="balanced")

    block = assembler.assemble("I greet Gareth", _fake_game_state())

    assert "Gareth" in block
    assert "hostile" in block.lower() or "-0.5" in block


# ---------------------------------------------------------------------------
# Step 3: recent events
# ---------------------------------------------------------------------------


def test_assemble_includes_recent_events(world_db, mock_world_rag):
    for turn in range(1, 13):
        world_db.record_event(
            turn=turn,
            event_type=EventType.TRAVEL.value,
            summary=f"Walked from room {turn} to room {turn + 1}",
            location="Millhaven",
        )
    assembler = MemoryAssembler(world_db, mock_world_rag, profile="balanced")

    block = assembler.assemble("I keep walking", _fake_game_state())

    assert "## RECENT EVENTS" in block
    assert "Walked from room 12" in block
    assert "Walked from room 11" in block


def test_profile_overrides_recent_turns_count(world_db, mock_world_rag):
    for turn in range(1, 21):
        world_db.record_event(
            turn=turn,
            event_type=EventType.TRAVEL.value,
            summary=f"step {turn}",
        )

    fast = MemoryAssembler(world_db, mock_world_rag, profile="fast")
    balanced = MemoryAssembler(world_db, mock_world_rag, profile="balanced")
    deep = MemoryAssembler(world_db, mock_world_rag, profile="deep")

    fast_block = fast.assemble("hi", _fake_game_state())
    balanced_block = balanced.assemble("hi", _fake_game_state())
    deep_block = deep.assemble("hi", _fake_game_state())

    fast_count = fast_block.count("step ")
    balanced_count = balanced_block.count("step ")
    deep_count = deep_block.count("step ")

    assert fast_count == 5
    assert balanced_count == 10
    assert deep_count == 15


# ---------------------------------------------------------------------------
# Step 6: lore via WorldRAG
# ---------------------------------------------------------------------------


def test_assemble_calls_world_rag_exactly_once(world_db, mock_world_rag):
    assembler = MemoryAssembler(world_db, mock_world_rag, profile="balanced")

    assembler.assemble("I look around", _fake_game_state())

    assert mock_world_rag.query_world.call_count == 1


def test_assemble_omits_world_rag_when_none(world_db):
    assembler = MemoryAssembler(world_db, world_rag=None, profile="balanced")

    block = assembler.assemble("I look around", _fake_game_state())

    assert "## WORLD LORE" not in block


def test_assemble_swallows_world_rag_exception(world_db, mock_world_rag):
    mock_world_rag.query_world.side_effect = RuntimeError("LightRAG offline")
    assembler = MemoryAssembler(world_db, mock_world_rag, profile="balanced")

    block = assembler.assemble("I look around", _fake_game_state())

    assert "## CURRENT STATE" in block
    assert "## WORLD LORE" not in block


def test_assemble_renders_world_rag_lore(world_db, mock_world_rag):
    mock_world_rag.query_world.return_value = "The Iron Guild controls metalwork."
    assembler = MemoryAssembler(world_db, mock_world_rag, profile="balanced")

    block = assembler.assemble("I enter the forge", _fake_game_state())

    assert "## WORLD LORE" in block
    assert "Iron Guild" in block


# ---------------------------------------------------------------------------
# Step 7: budgeting + truncation
# ---------------------------------------------------------------------------


def test_recent_events_never_dropped_under_budget_pressure(world_db, mock_world_rag):
    mock_world_rag.query_world.return_value = "L" * 5000
    for turn in range(1, 11):
        world_db.record_event(
            turn=turn,
            event_type=EventType.TRAVEL.value,
            summary=f"step {turn}",
        )
    assembler = MemoryAssembler(world_db, mock_world_rag, profile="balanced")

    block = assembler.assemble("hi", _fake_game_state())

    for turn in range(1, 11):
        assert f"step {turn}" in block


def test_player_action_always_present(world_db, mock_world_rag):
    assembler = MemoryAssembler(world_db, mock_world_rag, profile="balanced")

    block = assembler.assemble("I draw my sword and charge", _fake_game_state())

    assert "## PLAYER ACTION" in block
    assert "I draw my sword and charge" in block


# ---------------------------------------------------------------------------
# Profile registry
# ---------------------------------------------------------------------------


def test_profiles_registered():
    assert "fast" in PROFILES
    assert "balanced" in PROFILES
    assert "deep" in PROFILES
    for name, profile in PROFILES.items():
        assert isinstance(profile, AssemblyProfile)
        assert profile.name == name


def test_unknown_profile_falls_back_to_balanced(world_db, mock_world_rag):
    assembler = MemoryAssembler(world_db, mock_world_rag, profile="nonsense")

    assert assembler.profile.name == "balanced"
