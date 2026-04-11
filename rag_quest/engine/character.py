"""Character models for the game."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Race(Enum):
    """Playable character races."""

    HUMAN = "Human"
    ELF = "Elf"
    DWARF = "Dwarf"
    HALFLING = "Halfling"
    ORC = "Orc"


class CharacterClass(Enum):
    """Playable character classes."""

    FIGHTER = "Fighter"
    MAGE = "Mage"
    ROGUE = "Rogue"
    RANGER = "Ranger"
    CLERIC = "Cleric"


@dataclass
class Character:
    """Represents a player character."""

    name: str
    race: Race
    character_class: CharacterClass
    level: int = 1
    experience: int = 0
    max_hp: int = 20
    current_hp: int = 20
    location: str = "Starting Location"
    background: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        """Create a character from a dictionary."""
        data = data.copy()
        data["race"] = Race[data["race"]]
        data["character_class"] = CharacterClass[data["character_class"]]
        return cls(**data)

    def to_dict(self) -> dict:
        """Convert character to dictionary."""
        return {
            "name": self.name,
            "race": self.race.name,
            "character_class": self.character_class.name,
            "level": self.level,
            "experience": self.experience,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "location": self.location,
            "background": self.background,
        }

    def take_damage(self, amount: int) -> None:
        """Reduce HP by damage amount."""
        self.current_hp = max(0, self.current_hp - amount)

    def heal(self, amount: int) -> None:
        """Restore HP."""
        self.current_hp = min(self.max_hp, self.current_hp + amount)

    def is_alive(self) -> bool:
        """Check if character is alive."""
        return self.current_hp > 0

    def get_status(self) -> str:
        """Get a formatted status string."""
        hp_bar = "█" * (self.current_hp // 2) + "░" * (
            (self.max_hp - self.current_hp) // 2
        )
        return (
            f"{self.name} the {self.race.value} {self.character_class.value} "
            f"[Lvl {self.level}]\n"
            f"HP: {self.current_hp}/{self.max_hp} {hp_bar}\n"
            f"Location: {self.location}"
        )
