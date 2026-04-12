"""Tests for v0.7 Hub Bases: Base entity + World.bases serialization."""

from rag_quest.engine.bases import Base
from rag_quest.engine.inventory import Inventory
from rag_quest.engine.world import TimeOfDay, Weather, World


def test_base_defaults():
    b = Base(name="Ironhold", location_ref="Stonebridge")
    assert b.name == "Ironhold"
    assert b.location_ref == "Stonebridge"
    assert isinstance(b.storage, Inventory)
    assert b.stationed_npcs == []
    assert b.services == []
    assert b.upgrades == {}


def test_base_add_service_and_station_npc():
    b = Base(name="Ironhold", location_ref="Stonebridge")
    assert b.add_service("smith") is True
    assert b.add_service("SMITH") is False  # dedupe case-insensitive
    assert "smith" in b.services

    assert b.station_npc("Durin") is True
    assert b.station_npc("Durin") is False  # duplicate rejected
    assert b.stationed_npcs == ["Durin"]


def test_base_upgrade_accumulates():
    b = Base(name="Ironhold", location_ref="Stonebridge")
    assert b.upgrade("smith_level") == 1
    assert b.upgrade("smith_level") == 2
    assert b.upgrade("healer_level", delta=3) == 3
    assert b.upgrades == {"smith_level": 2, "healer_level": 3}


def test_base_roundtrip_serialization():
    b = Base(
        name="Ironhold",
        location_ref="Stonebridge",
        stationed_npcs=["Durin"],
        services=["smith", "storage"],
        upgrades={"smith_level": 2},
    )
    b.storage.add_item("iron ore", description="raw metal", quantity=5)

    data = b.to_dict()
    restored = Base.from_dict(data)

    assert restored.name == "Ironhold"
    assert restored.location_ref == "Stonebridge"
    assert restored.stationed_npcs == ["Durin"]
    assert restored.services == ["smith", "storage"]
    assert restored.upgrades == {"smith_level": 2}
    assert "iron ore" in restored.storage.items
    assert restored.storage.items["iron ore"].quantity == 5


def test_world_bases_default_empty():
    w = World(name="Test", setting="Fantasy", tone="Heroic")
    assert w.bases == []


def test_world_bases_roundtrip():
    w = World(name="Test", setting="Fantasy", tone="Heroic")
    w.bases.append(
        Base(
            name="Ironhold",
            location_ref="Stonebridge",
            services=["smith"],
        )
    )
    w.add_visited_location("Stonebridge")

    data = w.to_dict()
    assert len(data["bases"]) == 1
    assert data["bases"][0]["name"] == "Ironhold"

    restored = World.from_dict(data)
    assert len(restored.bases) == 1
    assert restored.bases[0].name == "Ironhold"
    assert restored.bases[0].services == ["smith"]
    assert "Stonebridge" in restored.visited_locations


def test_world_from_dict_backward_compat_without_bases():
    """Old saves without `bases` field should load with empty list."""
    data = {
        "name": "Old",
        "setting": "Fantasy",
        "tone": "Heroic",
        "current_time": "MORNING",
        "weather": "CLEAR",
        "day_number": 1,
        "visited_locations": [],
        "npcs_met": [],
        "recent_events": [],
        "discovered_items": [],
    }
    w = World.from_dict(data)
    assert w.bases == []
