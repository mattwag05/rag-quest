"""World import functionality for sharing."""

import json
import zipfile
from pathlib import Path
from typing import Optional, List


class WorldImporter:
    """Import a shared world package."""

    @staticmethod
    def import_world(file_path: Path) -> Optional[dict]:
        """Import a world from a .rqworld file.
        
        Args:
            file_path: Path to the .rqworld file
        
        Returns:
            World config dict, or None if import failed
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return None

        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                # Load metadata
                if "metadata.json" not in zf.namelist():
                    return None

                with zf.open("metadata.json") as f:
                    metadata = json.load(f)

                # Load world state
                world_data = {}
                if "world.json" in zf.namelist():
                    with zf.open("world.json") as f:
                        world_data = json.load(f)

                # Load quests
                quests_data = {}
                if "quests.json" in zf.namelist():
                    with zf.open("quests.json") as f:
                        quests_data = json.load(f)

                # Load events
                events_data = {}
                if "events.json" in zf.namelist():
                    with zf.open("events.json") as f:
                        events_data = json.load(f)

                # Load relationships
                rel_data = {}
                if "relationships.json" in zf.namelist():
                    with zf.open("relationships.json") as f:
                        rel_data = json.load(f)

                return {
                    "metadata": metadata,
                    "world": world_data,
                    "quests": quests_data,
                    "events": events_data,
                    "relationships": rel_data,
                }
        except (OSError, zipfile.BadZipFile, json.JSONDecodeError):
            pass

        return None

    @staticmethod
    def validate_world(file_path: Path) -> bool:
        """Check integrity of a .rqworld file.
        
        Args:
            file_path: Path to the .rqworld file
        
        Returns:
            True if valid, False otherwise
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return False

        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                # Must have metadata
                if "metadata.json" not in zf.namelist():
                    return False

                # Validate metadata is valid JSON
                with zf.open("metadata.json") as f:
                    json.load(f)

                # Validate other JSON files if present
                for filename in ["world.json", "quests.json", "events.json", "relationships.json"]:
                    if filename in zf.namelist():
                        with zf.open(filename) as f:
                            json.load(f)

                return True
        except (OSError, zipfile.BadZipFile, json.JSONDecodeError):
            return False

    @staticmethod
    def list_available_worlds(worlds_dir: Path) -> List[dict]:
        """Scan a directory for available .rqworld files.
        
        Args:
            worlds_dir: Directory to scan for .rqworld files
        
        Returns:
            List of world metadata dicts
        """
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
