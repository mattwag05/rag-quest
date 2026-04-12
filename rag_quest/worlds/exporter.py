"""World export functionality for sharing."""

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional


class WorldExporter:
    """Export a complete world package for sharing."""

    @staticmethod
    def export_world(game_state: dict, output_path: Path, 
                     author: str = "Unknown", 
                     description: str = "",
                     tags: Optional[list[str]] = None) -> Optional[Path]:
        """Export a complete world package as .rqworld file.
        
        Creates a ZIP containing:
        - world.json: world state, NPCs, factions, events
        - lore.json: extracted LightRAG knowledge (if available)
        - quests.json: quest chains and templates
        - metadata.json: name, description, author, version, tags
        - thumbnail.txt: ASCII art preview
        
        Args:
            game_state: Game state dict (from GameState.to_dict())
            output_path: Path to write .rqworld file
            author: Author name for the world
            description: Description of the world
            tags: Optional list of tags (e.g., ["dungeon", "dark"])
        
        Returns:
            Path to created .rqworld file, or None if export failed
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not output_path.suffix == '.rqworld':
            output_path = output_path.with_suffix('.rqworld')

        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Export world state
                world_data = game_state.get("world", {})
                zf.writestr("world.json", json.dumps(world_data, indent=2))

                # Export quests
                quest_data = game_state.get("quest_log", {})
                zf.writestr("quests.json", json.dumps(quest_data, indent=2))

                # Export events
                events_data = game_state.get("events", {})
                zf.writestr("events.json", json.dumps(events_data, indent=2))

                # Export relationships/factions
                rel_data = game_state.get("relationships", {})
                zf.writestr("relationships.json", json.dumps(rel_data, indent=2))

                # Create metadata
                metadata = {
                    "name": world_data.get("name", "Unknown World"),
                    "setting": world_data.get("setting", "Generic Fantasy"),
                    "tone": world_data.get("tone", "Neutral"),
                    "author": author,
                    "description": description,
                    "tags": tags or [],
                    "version": "0.5.0",
                    "exported_at": datetime.now().isoformat(),
                    "world_day_number": world_data.get("day_number", 1),
                }
                zf.writestr("metadata.json", json.dumps(metadata, indent=2))

                # Create thumbnail (ASCII art preview)
                thumbnail = WorldExporter._create_thumbnail(world_data)
                zf.writestr("thumbnail.txt", thumbnail)

            return output_path
        except (OSError, zipfile.BadZipFile):
            return None

    @staticmethod
    def _create_thumbnail(world_data: dict) -> str:
        """Create ASCII art preview of the world.
        
        Args:
            world_data: World state dict
        
        Returns:
            ASCII art string
        """
        name = world_data.get("name", "Unknown")
        setting = world_data.get("setting", "Fantasy")
        day = world_data.get("day_number", 1)
        
        thumbnail = f"""
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
        
        return thumbnail
