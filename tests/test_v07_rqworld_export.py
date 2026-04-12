"""Tests for v0.7 .rqworld exporter/importer: bases + modules.yaml bundling."""

import json
import textwrap
import zipfile
from pathlib import Path

from rag_quest import __version__
from rag_quest.engine.bases import Base
from rag_quest.engine.world import World
from rag_quest.worlds.exporter import WorldExporter
from rag_quest.worlds.importer import WorldImporter
from rag_quest.worlds.modules import (
    MANIFEST_FILENAME,
    Module,
    ModuleRegistry,
    ModuleStatus,
    load_modules,
)


def _game_state_with_bases_and_modules() -> dict:
    """Build a minimal GameState-shaped dict carrying a v3 world."""
    w = World(name="Ironhold Campaign", setting="Medieval Fantasy", tone="Heroic")
    w.bases.append(
        Base(
            name="Ironhold",
            location_ref="Stonebridge",
            services=["smith", "storage"],
        )
    )
    w.module_registry = ModuleRegistry(
        [
            Module(
                id="goblin-cave",
                title="The Goblin Cave",
                description="Clear the goblin threat.",
                entry_location="Stonebridge",
                lore_files=["lore/goblin-cave.md"],
                status=ModuleStatus.AVAILABLE,
            )
        ]
    )
    return {
        "world": w.to_dict(),
        "quest_log": {},
        "events": {},
        "relationships": {},
    }


# ---------------------------------------------------------------------------
# Bases round-trip (pure world.json path — no source_dir needed)
# ---------------------------------------------------------------------------


def test_export_then_import_preserves_bases(tmp_path):
    game_state = _game_state_with_bases_and_modules()
    out = WorldExporter.export_world(
        game_state=game_state,
        output_path=tmp_path / "campaign.rqworld",
        author="Tester",
    )
    assert out is not None and out.exists()

    parsed = WorldImporter.import_world(out)
    assert parsed is not None
    restored = World.from_dict(parsed["world"])
    assert len(restored.bases) == 1
    assert restored.bases[0].name == "Ironhold"
    assert restored.bases[0].location_ref == "Stonebridge"
    assert restored.bases[0].services == ["smith", "storage"]


def test_export_then_import_preserves_module_registry(tmp_path):
    game_state = _game_state_with_bases_and_modules()
    out = WorldExporter.export_world(
        game_state=game_state,
        output_path=tmp_path / "campaign.rqworld",
    )
    assert out is not None
    parsed = WorldImporter.import_world(out)
    restored = World.from_dict(parsed["world"])
    assert len(restored.module_registry) == 1
    goblin = restored.module_registry.get("goblin-cave")
    assert goblin is not None
    assert goblin.status == ModuleStatus.AVAILABLE
    assert goblin.lore_files == ["lore/goblin-cave.md"]


# ---------------------------------------------------------------------------
# Metadata version comes from rag_quest.__version__, not a hardcode
# ---------------------------------------------------------------------------


def test_export_metadata_uses_dynamic_version(tmp_path):
    out = WorldExporter.export_world(
        game_state=_game_state_with_bases_and_modules(),
        output_path=tmp_path / "w.rqworld",
    )
    with zipfile.ZipFile(out) as zf:
        with zf.open("metadata.json") as f:
            metadata = json.load(f)
    assert metadata["version"] == __version__


# ---------------------------------------------------------------------------
# modules.yaml + lore file bundling (source_dir flow)
# ---------------------------------------------------------------------------


