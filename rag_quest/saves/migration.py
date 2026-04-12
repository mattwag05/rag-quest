"""Save format migration system for version compatibility."""

from typing import Dict


class SaveMigrator:
    """Migrates save files between versions."""

    # Map version strings to migration functions
    MIGRATIONS: Dict[str, callable] = {}

    @staticmethod
    def migrate(save_data: dict, from_version: str, to_version: str) -> dict:
        """Migrate save data from one version to another.
        
        Args:
            save_data: The game state to migrate
            from_version: Version string the save is from (e.g., "0.4.0")
            to_version: Target version string (e.g., "0.5.0")
        
        Returns:
            Migrated game state dict
        """
        # For now, all saves are compatible with 0.5.0
        # Future migrations would go here
        
        current = save_data.copy()
        
        # Migration chain: 0.4.x -> 0.5.0
        if from_version.startswith("0.4"):
            current = SaveMigrator._migrate_0_4_to_0_5(current)
        
        return current

    @staticmethod
    def _migrate_0_4_to_0_5(save_data: dict) -> dict:
        """Migrate from 0.4.x to 0.5.0.
        
        Changes in 0.5.0:
        - Add playtime_seconds if missing
        - Ensure all new fields exist with defaults
        """
        migrated = save_data.copy()
        
        # Add playtime tracking if missing
        if "playtime_seconds" not in migrated:
            migrated["playtime_seconds"] = 0.0
        
        # Ensure character has all fields (v0.5 compatibility)
        if "character" in migrated:
            char = migrated["character"]
            # No new required fields yet in character
        
        return migrated
