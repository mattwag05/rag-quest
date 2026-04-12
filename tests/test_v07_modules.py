"""Tests for v0.7 modules.yaml loader + ModuleRegistry."""

import textwrap
from pathlib import Path

import pytest

from rag_quest.engine.world import World
from rag_quest.worlds.modules import (
    Module,
    ModuleManifestError,
    ModuleRegistry,
    ModuleStatus,
    load_modules,
)

# ---------------------------------------------------------------------------
# load_modules
# ---------------------------------------------------------------------------


def _write_manifest(tmp_path: Path, body: str) -> Path:
    (tmp_path / "modules.yaml").write_text(textwrap.dedent(body).lstrip())
    return tmp_path


def test_load_modules_missing_manifest_returns_empty_registry(tmp_path):
    registry = load_modules(tmp_path)
    assert len(registry) == 0
    assert registry.all() == []


def test_load_modules_empty_file_returns_empty_registry(tmp_path):
    (tmp_path / "modules.yaml").write_text("")
    registry = load_modules(tmp_path)
    assert len(registry) == 0


def test_load_modules_happy_path(tmp_path):
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: goblin-cave
            title: The Goblin Cave
            description: Clear the goblins threatening the village.
            entry_location: Stonebridge
            lore_files:
              - lore/goblin-cave.md
            rewards:
              xp: 200
              items: [goblin-chief-ring]
          - id: haunted-mill
            title: The Haunted Mill
            description: Investigate the cursed mill.
            entry_location: Blackwater
            unlock_when_quests_completed: [defeat-goblin-chief]
            completion_quest: exorcise-mill
        """,
    )
    registry = load_modules(tmp_path)
    assert len(registry) == 2

    goblin = registry.get("goblin-cave")
    assert goblin is not None
    assert goblin.title == "The Goblin Cave"
    assert goblin.entry_location == "Stonebridge"
    assert goblin.rewards == {"xp": 200, "items": ["goblin-chief-ring"]}
    assert goblin.lore_files == ["lore/goblin-cave.md"]
    assert goblin.status == ModuleStatus.AVAILABLE  # empty unlock list → available

    haunted = registry.get("haunted-mill")
    assert haunted is not None
    assert haunted.unlock_when_quests_completed == ["defeat-goblin-chief"]
    assert haunted.completion_quest == "exorcise-mill"
    assert haunted.status == ModuleStatus.LOCKED  # has prereqs → locked


def test_load_modules_ingests_lore_files_when_rag_supplied(tmp_path):
    lore = tmp_path / "lore"
    lore.mkdir()
    (lore / "goblin.md").write_text("# Goblin Cave\n\nA dark cavern.")

    _write_manifest(
        tmp_path,
        """
        modules:
          - id: goblin-cave
            title: Goblin Cave
            description: Goblins.
            entry_location: Stonebridge
            lore_files:
              - lore/goblin.md
        """,
    )

    ingested = []

    class FakeWorldRAG:
        def ingest_file(self, path):
            ingested.append(path)

    registry = load_modules(tmp_path, world_rag=FakeWorldRAG())
    assert len(registry) == 1
    assert len(ingested) == 1
    assert ingested[0].endswith("goblin.md")


def test_load_modules_skips_missing_lore_file_without_crashing(tmp_path, monkeypatch):
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: goblin-cave
            title: Goblin Cave
            description: Goblins.
            entry_location: Stonebridge
            lore_files:
              - lore/does-not-exist.md
        """,
    )

    class FakeWorldRAG:
        def __init__(self):
            self.calls = 0

        def ingest_file(self, path):
            self.calls += 1

    warnings: list[str] = []
    from rag_quest import ui

    monkeypatch.setattr(ui, "print_warning", warnings.append)

    rag = FakeWorldRAG()
    registry = load_modules(tmp_path, world_rag=rag)
    assert len(registry) == 1
    assert rag.calls == 0  # skipped, not crashed
    assert any("missing lore file" in w for w in warnings)


def test_load_modules_continues_when_rag_ingest_raises(tmp_path, monkeypatch):
    lore = tmp_path / "lore"
    lore.mkdir()
    (lore / "ok.md").write_text("# ok")

    _write_manifest(
        tmp_path,
        """
        modules:
          - id: m1
            title: M1
            description: d
            entry_location: X
            lore_files:
              - lore/ok.md
        """,
    )

    class BoomRAG:
        def ingest_file(self, path):
            raise RuntimeError("boom")

    warnings: list[str] = []
    from rag_quest import ui

    monkeypatch.setattr(ui, "print_warning", warnings.append)

    registry = load_modules(tmp_path, world_rag=BoomRAG())
    assert len(registry) == 1  # loader did not crash
    assert any("failed to ingest" in w for w in warnings)


