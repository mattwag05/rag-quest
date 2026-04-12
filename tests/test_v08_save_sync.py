"""Tests for v0.8 cross-device save sync via .rqworld round-trip.

Exercises the new `WorldExporter.save_file` parameter and the matching
`WorldImporter.extract_campaign(file, install_dir)` flow.
"""

import json
import textwrap
import zipfile
from pathlib import Path

from rag_quest.engine.bases import Base
from rag_quest.engine.world import World
from rag_quest.worlds.exporter import WorldExporter
from rag_quest.worlds.importer import WorldImporter
from rag_quest.worlds.modules import MANIFEST_FILENAME


def _game_state(world_name: str = "Ironhold Campaign") -> dict:
    w = World(name=world_name, setting="Fantasy", tone="Heroic")
    w.bases.append(Base(name="Ironhold", location_ref="Stonebridge"))
    return {
        "save_version": 3,
        "world": w.to_dict(),
        "character": {"name": "Durin", "level": 7},
        "quest_log": {"quests": []},
        "events": {},
        "relationships": {},
        "turn_number": 42,
    }


def _write_save_file(tmp_path: Path, world_name: str, payload: dict) -> Path:
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir(parents=True, exist_ok=True)
    save_path = saves_dir / f"{world_name}.json"
    save_path.write_text(json.dumps(payload, indent=2))
    return save_path


# ---------------------------------------------------------------------------
# Exporter: save_file bundles save.json + metadata flag
# ---------------------------------------------------------------------------


def test_export_with_save_file_bundles_save_json(tmp_path):
    payload = _game_state()
    save_path = _write_save_file(tmp_path, "Ironhold Campaign", payload)

    out = WorldExporter.export_world(
        game_state=payload,
        output_path=tmp_path / "pack.rqworld",
        save_file=save_path,
    )
    assert out is not None
    with zipfile.ZipFile(out) as zf:
        assert "save.json" in zf.namelist()
        with zf.open("save.json") as f:
            restored = json.load(f)
    # Exact byte-for-byte verbatim copy is overkill; assert the payload
    # survived round-trip semantically.
    assert restored["save_version"] == 3
    assert restored["turn_number"] == 42
    assert restored["character"]["name"] == "Durin"


def test_export_metadata_flags_bundled_save(tmp_path):
    save_path = _write_save_file(tmp_path, "X", _game_state("X"))
    out = WorldExporter.export_world(
        game_state=_game_state("X"),
        output_path=tmp_path / "pack.rqworld",
        save_file=save_path,
    )
    parsed = WorldImporter.import_world(out)
    assert parsed["metadata"]["has_save_file"] is True


def test_export_without_save_file_flag_is_false(tmp_path):
    out = WorldExporter.export_world(
        game_state=_game_state("X"),
        output_path=tmp_path / "pack.rqworld",
    )
    parsed = WorldImporter.import_world(out)
    assert parsed["metadata"]["has_save_file"] is False
    with zipfile.ZipFile(out) as zf:
        assert "save.json" not in zf.namelist()


def test_export_silently_skips_missing_save_file(tmp_path):
    out = WorldExporter.export_world(
        game_state=_game_state("X"),
        output_path=tmp_path / "pack.rqworld",
        save_file=tmp_path / "does-not-exist.json",
    )
    # Package still written successfully; just without save.json.
    assert out is not None
    parsed = WorldImporter.import_world(out)
    assert parsed["metadata"]["has_save_file"] is False


# ---------------------------------------------------------------------------
# Importer: extract_campaign writes to install_dir/worlds and install_dir/saves
# ---------------------------------------------------------------------------


def _write_world_source(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    lore = tmp_path / "lore"
    lore.mkdir()
    (lore / "cave.md").write_text("# Goblin Cave")
    (tmp_path / MANIFEST_FILENAME).write_text(textwrap.dedent("""
            modules:
              - id: cave
                title: Cave
                description: d
                entry_location: X
                lore_files:
                  - lore/cave.md
            """).lstrip())
    return tmp_path


def test_extract_campaign_restores_save_and_world_layout(tmp_path):
    source = _write_world_source(tmp_path / "source")
    save_path = _write_save_file(tmp_path, "Ironhold Campaign", _game_state())

    pack = tmp_path / "campaign.rqworld"
    WorldExporter.export_world(
        game_state=_game_state(),
        output_path=pack,
        source_dir=source,
        save_file=save_path,
    )

    install_dir = tmp_path / "install"
    result = WorldImporter.extract_campaign(pack, install_dir=install_dir)
    assert result is not None
    assert result["world_name"] == "Ironhold Campaign"

    # World files land under install_dir/worlds/<name>/
    worlds_dir = install_dir / "worlds" / "Ironhold Campaign"
    assert worlds_dir.exists()
    assert (worlds_dir / MANIFEST_FILENAME).exists()
    assert (worlds_dir / "lore" / "cave.md").exists()
    # save.json should NOT remain inside the world dir — it moves to saves/.
    assert not (worlds_dir / "save.json").exists()

    # Save file lands under install_dir/saves/<name>.json
    save_target = install_dir / "saves" / "Ironhold Campaign.json"
    assert save_target.exists()
    restored_save = json.loads(save_target.read_text())
    assert restored_save["turn_number"] == 42
    assert restored_save["character"]["name"] == "Durin"


def test_extract_campaign_without_save_file_still_unpacks_world(tmp_path):
    source = _write_world_source(tmp_path / "source")
    pack = tmp_path / "campaign.rqworld"
    WorldExporter.export_world(
        game_state=_game_state("NoSave World"),
        output_path=pack,
        source_dir=source,
        # no save_file
    )

    install_dir = tmp_path / "install"
    result = WorldImporter.extract_campaign(pack, install_dir=install_dir)
    assert result is not None
    assert result["save_path"] is None
    assert (install_dir / "worlds" / "NoSave World" / MANIFEST_FILENAME).exists()
    assert not (install_dir / "saves" / "NoSave World.json").exists()


def test_extract_campaign_sanitizes_unsafe_world_names(tmp_path):
    """A metadata.name with path separators shouldn't escape install_dir."""
    # Manually craft an archive whose metadata.name contains `../`.
    pack = tmp_path / "evil.rqworld"
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "metadata.json",
            json.dumps({"name": "../pwned", "has_save_file": False}),
        )
        zf.writestr("world.json", json.dumps({"name": "../pwned"}))

    install_dir = tmp_path / "install"
    result = WorldImporter.extract_campaign(pack, install_dir=install_dir)
    assert result is not None
    # The sanitizer replaces path separators with underscores.
    assert "pwned" in result["world_name"]
    assert "/" not in result["world_name"]
    # Nothing should have been written outside install_dir.
    assert not (tmp_path / "pwned").exists()


def test_extract_campaign_round_trip_preserves_save_verbatim(tmp_path):
    """End-to-end: export a save on machine A, extract it on machine B,
    the restored save.json payload should be semantically identical."""
    original_payload = _game_state("Round Trip")
    original_payload["relationships"]["npcs"] = {"Durin": {"trust": 85}}
    save_path = _write_save_file(tmp_path, "Round Trip", original_payload)

    pack = tmp_path / "campaign.rqworld"
    WorldExporter.export_world(
        game_state=original_payload,
        output_path=pack,
        save_file=save_path,
    )

    install_dir = tmp_path / "install"
    WorldImporter.extract_campaign(pack, install_dir=install_dir)
    restored = json.loads((install_dir / "saves" / "Round Trip.json").read_text())
    assert restored == original_payload
