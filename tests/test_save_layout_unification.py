"""Regression tests for rag-quest-dbs: CLI + web + autosave all route
through `SaveManager` slot directories instead of a flat
`saves/{world_name}.json` layout.

These tests operate on the disk layer only — they don't spin up the full
engine, narrator, or LightRAG. The contract under test is:

1. `SaveManager.save_paths_for(slot_id)` returns paths rooted at
   `save_dir/{slot_id}/`.
2. `SaveManager.save_game(state, slot_id=...)` updates an existing slot
   in place: same UUID, preserved `created_at`, bumped `updated_at`,
   preserved `name` when the caller doesn't override.
3. `SaveManager.list_saves()` surfaces a slot created that way — i.e.
   "CLI-minted" worlds aren't invisible to the web UI.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from rag_quest.saves.manager import SaveManager, SavePaths


def _fake_state(
    character_name: str, world_name: str, *, level: int = 1, turn: int = 0
) -> dict:
    """Minimal state dict with the fields SaveManager extracts for metadata."""
    return {
        "character": {"name": character_name, "level": level},
        "world": {"name": world_name},
        "turn_number": turn,
        "playtime_seconds": 0.0,
    }


def test_save_paths_for_is_rooted_in_slot_dir(tmp_path: Path) -> None:
    sm = SaveManager(save_dir=tmp_path)
    paths = sm.save_paths_for("abc-123")

    assert isinstance(paths, SavePaths)
    assert paths.slot_dir == tmp_path / "abc-123"
    assert paths.state == tmp_path / "abc-123" / "state.json"
    assert paths.metadata == tmp_path / "abc-123" / "metadata.json"
    assert paths.world_db == tmp_path / "abc-123" / "world.db"


def test_cli_new_game_is_visible_to_list_saves(tmp_path: Path) -> None:
    """CLI-minted worlds must show up in `SaveManager.list_saves()`.

    This is the core regression the bead tracks: before the fix, CLI
    wrote flat `saves/{world_name}.json` which `list_saves` never
    scanned, so the web UI's `GET /saves` couldn't see them.
    """
    sm = SaveManager(save_dir=tmp_path)

    # Simulate the CLI new-game path in __main__.py — mint a slot from
    # a fresh state dict.
    slot = sm.save_game(
        _fake_state("Alice", "Test World"), slot_name="Alice - Test World"
    )

    listed = sm.list_saves()
    assert len(listed) == 1
    assert listed[0].slot_id == slot.slot_id
    assert listed[0].world_name == "Test World"
    assert listed[0].character_name == "Alice"
    # Verify the slot layout matches save_paths_for
    paths = sm.save_paths_for(slot.slot_id)
    assert paths.state.exists()
    assert paths.metadata.exists()


def test_update_in_place_reuses_slot_preserves_created_at(tmp_path: Path) -> None:
    sm = SaveManager(save_dir=tmp_path)

    slot1 = sm.save_game(_fake_state("Alice", "Test", level=1, turn=0))
    time.sleep(0.01)  # ensure updated_at timestamp moves
    slot2 = sm.save_game(
        _fake_state("Alice", "Test", level=2, turn=5),
        slot_id=slot1.slot_id,
    )

    # Same slot — not a new UUID mint
    assert slot2.slot_id == slot1.slot_id
    # created_at preserved from the original save
    assert slot2.created_at == slot1.created_at
    # updated_at bumped
    assert slot2.updated_at > slot1.updated_at
    # Metadata reflects the new level + turn
    assert slot2.character_level == 2
    assert slot2.turn_number == 5
    # Slot name preserved when the caller didn't override
    assert slot2.name == slot1.name
    # Still exactly one slot on disk
    assert len(sm.list_saves()) == 1


def test_update_in_place_can_override_slot_name(tmp_path: Path) -> None:
    sm = SaveManager(save_dir=tmp_path)
    slot1 = sm.save_game(_fake_state("Alice", "Test"), slot_name="Original Label")
    slot2 = sm.save_game(
        _fake_state("Alice", "Test"),
        slot_id=slot1.slot_id,
        slot_name="New Label",
    )
    assert slot2.name == "New Label"


def test_autosave_roundtrip_matches_load_game(tmp_path: Path) -> None:
    """Simulate the autosave loop: mint a slot, update it a few times,
    verify `load_game(slot_id)` returns the latest state.
    """
    sm = SaveManager(save_dir=tmp_path)

    slot = sm.save_game(_fake_state("Bob", "Ruins", turn=0))
    sm.save_game(_fake_state("Bob", "Ruins", turn=1), slot_id=slot.slot_id)
    sm.save_game(_fake_state("Bob", "Ruins", turn=2), slot_id=slot.slot_id)

    loaded = sm.load_game(slot.slot_id)
    assert loaded is not None
    assert loaded["turn_number"] == 2
    assert loaded["character"]["name"] == "Bob"

    # Confirm the on-disk state.json matches
    state_file = sm.save_paths_for(slot.slot_id).state
    with open(state_file, "r") as f:
        disk = json.load(f)
    assert disk["turn_number"] == 2


def test_legacy_positional_save_game_still_works(tmp_path: Path) -> None:
    """Backwards compat: the old positional calling convention still mints a fresh slot."""
    sm = SaveManager(save_dir=tmp_path)

    slot = sm.save_game("Test World", 0, _fake_state("Alice", "Test World"), "Alice")
    assert slot.slot_id
    assert "Alice" in slot.name
    assert slot.world_name == "Test World"
