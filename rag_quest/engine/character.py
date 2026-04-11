"""Character models for the game."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict


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
class Ability:
    """A special ability that a character can use."""
    name: str
    description: str
    damage_formula: str  # e.g., "2d8+str"
    unlock_level: int
    cooldown: int = 0


# Class abilities: unlock at specific levels
CLASS_ABILITIES = {
    CharacterClass.FIGHTER: [
        Ability("Power Strike", "Deal 2x damage", "2d8+str", 1),
        Ability("Shield Wall", "Gain +3 defense", "0", 3),
        Ability("Cleave", "Hit all enemies", "1d8+str", 6),
    ],
    CharacterClass.MAGE: [
        Ability("Fireball", "AoE fire damage", "2d6+int", 1),
        Ability("Heal", "Restore HP", "2d6+int", 2),
        Ability("Arcane Shield", "Temporary +2 defense", "0", 4),
    ],
    CharacterClass.ROGUE: [
        Ability("Backstab", "3x damage on surprise", "3d6+dex", 1),
        Ability("Dodge", "Avoid next attack", "0", 3),
        Ability("Steal", "Grab enemy item", "0", 5),
    ],
    CharacterClass.RANGER: [
        Ability("Arrow Volley", "Ranged AoE damage", "2d6+dex", 1),
        Ability("Track", "Reveal nearby threats", "0", 3),
        Ability("Animal Companion", "Summon ally", "0", 6),
    ],
    CharacterClass.CLERIC: [
        Ability("Divine Heal", "Large healing", "3d6+wis", 1),
        Ability("Smite", "Holy damage", "2d6+wis", 2),
        Ability("Bless", "Party buff", "0", 4),
    ],
}

# XP thresholds for leveling
XP_THRESHOLDS = [0, 100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500]


@dataclass
class Equipment:
    """Character equipment slot."""
    weapon: Optional[str] = None
    armor: Optional[str] = None
    accessory: Optional[str] = None


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
    
    # Combat stats (6 D&D attributes)
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    
    # Defense & attack modifiers
    attack_bonus: int = 0
    defense_ac: int = 10
    damage_dice: str = "1d6"  # Damage per attack
    
    # Progression
    unlocked_abilities: List[Ability] = field(default_factory=list)
    equipment: Equipment = field(default_factory=Equipment)
    
    # Traits by race/class for stat boosts
    def __post_init__(self):
        """Initialize character with race/class bonuses."""
        self._apply_race_bonuses()
        self._apply_class_bonuses()
        self._recalculate_combat_stats()
        self._unlock_starting_abilities()
    
    def _apply_race_bonuses(self):
        """Apply racial stat bonuses."""
        if self.race == Race.HUMAN:
            self.strength += 1
            self.dexterity += 1
        elif self.race == Race.ELF:
            self.dexterity += 2
        elif self.race == Race.DWARF:
            self.constitution += 2
        elif self.race == Race.HALFLING:
            self.dexterity += 2
            self.charisma += 1
        elif self.race == Race.ORC:
            self.strength += 2
            self.constitution += 1
    
    def _apply_class_bonuses(self):
        """Apply class-specific bonuses."""
        if self.character_class == CharacterClass.FIGHTER:
            self.strength += 2
            self.constitution += 1
            self.max_hp = 30
            self.current_hp = 30
            self.damage_dice = "1d8"
        elif self.character_class == CharacterClass.MAGE:
            self.intelligence += 2
            self.wisdom += 1
            self.max_hp = 15
            self.current_hp = 15
            self.damage_dice = "1d4"
        elif self.character_class == CharacterClass.ROGUE:
            self.dexterity += 2
            self.charisma += 1
            self.max_hp = 18
            self.current_hp = 18
            self.damage_dice = "1d6"
        elif self.character_class == CharacterClass.RANGER:
            self.dexterity += 1
            self.wisdom += 2
            self.max_hp = 22
            self.current_hp = 22
            self.damage_dice = "1d8"
        elif self.character_class == CharacterClass.CLERIC:
            self.wisdom += 2
            self.strength += 1
            self.max_hp = 26
            self.current_hp = 26
            self.damage_dice = "1d6"
    
    def _recalculate_combat_stats(self):
        """Recalculate attack and defense based on stats."""
        # Attack bonus is based on primary stat for class
        if self.character_class == CharacterClass.FIGHTER:
            self.attack_bonus = (self.strength - 10) // 2
        elif self.character_class == CharacterClass.MAGE:
            self.attack_bonus = (self.intelligence - 10) // 2
        elif self.character_class == CharacterClass.ROGUE:
            self.attack_bonus = (self.dexterity - 10) // 2
        elif self.character_class == CharacterClass.RANGER:
            self.attack_bonus = (self.dexterity - 10) // 2
        elif self.character_class == CharacterClass.CLERIC:
            self.attack_bonus = (self.wisdom - 10) // 2
        
        # Defense AC (lower is better in D&D)
        self.defense_ac = 10 + (self.dexterity - 10) // 2
    
    def _unlock_starting_abilities(self):
        """Unlock starting abilities based on class."""
        self.unlocked_abilities = []
        if self.character_class in CLASS_ABILITIES:
            for ability in CLASS_ABILITIES[self.character_class]:
                if ability.unlock_level <= self.level:
                    self.unlocked_abilities.append(ability)
    
    def gain_xp(self, amount: int) -> Optional[int]:
        """Gain experience and level up if needed. Returns new level or None."""
        self.experience += amount
        old_level = self.level
        
        # Check for level up
        while self.level < len(XP_THRESHOLDS) - 1:
            if self.experience >= XP_THRESHOLDS[self.level + 1]:
                self.level += 1
            else:
                break
        
        # Apply stat increases on level up
        if self.level > old_level:
            self._apply_level_up_bonus()
            self._recalculate_combat_stats()
            self._unlock_new_abilities()
            return self.level
        
        return None
    
    def _apply_level_up_bonus(self):
        """Apply stat bonuses on level up."""
        # Increase primary stat by 1
        if self.character_class == CharacterClass.FIGHTER:
            self.strength += 1
        elif self.character_class == CharacterClass.MAGE:
            self.intelligence += 1
        elif self.character_class == CharacterClass.ROGUE:
            self.dexterity += 1
        elif self.character_class == CharacterClass.RANGER:
            self.dexterity += 1
        elif self.character_class == CharacterClass.CLERIC:
            self.wisdom += 1
        
        # Always increase HP
        hp_gain = 5 + (self.constitution - 10) // 2
        self.max_hp += max(1, hp_gain)
        self.current_hp = self.max_hp
    
    def _unlock_new_abilities(self):
        """Unlock new abilities at current level."""
        if self.character_class in CLASS_ABILITIES:
            for ability in CLASS_ABILITIES[self.character_class]:
                if ability.unlock_level == self.level and ability not in self.unlocked_abilities:
                    self.unlocked_abilities.append(ability)
    
    def get_abilities(self) -> List[str]:
        """Get list of unlocked ability names."""
        return [a.name for a in self.unlocked_abilities]

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
            "strength": self.strength,
            "dexterity": self.dexterity,
            "constitution": self.constitution,
            "intelligence": self.intelligence,
            "wisdom": self.wisdom,
            "charisma": self.charisma,
            "attack_bonus": self.attack_bonus,
            "defense_ac": self.defense_ac,
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
        
        stats = f"STR {self.strength} | DEX {self.dexterity} | CON {self.constitution} | INT {self.intelligence} | WIS {self.wisdom} | CHA {self.charisma}"
        abilities_str = ", ".join(self.get_abilities()) if self.unlocked_abilities else "None yet"
        
        return (
            f"{self.name} the {self.race.value} {self.character_class.value} "
            f"[Lvl {self.level}]\n"
            f"HP: {self.current_hp}/{self.max_hp} {hp_bar}\n"
            f"XP: {self.experience}/{XP_THRESHOLDS[min(self.level, len(XP_THRESHOLDS)-1)]}\n"
            f"Stats: {stats}\n"
            f"Location: {self.location}\n"
            f"Abilities: {abilities_str}"
        )
    
    def get_short_status(self) -> str:
        """Get a short one-line status."""
        hp_bar = "█" * (self.current_hp // 2) + "░" * (
            (self.max_hp - self.current_hp) // 2
        )
        return f"[{self.name} | Lvl {self.level} | HP: {self.current_hp}/{self.max_hp} {hp_bar}]"
