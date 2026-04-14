"""Save game management with multiple slots, auto-save, and recovery."""

import json
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4


@dataclass
class SaveSlot:
    """Metadata about a save slot."""

    slot_id: str
    name: str
    character_name: str
    character_level: int
    world_name: str
    turn_number: int
    created_at: str  # ISO format datetime
    updated_at: str  # ISO format datetime
    playtime_seconds: float

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SaveSlot":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SavePaths:
    """Canonical on-disk layout for a single save slot.

    All three paths live inside ``slot_dir``:

    - ``state``: the JSON dump of ``GameState.to_dict()``
    - ``metadata``: the ``SaveSlot`` metadata (for ``list_saves``)
    - ``world_db``: the SQLite ``WorldDB`` (v0.9 Phase 1+)

    Returned by ``SaveManager.save_paths_for(slot_id)`` so every caller
    (CLI autosave, web onboarding, web load) resolves paths the same way.
    """

    slot_dir: Path
    state: Path
    metadata: Path
    world_db: Path


class SaveManager:
    """Manages multiple save slots with auto-save and recovery."""

    def __init__(self, save_dir: Optional[Path] = None):
        """Initialize save manager.

        Args:
            save_dir: Directory to store save files. Defaults to ~/.local/share/rag-quest/saves/
        """
        if save_dir is None:
            save_dir = Path.home() / ".local" / "share" / "rag-quest" / "saves"

        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.auto_save_dir = self.save_dir / "autosaves"
        self.auto_save_dir.mkdir(exist_ok=True)

    def list_saves(self, world_name: str = None) -> List[SaveSlot]:
        """List all available save slots.

        Args:
            world_name: Optional world name filter (for backwards compatibility, ignored)

        Returns:
            List of SaveSlot objects
        """
        slots = []
        for metadata_file in self.save_dir.glob("*/metadata.json"):
            try:
                with open(metadata_file, "r") as f:
                    data = json.load(f)
                    slots.append(SaveSlot.from_dict(data))
            except (json.JSONDecodeError, OSError):
                pass

        # Sort by updated_at descending
        slots.sort(key=lambda s: s.updated_at, reverse=True)
        return slots

    def save_paths_for(self, slot_id: str) -> SavePaths:
        """Return the canonical on-disk paths for a slot.

        Every caller that needs ``state.json`` / ``metadata.json`` /
        ``world.db`` routes through this helper so the layout is owned
        by SaveManager alone.
        """
        slot_dir = self.save_dir / slot_id
        return SavePaths(
            slot_dir=slot_dir,
            state=slot_dir / "state.json",
            metadata=slot_dir / "metadata.json",
            world_db=slot_dir / "world.db",
        )

    def save_game(self, *args, **kwargs) -> SaveSlot:
        """Save game to a slot.

        Supports three calling styles:
        - UPDATE: save_game(game_state, slot_id="<uuid>") — writes to an
          existing slot in place, preserving ``created_at`` and bumping
          ``updated_at``. Used by the CLI and web autosave paths.
        - NEW: save_game(game_state, slot_name="...") — mints a fresh
          UUID slot. Used on new-game creation.
        - OLD: save_game(world_name, slot_number, state, character_name)
          — positional-arg legacy path, still mints a fresh UUID.

        Returns:
            SaveSlot metadata for the created or updated save.
        """
        # Pop the update-in-place kwarg before the legacy arg parsing runs;
        # it's new-style only and never collides with the positional compat.
        slot_id_override: Optional[str] = kwargs.pop("slot_id", None)

        # Handle positional arguments for backwards compatibility
        if len(args) >= 4:
            # Old style: save_game(world_name, slot_number, state, character_name)
            world_name, slot_number, state, character_name = args[:4]
            game_state = state
            slot_name = (
                f"{character_name} - Slot {slot_number}"
                if character_name
                else f"Slot {slot_number}"
            )
        elif len(args) >= 1:
            # New style: save_game(game_state, ...)
            game_state = args[0]
            slot_name = args[1] if len(args) > 1 else kwargs.get("slot_name")
        else:
            # Kwargs only
            game_state = kwargs.get("game_state")
            slot_name = kwargs.get("slot_name")

            # Handle old-style kwargs
            if game_state is None:
                game_state = kwargs.get("state")

            if slot_name is None:
                character_name = kwargs.get("character_name")
                slot_number = kwargs.get("slot_number")
                if character_name or slot_number:
                    slot_name = (
                        f"{character_name or 'Unknown'} - Slot {slot_number or 0}"
                    )

        if game_state is None:
            raise ValueError("game_state parameter required")

        # Resolve slot identity. In update mode we preserve created_at from
        # the existing metadata so the slot's lifetime is honest; in new-slot
        # mode we mint a fresh UUID and stamp created_at = updated_at = now.
        now = datetime.now().isoformat()
        if slot_id_override is not None:
            slot_id = slot_id_override
            existing = self.get_save_info(slot_id)
            created_at = existing.created_at if existing is not None else now
            # If the caller didn't supply a new slot_name, preserve the
            # existing one so autosaves don't wipe the human-readable label.
            if slot_name is None and existing is not None:
                slot_name = existing.name
        else:
            slot_id = str(uuid4())
            created_at = now

        paths = self.save_paths_for(slot_id)
        paths.slot_dir.mkdir(parents=True, exist_ok=True)

        # Extract metadata from game state
        char = game_state.get("character", {})
        world = game_state.get("world", {})
        char_name = char.get("name", "Unknown")
        char_level = char.get("level", 1)
        world_name = world.get("name", "Unknown World")
        turn_number = game_state.get("turn_number", 0)

        if slot_name is None:
            slot_name = f"{char_name} - Level {char_level}"

        metadata = SaveSlot(
            slot_id=slot_id,
            name=slot_name,
            character_name=char_name,
            character_level=char_level,
            world_name=world_name,
            turn_number=turn_number,
            created_at=created_at,
            updated_at=now,
            playtime_seconds=game_state.get("playtime_seconds", 0),
        )

        with open(paths.metadata, "w") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        with open(paths.state, "w") as f:
            json.dump(game_state, f, indent=2)

        return metadata

    def load_game(
        self, slot_id_or_world: str = None, slot_number: int = None
    ) -> Optional[dict]:
        """Load game state from a slot.

        Args:
            slot_id_or_world: Slot ID (new) or world name (old backwards compat style)
            slot_number: Slot number (only used in old style call)

        Returns:
            Game state dict, or None if load failed
        """
        # Handle backwards compatibility: load_game(world_name, slot_number)
        if slot_number is not None:
            # Old style: load_game("Test World", 0)
            # Convert to new style by finding the slot
            slots = self.list_saves(slot_id_or_world)
            if slot_number < len(slots):
                slot_id = slots[slot_number].slot_id
            else:
                return None
        else:
            # New style: load_game(slot_id)
            slot_id = slot_id_or_world

        if not slot_id:
            return None

        slot_dir = self.save_dir / slot_id
        state_file = slot_dir / "state.json"

        if not state_file.exists():
            return None

        try:
            with open(state_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            # Try to recover from auto-save
            return self._recover_from_autosave(slot_id)

    def delete_save(self, slot_id: str) -> bool:
        """Delete a save slot.

        Args:
            slot_id: ID of the save slot to delete

        Returns:
            True if successful, False if slot not found
        """
        slot_dir = self.save_dir / slot_id
        if not slot_dir.exists():
            return False

        import shutil

        shutil.rmtree(slot_dir)
        return True

    def auto_save(self, game_state: dict) -> None:
        """Create an auto-save, rotating to keep only 3 most recent.

        Args:
            game_state: Game state dict to save
        """
        # Create auto-save with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        auto_save_file = self.auto_save_dir / f"autosave_{timestamp}.json"

        with open(auto_save_file, "w") as f:
            json.dump(game_state, f)

        # Keep only 3 most recent auto-saves
        auto_saves = sorted(self.auto_save_dir.glob("autosave_*.json"))
        while len(auto_saves) > 3:
            auto_saves[0].unlink()
            auto_saves.pop(0)

    def export_save(self, slot_id: str, output_path: Path) -> Optional[Path]:
        """Export a save as a .rqsave file (ZIP with JSON).

        Args:
            slot_id: ID of the save slot to export
            output_path: Path where to save the .rqsave file

        Returns:
            Path to created file, or None if export failed
        """
        slot_dir = self.save_dir / slot_id
        if not slot_dir.exists():
            return None

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add metadata
                metadata_file = slot_dir / "metadata.json"
                if metadata_file.exists():
                    zf.write(metadata_file, "metadata.json")

                # Add state
                state_file = slot_dir / "state.json"
                if state_file.exists():
                    zf.write(state_file, "state.json")

            return output_path
        except (OSError, zipfile.BadZipFile):
            return None

    def import_save(self, file_path: Path) -> Optional[SaveSlot]:
        """Import a save from a .rqsave file.

        Args:
            file_path: Path to the .rqsave file

        Returns:
            SaveSlot metadata, or None if import failed
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return None

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                # Extract to temp slot
                slot_id = str(uuid4())
                slot_dir = self.save_dir / slot_id
                slot_dir.mkdir(exist_ok=True)

                zf.extractall(slot_dir)

                # Load and validate metadata
                metadata_file = slot_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, "r") as f:
                        data = json.load(f)
                        metadata = SaveSlot.from_dict(data)
                        # Update IDs to new slot
                        metadata.slot_id = slot_id
                        metadata.updated_at = datetime.now().isoformat()

                        # Save updated metadata
                        with open(metadata_file, "w") as mf:
                            json.dump(metadata.to_dict(), mf, indent=2)

                        return metadata
        except (OSError, zipfile.BadZipFile):
            pass

        return None

    def get_save_info(self, slot_id: str) -> Optional[SaveSlot]:
        """Get metadata for a save slot.

        Args:
            slot_id: ID of the save slot

        Returns:
            SaveSlot metadata, or None if not found
        """
        slot_dir = self.save_dir / slot_id
        metadata_file = slot_dir / "metadata.json"

        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file, "r") as f:
                data = json.load(f)
                return SaveSlot.from_dict(data)
        except (json.JSONDecodeError, OSError):
            return None

    def _recover_from_autosave(self, slot_id: str) -> Optional[dict]:
        """Attempt to recover a save from auto-save.

        Args:
            slot_id: ID of the save slot that failed to load

        Returns:
            Game state dict, or None if recovery failed
        """
        auto_saves = sorted(self.auto_save_dir.glob("autosave_*.json"), reverse=True)

        for auto_save_file in auto_saves:
            try:
                with open(auto_save_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

        return None
