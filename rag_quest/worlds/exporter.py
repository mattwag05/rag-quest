"""World export functionality for sharing."""

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from .. import __version__
from .modules import MANIFEST_FILENAME


class WorldExporter:
    """Export a complete world package for sharing."""

    @staticmethod
    def export_world(
        game_state: dict = None,
        output_path: Path = None,
        author: str = "Unknown",
        description: str = "",
        tags: Optional[list[str]] = None,
        source_dir: Optional[Path] = None,
        world: dict = None,
        character_name: str = None,
        output_path_old: Path = None,
    ) -> Optional[Path]:
        """Export a complete world package as .rqworld file.

        Creates a ZIP containing:
        - world.json: world state (includes bases and module_registry v0.7+)
        - quests.json: quest chains and templates
        - events.json: active/historical world events
        - relationships.json: NPC relationships and factions
        - metadata.json: name, description, author, version, tags
        - thumbnail.txt: ASCII art preview
        - modules.yaml: source manifest (v0.7, when source_dir supplied)
        - lore/**: every lore_file referenced by modules.yaml (v0.7, when
          source_dir supplied)

        The `source_dir` parameter is the on-disk world directory whose
        `modules.yaml` and lore files should be bundled. Without it the
        exporter still ships `world.json` (which carries the parsed
        `module_registry` runtime state) but an importer won't be able to
        re-ingest lore files into a fresh LightRAG index.

        Returns the path to the written `.rqworld`, or None on failure.
        """
        if world is not None and game_state is None:
            game_state = {
                "world": world,
                "quest_log": {},
                "events": {},
                "relationships": {},
            }
            if character_name and not author:
                author = character_name

        if output_path_old is not None and output_path is None:
            output_path = output_path_old

        if game_state is None or output_path is None:
            return None

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not output_path.suffix == ".rqworld":
            output_path = output_path.with_suffix(".rqworld")

        try:
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                world_data = game_state.get("world", {})
                zf.writestr("world.json", json.dumps(world_data, indent=2))
                zf.writestr(
                    "quests.json",
                    json.dumps(game_state.get("quest_log", {}), indent=2),
                )
                zf.writestr(
                    "events.json",
                    json.dumps(game_state.get("events", {}), indent=2),
                )
                zf.writestr(
                    "relationships.json",
                    json.dumps(game_state.get("relationships", {}), indent=2),
                )

                bundled_modules = False
                bundled_lore_count = 0
                if source_dir is not None:
                    bundled_modules, bundled_lore_count = (
                        WorldExporter._bundle_modules_and_lore(zf, Path(source_dir))
                    )

                metadata = {
                    "name": world_data.get("name", "Unknown World"),
                    "setting": world_data.get("setting", "Generic Fantasy"),
                    "tone": world_data.get("tone", "Neutral"),
                    "author": author,
                    "description": description,
                    "tags": tags or [],
                    "version": __version__,
                    "exported_at": datetime.now().isoformat(),
                    "world_day_number": world_data.get("day_number", 1),
                    "has_modules_manifest": bundled_modules,
                    "bundled_lore_files": bundled_lore_count,
                }
                zf.writestr("metadata.json", json.dumps(metadata, indent=2))
                zf.writestr(
                    "thumbnail.txt", WorldExporter._create_thumbnail(world_data)
                )

            return output_path
        except (OSError, zipfile.BadZipFile):
            return None

    @staticmethod
    def _bundle_modules_and_lore(
        zf: zipfile.ZipFile, source_dir: Path
    ) -> tuple[bool, int]:
        """Copy modules.yaml + every referenced lore file into the archive.

        Returns (bundled_manifest?, number_of_lore_files_bundled).
        Silent no-op if the manifest is absent or malformed — a broken
        manifest at export time shouldn't block the rest of the world
        shipping. The validate-module CLI is the right place to catch that.
        """
        manifest_path = source_dir / MANIFEST_FILENAME
        if not manifest_path.exists():
            return False, 0

        try:
            import yaml

            with manifest_path.open("r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
        except Exception:
            return False, 0

        zf.write(manifest_path, arcname=MANIFEST_FILENAME)

        lore_count = 0
        entries = raw.get("modules") if isinstance(raw, dict) else None
        if not isinstance(entries, list):
            return True, 0
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for lore_rel in entry.get("lore_files") or []:
                if not isinstance(lore_rel, str):
                    continue
                lore_abs = (source_dir / lore_rel).resolve()
                # Reject absolute paths or paths outside source_dir to avoid
                # bundling arbitrary files.
                try:
                    lore_abs.relative_to(source_dir.resolve())
                except ValueError:
                    continue
                if not lore_abs.exists():
                    continue
                zf.write(lore_abs, arcname=lore_rel)
                lore_count += 1

        return True, lore_count

    @staticmethod
    def _create_thumbnail(world_data: dict) -> str:
        """ASCII art preview of the world for the package header."""
        name = world_data.get("name", "Unknown")
        setting = world_data.get("setting", "Fantasy")
        day = world_data.get("day_number", 1)
        return f"""
╔════════════════════════════════════════╗
║         {name:^36} ║
╠════════════════════════════════════════╣
║ Setting: {setting:<28} ║
║ Day: {day:<35} ║
║                                        ║
║ Visited Locations: {len(world_data.get('visited_locations', [])):<15} ║
║ NPCs Met: {len(world_data.get('npcs_met', [])):<24} ║
║                                        ║
╚════════════════════════════════════════╝
""".strip()
