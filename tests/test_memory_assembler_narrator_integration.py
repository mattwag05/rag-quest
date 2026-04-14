"""Narrator-side integration for ``MemoryAssembler``.

Verifies the gating logic at ``rag_quest/engine/narrator.py``:

- when a ``MemoryAssembler`` is wired in, the narrator's system prompt
  contains the structured §4.3 block and ``WorldRAG.query_world`` is
  *not* called from the narrator (the assembler owns the lore call).
- when no assembler is wired, the legacy ``query_world`` path still
  runs so existing behavior is unchanged for users who haven't opted in.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rag_quest.engine.character import Character, CharacterClass, Race
from rag_quest.engine.narrator import Narrator
from rag_quest.engine.world import World
from rag_quest.knowledge.memory_assembler import MemoryAssembler
from rag_quest.knowledge.world_db import EntityType, WorldDB


@pytest.fixture
def character():
    return Character(
        name="Hero",
        race=Race.HUMAN,
        character_class=CharacterClass.FIGHTER,
        location="Millhaven",
    )


@pytest.fixture
def world():
    return World(name="Test World", setting="Fantasy", tone="Heroic")


@pytest.fixture
def world_db(tmp_path):
    db = WorldDB(tmp_path / "world.db")
    db.upsert_entity(EntityType.NPC.value, "Gareth", turn=1, location="Millhaven")
    yield db
    db.close()


@pytest.fixture
def fake_llm():
    llm = MagicMock()
    llm.complete.return_value = "Narrator says hi."
    return llm


@pytest.fixture
def fake_world_rag():
    rag = MagicMock()
    rag.query_world.return_value = "Some lore about Millhaven."
    return rag


def test_narrator_uses_assembler_when_wired(
    fake_llm, fake_world_rag, character, world, world_db
):
    assembler = MemoryAssembler(world_db, fake_world_rag, profile="balanced")
    narrator = Narrator(
        fake_llm, fake_world_rag, character, world, memory_assembler=assembler
    )

    narrator.process_action("I greet Gareth")

    assert fake_llm.complete.call_count == 1
    messages = fake_llm.complete.call_args[0][0]
    system_content = messages[0]["content"]
    assert "## CURRENT STATE" in system_content
    assert "## PLAYER ACTION" in system_content
    assert "Gareth" in system_content


def test_narrator_falls_back_to_world_rag_without_assembler(
    fake_llm, fake_world_rag, character, world
):
    narrator = Narrator(fake_llm, fake_world_rag, character, world)

    narrator.process_action("I look around")

    assert fake_world_rag.query_world.called
    messages = fake_llm.complete.call_args[0][0]
    system_content = messages[0]["content"]
    assert "RELEVANT WORLD LORE" in system_content
    assert "## CURRENT STATE" not in system_content


def test_narrator_assembler_takes_over_lore_call(
    fake_llm, fake_world_rag, character, world, world_db
):
    """When the assembler is wired, the narrator must not double-query LightRAG.

    The assembler owns the single ``query_world`` call per turn (Step 6).
    A second call from the narrator's legacy path would mean we're paying
    LightRAG twice and double-injecting lore.
    """
    assembler = MemoryAssembler(world_db, fake_world_rag, profile="balanced")
    narrator = Narrator(
        fake_llm, fake_world_rag, character, world, memory_assembler=assembler
    )

    narrator.process_action("I look around")

    # Exactly one call — from inside the assembler, not from the narrator.
    assert fake_world_rag.query_world.call_count == 1