# ---------------------------------------------------------------------------
# Manifest validation errors
# ---------------------------------------------------------------------------


def test_invalid_yaml_raises_manifest_error(tmp_path):
    (tmp_path / "modules.yaml").write_text("modules:\n  - id: [unclosed")
    with pytest.raises(ModuleManifestError, match="not valid YAML"):
        load_modules(tmp_path)


def test_top_level_must_be_mapping(tmp_path):
    (tmp_path / "modules.yaml").write_text("- just a list\n- of strings")
    with pytest.raises(ModuleManifestError, match="top-level 'modules:'"):
        load_modules(tmp_path)


def test_modules_key_must_be_list(tmp_path):
    _write_manifest(tmp_path, "modules: not-a-list\n")
    with pytest.raises(ModuleManifestError, match="must be a list"):
        load_modules(tmp_path)


def test_missing_required_field_raises(tmp_path):
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: m1
            title: M1
            description: d
        """,
    )
    with pytest.raises(ModuleManifestError, match="entry_location"):
        load_modules(tmp_path)


def test_empty_required_field_raises(tmp_path):
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: m1
            title: ""
            description: d
            entry_location: X
        """,
    )
    with pytest.raises(ModuleManifestError, match="title"):
        load_modules(tmp_path)


def test_duplicate_module_id_raises(tmp_path):
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: dup
            title: A
            description: a
            entry_location: X
          - id: dup
            title: B
            description: b
            entry_location: Y
        """,
    )
    with pytest.raises(ModuleManifestError, match="Duplicate module id 'dup'"):
        load_modules(tmp_path)


def test_unknown_field_raises(tmp_path):
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: m1
            title: M1
            description: d
            entry_location: X
            typo_field: oops
        """,
    )
    with pytest.raises(ModuleManifestError, match="unknown field"):
        load_modules(tmp_path)


def test_wrong_unlock_type_raises(tmp_path):
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: m1
            title: M1
            description: d
            entry_location: X
            unlock_when_quests_completed: "defeat-boss"
        """,
    )
    with pytest.raises(ModuleManifestError, match="unlock_when_quests_completed"):
        load_modules(tmp_path)


def test_non_dict_module_entry_raises(tmp_path):
    _write_manifest(tmp_path, "modules:\n  - just_a_string\n")
    with pytest.raises(ModuleManifestError, match="must be a mapping"):
        load_modules(tmp_path)


# ---------------------------------------------------------------------------
# ModuleRegistry behavior
# ---------------------------------------------------------------------------


def test_registry_by_status_filters():
    mods = [
        Module(id="a", title="A", description="", entry_location="X"),
        Module(
            id="b",
            title="B",
            description="",
            entry_location="Y",
            unlock_when_quests_completed=["q1"],
        ),
    ]
    reg = ModuleRegistry(mods)
    available = reg.by_status(ModuleStatus.AVAILABLE)
    locked = reg.by_status(ModuleStatus.LOCKED)
    assert [m.id for m in available] == ["a"]
    assert [m.id for m in locked] == ["b"]


def test_registry_roundtrip_preserves_status():
    mods = [
        Module(
            id="a",
            title="A",
            description="",
            entry_location="X",
            status=ModuleStatus.ACTIVE,
        ),
        Module(
            id="b",
            title="B",
            description="",
            entry_location="Y",
            status=ModuleStatus.COMPLETED,
        ),
    ]
    reg = ModuleRegistry(mods)
    restored = ModuleRegistry.from_dict(reg.to_dict())
    assert restored.get("a").status == ModuleStatus.ACTIVE
    assert restored.get("b").status == ModuleStatus.COMPLETED


# ---------------------------------------------------------------------------
# World integration
# ---------------------------------------------------------------------------


def test_world_module_registry_defaults_empty():
    w = World(name="Test", setting="Fantasy", tone="Heroic")
    assert len(w.module_registry) == 0


def test_world_roundtrip_preserves_module_registry():
    w = World(name="Test", setting="Fantasy", tone="Heroic")
    w.module_registry = ModuleRegistry(
        [
            Module(
                id="goblin-cave",
                title="The Goblin Cave",
                description="Clear goblins.",
                entry_location="Stonebridge",
                status=ModuleStatus.ACTIVE,
            )
        ]
    )
    restored = World.from_dict(w.to_dict())
    assert len(restored.module_registry) == 1
    assert restored.module_registry.get("goblin-cave").status == ModuleStatus.ACTIVE


def test_world_from_dict_backward_compat_without_module_registry():
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
    assert len(w.module_registry) == 0
    assert w.bases == []
