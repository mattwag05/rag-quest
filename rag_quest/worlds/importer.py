"""World import functionality for sharing."""

import json
import zipfile
from pathlib import Path
from typing import List, Optional

from .modules import MANIFEST_FILENAME


class WorldImporter:
    """Import a shared world package."""

    @staticmethod
    def import_world(file_path: Path) -> Optional[dict]:
        """Read a `.rqworld` package into a dict of its JSON entries.

        This does NOT touch the filesystem beyond reading the ZIP — it's a
        pure-parse read useful for previews and metadata listings. Use
        `extract_to()` when you need the side-car files (`modules.yaml`,
        lore files) on disk for LightRAG ingestion.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return None

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                if "metadata.json" not in zf.namelist():
                    return None

                with zf.open("metadata.json") as f:
                    metadata = json.load(f)

                def _read_json(name: str) -> dict:
                    if name not in zf.namelist():
                        return {}
                    with zf.open(name) as f:
                        return json.load(f)

                return {
                    "metadata": metadata,
                    "world": _read_json("world.json"),
                    "quests": _read_json("quests.json"),
                    "events": _read_json("events.json"),
                    "relationships": _read_json("relationships.json"),
                    "has_modules_manifest": MANIFEST_FILENAME in zf.namelist(),
                }
        except (OSError, zipfile.BadZipFile, json.JSONDecodeError):
            return None

    @staticmethod
    def extract_to(file_path: Path, target_dir: Path) -> Optional[dict]:
        """Extract a `.rqworld` package into `target_dir` on disk.

        Writes the JSON parse result AND any side-car files — `modules.yaml`,
        lore files under `lore/**` — so the caller can subsequently run
        `load_modules(target_dir, world_rag)` to re-ingest module lore into
        a fresh LightRAG index. Returns the same dict shape as
        `import_world()` plus a `target_dir` key pointing at the extraction
        root. Returns None on I/O failure or an invalid archive.

        Safety: refuses to extract any archive member whose path escapes
        `target_dir` (Zip-Slip guard).
        """
        file_path = Path(file_path)
        target_dir = Path(target_dir)
        if not file_path.exists():
            return None

        target_dir.mkdir(parents=True, exist_ok=True)
        target_resolved = target_dir.resolve()

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                for member in zf.infolist():
                    # Zip-Slip guard: resolve the final path and ensure it
                    # stays within target_dir.
                    dest = (target_dir / member.filename).resolve()
                    try:
                        dest.relative_to(target_resolved)
                    except ValueError:
                        continue
                    if member.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                        continue
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(dest, "wb") as out:
                        out.write(src.read())
        except (OSError, zipfile.BadZipFile):
            return None

        parsed = WorldImporter.import_world(file_path)
        if parsed is None:
            return None
        parsed["target_dir"] = str(target_dir)
        return parsed

    @staticmethod
    def validate_world(file_path: Path) -> bool:
        """Quick integrity check: zip opens, metadata parses, every bundled
        JSON is well-formed."""
        file_path = Path(file_path)
        if not file_path.exists():
            return False

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                if "metadata.json" not in zf.namelist():
                    return False
                with zf.open("metadata.json") as f:
                    json.load(f)
                for filename in (
                    "world.json",
                    "quests.json",
                    "events.json",
                    "relationships.json",
                ):
                    if filename in zf.namelist():
                        with zf.open(filename) as f:
                            json.load(f)
                return True
        except (OSError, zipfile.BadZipFile, json.JSONDecodeError):
            return False

    @staticmethod
    def list_available_worlds(worlds_dir: Path) -> List[dict]:
        """Scan `worlds_dir` for `.rqworld` files and return their metadata."""
        worlds_dir = Path(worlds_dir)
        if not worlds_dir.exists():
            return []

        worlds = []
        for world_file in worlds_dir.glob("*.rqworld"):
            world_data = WorldImporter.import_world(world_file)
            if world_data:
                metadata = world_data.get("metadata", {})
                metadata["file_path"] = str(world_file)
                worlds.append(metadata)

        return worlds
