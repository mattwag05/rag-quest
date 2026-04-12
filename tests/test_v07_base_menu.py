"""Tests for v0.7 /base hybrid menu: NPC stationing, service addendum, storage moves."""

from rag_quest.engine.bases import (
    SERVICE_DESCRIPTIONS,
    Base,
    build_service_prompt_addendum,
)
from rag_quest.engine.inventory import Inventory

# ---------------------------------------------------------------------------
# NPC stationing + service binding
# ---------------------------------------------------------------------------


def test_station_npc_with_service_binds_and_autoadds_service():
    b = Base(name="Ironhold", location_ref="Stonebridge")
    assert b.station_npc("Durin", service="smith") is True
    assert "Durin" in b.stationed_npcs
    assert b.npc_service["Durin"] == "smith"
    assert "smith" in b.services  # auto-registered


def test_station_npc_without_service_leaves_mapping_empty():
    b = Base(name="Ironhold", location_ref="X")
    assert b.station_npc("Mira") is True
    assert b.stationed_npcs == ["Mira"]
    assert b.npc_service == {}
    assert b.services == []


def test_station_same_npc_twice_returns_false_but_updates_role():
    b = Base(name="Ironhold", location_ref="X")
    assert b.station_npc("Durin", service="smith") is True
    assert b.station_npc("Durin", service="healer") is False  # duplicate NPC
    # But the role mapping was still updated.
    assert b.npc_service["Durin"] == "healer"
    assert b.stationed_npcs == ["Durin"]


def test_service_of_returns_empty_for_unknown_npc():
    b = Base(name="Ironhold", location_ref="X")
    assert b.service_of("nobody") == ""


def test_npcs_by_service_groups_including_unassigned():
    b = Base(name="Ironhold", location_ref="X")
    b.station_npc("Durin", service="smith")
    b.station_npc("Aelin", service="healer")
    b.station_npc("Ghost")  # unassigned
    grouped = b.npcs_by_service()
    assert grouped["smith"] == ["Durin"]
    assert grouped["healer"] == ["Aelin"]
    assert grouped[""] == ["Ghost"]


# ---------------------------------------------------------------------------
# Serialization preserves the new field
# ---------------------------------------------------------------------------


def test_base_roundtrip_preserves_npc_service_map():
    b = Base(name="Ironhold", location_ref="Stonebridge")
    b.station_npc("Durin", service="smith")
    b.station_npc("Aelin", service="healer")
    restored = Base.from_dict(b.to_dict())
    assert restored.npc_service == {"Durin": "smith", "Aelin": "healer"}
    assert restored.npcs_by_service()["smith"] == ["Durin"]
    assert restored.npcs_by_service()["healer"] == ["Aelin"]


def test_base_from_dict_backward_compat_without_npc_service():
    """v3 saves from before this commit had no `npc_service` key."""
    data = {
        "name": "Old",
        "location_ref": "X",
        "storage": {"items": {}, "max_weight": 100.0},
        "stationed_npcs": ["Durin"],
        "services": ["smith"],
        "upgrades": {},
    }
    b = Base.from_dict(data)
    assert b.stationed_npcs == ["Durin"]
    assert b.npc_service == {}
    assert b.service_of("Durin") == ""


# ---------------------------------------------------------------------------
# build_service_prompt_addendum
# ---------------------------------------------------------------------------


def test_addendum_names_base_npc_and_service():
    b = Base(name="Ironhold", location_ref="Stonebridge")
    b.station_npc("Durin", service="smith")
    text = build_service_prompt_addendum(b, "Durin", "can you repair this sword?")
    assert "Ironhold" in text
    assert "Stonebridge" in text
    assert "Durin" in text
    assert "smith" in text
    assert "can you repair this sword?" in text


def test_addendum_includes_canonical_service_description():
    b = Base(name="Ironhold", location_ref="X")
    b.station_npc("Mira", service="healer")
    text = build_service_prompt_addendum(b, "Mira", "heal me")
    # The canonical SERVICE_DESCRIPTIONS entry for healer should be present.
    assert SERVICE_DESCRIPTIONS["healer"] in text


def test_addendum_handles_unassigned_npc_with_generic_note():
    b = Base(name="Ironhold", location_ref="X")
    b.station_npc("Ghost")  # no service
    text = build_service_prompt_addendum(b, "Ghost", "hello")
    assert "general staff" in text
    assert "no bound service" in text


def test_addendum_is_deterministic():
    b = Base(name="Ironhold", location_ref="Stonebridge")
    b.station_npc("Durin", service="smith")
    first = build_service_prompt_addendum(b, "Durin", "sharpen blade")
    second = build_service_prompt_addendum(b, "Durin", "sharpen blade")
    assert first == second


# ---------------------------------------------------------------------------
# Storage transfer helpers (exercising the underlying Inventory moves)
# ---------------------------------------------------------------------------


def test_deposit_moves_item_from_inventory_to_base_storage():
    """Simulates what /base deposit does under the hood."""
    player_inv = Inventory()
    player_inv.add_item(name="iron ore", description="raw metal", quantity=5)

    base = Base(name="Ironhold", location_ref="X")
    item = player_inv.get_item("iron ore")
    assert item is not None

    # Move 3 of 5
    ok = base.storage.add_item(
        name=item.name,
        description=item.description,
        quantity=3,
        weight=item.weight,
        rarity=item.rarity,
    )
    player_inv.remove_item(item.name, quantity=3)

    assert ok is True
    assert base.storage.get_item("iron ore").quantity == 3
    assert player_inv.get_item("iron ore").quantity == 2


def test_withdraw_pulls_item_back_to_inventory():
    player_inv = Inventory()
    base = Base(name="Ironhold", location_ref="X")
    base.storage.add_item(name="healing potion", description="glow", quantity=4)

    # Withdraw 2
    item = base.storage.get_item("healing potion")
    player_inv.add_item(
        name=item.name,
        description=item.description,
        quantity=2,
        weight=item.weight,
        rarity=item.rarity,
    )
    base.storage.remove_item(item.name, quantity=2)

    assert player_inv.get_item("healing potion").quantity == 2
    assert base.storage.get_item("healing potion").quantity == 2