def _write_world_source(tmp_path: Path) -> Path:
    """Build a source world directory with modules.yaml + lore files."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    lore = tmp_path / "lore"
    lore.mkdir()
    (lore / "goblin-cave.md").write_text("# Goblin Cave\n\nA dark cavern.")
    (lore / "tower.md").write_text("# Tower of Echoes\n\nAn old ruin.")

    manifest = textwrap.dedent("""
        modules:
          - id: goblin-cave
            title: The Goblin Cave
            description: Clear the goblins.
            entry_location: Stonebridge
            lore_files:
              - lore/goblin-cave.md
          - id: tower
            title: Tower of Echoes
            description: Investigate.
            entry_location: Silver Hollow
            lore_files:
              - lore/tower.md
        """).lstrip()
    (tmp_path / MANIFEST_FILENAME).write_text(manifest)
    return tmp_path


def test_exporter_bundles_modules_yaml_and_lore_files(tmp_path):
    source = _write_world_source(tmp_path / "source")
    out_path = tmp_path / "pack.rqworld"

    WorldExporter.export_world(
        game_state=_game_state_with_bases_and_modules(),
        output_path=out_path,
        source_dir=source,
    )

    with zipfile.ZipFile(out_path) as zf:
        names = set(zf.namelist())

    assert MANIFEST_FILENAME in names
    assert "lore/goblin-cave.md" in names
    assert "lore/tower.md" in names


def test_exporter_metadata_flags_bundled_manifest(tmp_path):
    source = _write_world_source(tmp_path / "source")
    out_path = tmp_path / "pack.rqworld"

    WorldExporter.export_world(
        game_state=_game_state_with_bases_and_modules(),
        output_path=out_path,
        source_dir=source,
    )

    parsed = WorldImporter.import_world(out_path)
    assert parsed["has_modules_manifest"] is True
    assert parsed["metadata"]["bundled_lore_files"] == 2


def test_exporter_silently_skips_when_source_dir_has_no_manifest(tmp_path):
    empty_source = tmp_path / "empty"
    empty_source.mkdir()
    out_path = tmp_path / "pack.rqworld"

    WorldExporter.export_world(
        game_state=_game_state_with_bases_and_modules(),
        output_path=out_path,
        source_dir=empty_source,
    )

    parsed = WorldImporter.import_world(out_path)
    assert parsed["has_modules_manifest"] is False
    assert parsed["metadata"]["bundled_lore_files"] == 0


def test_exporter_skips_missing_lore_file_entries(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / MANIFEST_FILENAME).write_text(textwrap.dedent("""
            modules:
              - id: m1
                title: M1
                description: d
                entry_location: X
                lore_files:
                  - lore/missing.md
            """).lstrip())
    out_path = tmp_path / "pack.rqworld"

    WorldExporter.export_world(
        game_state=_game_state_with_bases_and_modules(),
        output_path=out_path,
        source_dir=source,
    )

    with zipfile.ZipFile(out_path) as zf:
        names = set(zf.namelist())
    assert MANIFEST_FILENAME in names
    assert "lore/missing.md" not in names  # skipped, not crashed


def test_exporter_rejects_lore_paths_escaping_source_dir(tmp_path):
    """Zip-Slip protection on the author side: can't bundle files outside source_dir."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("pwned")

    source = tmp_path / "source"
    source.mkdir()
    (source / MANIFEST_FILENAME).write_text(textwrap.dedent("""
            modules:
              - id: m1
                title: M1
                description: d
                entry_location: X
                lore_files:
                  - ../outside/secret.md
            """).lstrip())
    out_path = tmp_path / "pack.rqworld"

    WorldExporter.export_world(
        game_state=_game_state_with_bases_and_modules(),
        output_path=out_path,
        source_dir=source,
    )

    with zipfile.ZipFile(out_path) as zf:
        names = set(zf.namelist())
    # manifest is still bundled (it's in source_dir)
    assert MANIFEST_FILENAME in names
    # but the escaping lore reference is refused
    assert not any("secret.md" in n for n in names)


# ---------------------------------------------------------------------------
# extract_to — round-trip the package back to disk
# ---------------------------------------------------------------------------


def test_extract_to_writes_manifest_and_lore(tmp_path):
    source = _write_world_source(tmp_path / "source")
    pack = tmp_path / "pack.rqworld"
    WorldExporter.export_world(
        game_state=_game_state_with_bases_and_modules(),
        output_path=pack,
        source_dir=source,
    )

    target = tmp_path / "imported-world"
    parsed = WorldImporter.extract_to(pack, target)

    assert parsed is not None
    assert parsed["target_dir"] == str(target)
    assert (target / MANIFEST_FILENAME).exists()
    assert (target / "lore" / "goblin-cave.md").exists()
    assert (target / "lore" / "tower.md").exists()


def test_extract_to_output_plugs_into_load_modules(tmp_path):
    """The whole point: after extract_to, load_modules(target_dir) should work."""
    source = _write_world_source(tmp_path / "source")
    pack = tmp_path / "pack.rqworld"
    WorldExporter.export_world(
        game_state=_game_state_with_bases_and_modules(),
        output_path=pack,
        source_dir=source,
    )

    target = tmp_path / "imported-world"
    WorldImporter.extract_to(pack, target)

    registry = load_modules(target)  # no world_rag → no ingestion side effect
    assert len(registry) == 2
    assert registry.get("goblin-cave").lore_files == ["lore/goblin-cave.md"]
    assert registry.get("tower").lore_files == ["lore/tower.md"]


def test_extract_to_rejects_zip_slip_members(tmp_path):
    """Crafted archive with an escaping member shouldn't write outside target_dir."""
    target = tmp_path / "victim"
    outside = tmp_path / "should-not-exist.txt"
    assert not outside.exists()

    pack = tmp_path / "evil.rqworld"
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("metadata.json", json.dumps({"name": "x"}))
        # member path attempts to escape via ../
        zf.writestr("../should-not-exist.txt", "pwned")

    parsed = WorldImporter.extract_to(pack, target)
    assert parsed is not None  # still succeeds for safe members
    assert not outside.exists()  # escaping member was rejected


def test_validate_world_accepts_v07_package(tmp_path):
    out = WorldExporter.export_world(
        game_state=_game_state_with_bases_and_modules(),
        output_path=tmp_path / "w.rqworld",
    )
    assert WorldImporter.validate_world(out) is True
