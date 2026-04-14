"""Tests for v0.7 save format v3: bases + module registry in GameState serialization.

These tests avoid constructing a full GameState (which needs Narrator/WorldRAG/LLM).
Instead they verify that (1) the constant bumped to 3, and (2) the World-level
serialization — which is what GameState.to_dict delegates to for bases and
module_registry — correctly round-trips the new fields and tolerates v2 saves.
"""

from rag_quest.engine.bases import Base
from rag_quest.engine.game import SAVE_FORMAT_VERSION
from rag_quest.engine.world import World
from rag_quest.worlds.modules import Module, ModuleRegistry, ModuleStatus


def test_save_format_version_is_at_least_three():
    """v0.7 added bases + module_registry at v3. v0.9 Phase 1 bumped to v4
    (SQLite WorldDB). The bases/modules round-trip below is what this file
    is actually guarding — the version constant just needs to stay >= 3 so
    those fields are still part of the serialized format."""
    assert SAVE_FORMAT_VERSION >= 3


def test_world_dict_contains_bases_and_module_registry():
    """Fresh v3 worlds serialize both new fields at the `world` key."""
    w = World(name="v3", setting="Fantasy", tone="Heroic")
    data = w.to_dict()
    assert "bases" in data
    assert "module_registry" in data
    assert data["bases"] == []
    assert data["module_registry"] == {"modules": []}


def test_world_v3_full_roundtrip_with_bases_and_modules():
    """Populated bases + modules round-trip through to_dict/from_dict."""
    w = World(name="v3", setting="Fantasy", tone="Heroic")
    w.bases.append(Base(name="Ironhold", location_ref="Stonebridge"))
    w.module_registry = ModuleRegistry(
        [
            Module(
                id="goblin-cave",
                title="Goblin Cave",
                description="d",
                entry_location="Stonebridge",
                status=ModuleStatus.ACTIVE,
            )
        ]
    )
    data = w.to_dict()
    restored = World.from_dict(data)
    assert len(restored.bases) == 1
    assert restored.bases[0].name == "Ironhold"
    assert len(restored.module_registry) == 1
    assert restored.module_registry.get("goblin-cave").status == ModuleStatus.ACTIVE


def test_v2_world_dict_loads_with_empty_v3_collections():
    """A v2-shape World dict (no `bases`, no `module_registry`) loads cleanly.

    Clean-break policy: v2 saves get empty collections for v3 fields. No
    retroactive migration — new features only populate on new saves.
    """
    v2_data = {
        "name": "OldSave",
        "setting": "Fantasy",
        "tone": "Heroic",
        "current_time": "MORNING",
        "weather": "CLEAR",
        "day_number": 5,
        "visited_locations": ["Stonebridge"],
        "npcs_met": ["Mira"],
        "recent_events": ["entered town"],
        "discovered_items": ["rusty sword"],
        # no `bases`
        # no `module_registry`
    }
    w = World.from_dict(v2_data)
    assert w.name == "OldSave"
    assert w.day_number == 5
    assert list(w.visited_locations) == ["Stonebridge"]
    assert w.bases == []
    assert len(w.module_registry) == 0
