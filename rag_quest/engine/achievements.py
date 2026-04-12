"""Achievement system for RAG-Quest."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Achievement:
    """An achievement that can be unlocked."""
    id: str
    name: str
    description: str
    icon: str  # emoji
    is_hidden: bool = False
    unlocked: bool = False
    unlocked_at: Optional[str] = None  # ISO format datetime

    def to_dict(self) -> dict:
        """Serialize achievement."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "is_hidden": self.is_hidden,
            "unlocked": self.unlocked,
            "unlocked_at": self.unlocked_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Achievement":
        """Deserialize achievement."""
        return cls(**data)

    def unlock(self) -> None:
        """Unlock this achievement."""
        if not self.unlocked:
            self.unlocked = True
            self.unlocked_at = datetime.now().isoformat()


class AchievementManager:
    """Manages achievements for the game."""

    def __init__(self):
        """Initialize achievement manager with built-in achievements."""
        self.achievements: dict[str, Achievement] = {}
        self._init_achievements()

    def _init_achievements(self) -> None:
        """Initialize all built-in achievements."""
        achievement_list = [
            Achievement(
                id="first_steps",
                name="First Steps",
                description="Complete your first turn",
                icon="👣",
            ),
            Achievement(
                id="explorer",
                name="Explorer",
                description="Visit 10 different locations",
                icon="🗺️",
            ),
            Achievement(
                id="social_butterfly",
                name="Social Butterfly",
                description="Befriend 5 NPCs",
                icon="🦋",
            ),
            Achievement(
                id="dragon_slayer",
                name="Dragon Slayer",
                description="Defeat a boss enemy",
                icon="🐉",
            ),
            Achievement(
                id="hoarder",
                name="Hoarder",
                description="Collect 20 items",
                icon="💎",
            ),
            Achievement(
                id="party_leader",
                name="Party Leader",
                description="Recruit 3 companions",
                icon="👥",
            ),
            Achievement(
                id="quest_master",
                name="Quest Master",
                description="Complete 5 quests",
                icon="📜",
            ),
            Achievement(
                id="survivor",
                name="Survivor",
                description="Survive with 1 HP",
                icon="💪",
            ),
            Achievement(
                id="level_5",
                name="Rising Power",
                description="Reach level 5",
                icon="⭐",
            ),
            Achievement(
                id="level_10",
                name="Master Adventurer",
                description="Reach level 10",
                icon="✨",
            ),
            Achievement(
                id="world_traveler",
                name="World Traveler",
                description="Complete a full quest chain",
                icon="🌍",
            ),
        ]

        for achievement in achievement_list:
            self.achievements[achievement.id] = achievement

    def check_achievements(self, game_state: dict = None, player: dict = None) -> List[Achievement]:
        """Check for newly unlocked achievements based on game state.
        
        Args:
            game_state: Current game state dict (NEW API)
            player: Player dict (OLD API backwards compat, ignored if game_state provided)
        
        Returns:
            List of newly unlocked achievements
        """
        # Handle backwards compatibility: check_achievements(player={...})
        if game_state is None and player is not None:
            # Old style call with player object, convert to game_state format
            game_state = {
                "character": player,
                "world": {"visited_locations": [], "npcs_met": []},
                "inventory": {"items": []},
                "party": {"members": []},
                "quest_log": {"quests": []},
                "turn_number": 1
            }
        
        if game_state is None:
            return []
        
        newly_unlocked = []

        character = game_state.get("character", {})
        inventory = game_state.get("inventory", {})
        party = game_state.get("party", {})
        quest_log = game_state.get("quest_log", {})
        world = game_state.get("world", {})
        turn_number = game_state.get("turn_number", 0)
        current_hp = character.get("current_hp", 1)

        # First Steps - complete a turn
        if turn_number > 0:
            if not self.achievements["first_steps"].unlocked:
                self.achievements["first_steps"].unlock()
                newly_unlocked.append(self.achievements["first_steps"])

        # Explorer - visit 10 locations
        visited = len(world.get("visited_locations", []))
        if visited >= 10:
            if not self.achievements["explorer"].unlocked:
                self.achievements["explorer"].unlock()
                newly_unlocked.append(self.achievements["explorer"])

        # Social Butterfly - befriend 5 NPCs
        met_npcs = len(world.get("npcs_met", []))
        if met_npcs >= 5:
            if not self.achievements["social_butterfly"].unlocked:
                self.achievements["social_butterfly"].unlock()
                newly_unlocked.append(self.achievements["social_butterfly"])

        # Hoarder - collect 20 items
        item_count = len(inventory.get("items", []))
        if item_count >= 20:
            if not self.achievements["hoarder"].unlocked:
                self.achievements["hoarder"].unlock()
                newly_unlocked.append(self.achievements["hoarder"])

        # Party Leader - recruit 3 companions
        party_members = len(party.get("members", []))
        if party_members >= 3:
            if not self.achievements["party_leader"].unlocked:
                self.achievements["party_leader"].unlock()
                newly_unlocked.append(self.achievements["party_leader"])

        # Quest Master - complete 5 quests
        completed_quests = len([q for q in quest_log.get("quests", [])
                                if q.get("status") == "completed"])
        if completed_quests >= 5:
            if not self.achievements["quest_master"].unlocked:
                self.achievements["quest_master"].unlock()
                newly_unlocked.append(self.achievements["quest_master"])

        # Survivor - survive with 1 HP
        if current_hp == 1 and character.get("current_hp", 0) > 0:
            if not self.achievements["survivor"].unlocked:
                self.achievements["survivor"].unlock()
                newly_unlocked.append(self.achievements["survivor"])

        # Level 5
        if character.get("level", 1) >= 5:
            if not self.achievements["level_5"].unlocked:
                self.achievements["level_5"].unlock()
                newly_unlocked.append(self.achievements["level_5"])

        # Level 10
        if character.get("level", 1) >= 10:
            if not self.achievements["level_10"].unlocked:
                self.achievements["level_10"].unlock()
                newly_unlocked.append(self.achievements["level_10"])

        # Dragon Slayer - checked via combat encounters (placeholder)
        # World Traveler - checked via quest completion (placeholder)

        return newly_unlocked

    def get_all_achievements(self) -> List[Achievement]:
        """Get all achievements (both locked and unlocked).
        
        Returns:
            List of all Achievement objects
        """
        return list(self.achievements.values())

    def get_unlocked(self) -> List[Achievement]:
        """Get all unlocked achievements.
        
        Returns:
            List of unlocked Achievement objects
        """
        return [a for a in self.achievements.values() if a.unlocked]

    def unlock_achievement(self, achievement_id: str) -> bool:
        """Manually unlock an achievement.
        
        Args:
            achievement_id: ID of the achievement
        
        Returns:
            True if unlocked, False if not found
        """
        if achievement_id not in self.achievements:
            return False

        self.achievements[achievement_id].unlock()
        return True

    def to_dict(self) -> dict:
        """Serialize achievement manager."""
        return {
            "achievements": {
                aid: ach.to_dict()
                for aid, ach in self.achievements.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AchievementManager":
        """Deserialize achievement manager."""
        manager = cls()
        for aid, ach_data in data.get("achievements", {}).items():
            if aid in manager.achievements:
                manager.achievements[aid] = Achievement.from_dict(ach_data)
        return manager
