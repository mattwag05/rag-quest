"""Multi-character party system for RAG-Quest."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict


class CombatStyle(Enum):
    """How companions fight in combat."""
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    SUPPORT = "support"
    BALANCED = "balanced"


class DialogueStyle(Enum):
    """How companions speak."""
    FORMAL = "formal"
    CASUAL = "casual"
    GRUMPY = "grumpy"
    CHEERFUL = "cheerful"
    MYSTERIOUS = "mysterious"


@dataclass
class PartyMember:
    """An NPC companion with stats, abilities, personality, and loyalty."""

    name: str
    race: str
    character_class: str
    level: int = 1
    current_hp: int = 20
    max_hp: int = 20
    experience: int = 0

    # Combat stats
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    # Personality and loyalty
    personality_traits: List[str] = field(default_factory=list)
    loyalty: int = 50  # 0-100, starts neutral
    combat_style: CombatStyle = CombatStyle.BALANCED
    dialogue_style: DialogueStyle = DialogueStyle.CASUAL
    backstory: str = ""

    # Inventory management
    inventory_slots: int = 10
    items_carried: List[str] = field(default_factory=list)

    # Status tracking
    is_alive: bool = True
    status_effects: List[str] = field(default_factory=list)

    def take_damage(self, amount: int) -> None:
        """Reduce HP and handle death."""
        self.current_hp = max(0, self.current_hp - amount)
        if self.current_hp <= 0:
            self.is_alive = False

    def heal(self, amount: int) -> None:
        """Restore HP."""
        self.current_hp = min(self.max_hp, self.current_hp + amount)

    def modify_loyalty(self, amount: int, reason: str = "") -> None:
        """
        Modify loyalty score.
        
        Args:
            amount: Change to loyalty (-100 to +100)
            reason: Reason for loyalty change (for logging)
        """
        self.loyalty = max(0, min(100, self.loyalty + amount))

    def can_be_recruited(self) -> bool:
        """Check if companion can be recruited (loyalty >= 50)."""
        return self.loyalty >= 50

    def will_leave_party(self) -> bool:
        """Check if companion will abandon the party (loyalty < 20)."""
        return self.loyalty < 20

    def add_item(self, item_name: str) -> bool:
        """Add item to companion inventory. Returns True if successful."""
        if len(self.items_carried) >= self.inventory_slots:
            return False
        self.items_carried.append(item_name)
        return True

    def remove_item(self, item_name: str) -> bool:
        """Remove item from companion inventory. Returns True if successful."""
        if item_name in self.items_carried:
            self.items_carried.remove(item_name)
            return True
        return False

    def get_combat_power(self) -> int:
        """Calculate combat power as aggregate of stats."""
        return sum([
            self.strength, self.dexterity, self.constitution,
            self.intelligence, self.wisdom, self.charisma
        ]) + (self.level * 10)

    def to_dict(self) -> dict:
        """Serialize party member."""
        return {
            "name": self.name,
            "race": self.race,
            "character_class": self.character_class,
            "level": self.level,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "experience": self.experience,
            "strength": self.strength,
            "dexterity": self.dexterity,
            "constitution": self.constitution,
            "intelligence": self.intelligence,
            "wisdom": self.wisdom,
            "charisma": self.charisma,
            "personality_traits": self.personality_traits,
            "loyalty": self.loyalty,
            "combat_style": self.combat_style.value,
            "dialogue_style": self.dialogue_style.value,
            "backstory": self.backstory,
            "inventory_slots": self.inventory_slots,
            "items_carried": self.items_carried,
            "is_alive": self.is_alive,
            "status_effects": self.status_effects,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PartyMember":
        """Deserialize party member."""
        data = data.copy()
        data["combat_style"] = CombatStyle(data["combat_style"])
        data["dialogue_style"] = DialogueStyle(data["dialogue_style"])
        return cls(**data)


class Party:
    """Manages the player's party of companions."""

    def __init__(self, max_size: int = 4):
        """Initialize party. Default size includes player."""
        self.members: List[PartyMember] = []
        self.max_size = max_size

    def add_member(self, member: PartyMember) -> bool:
        """
        Add a member to the party.
        
        Returns:
            True if added, False if party is full
        """
        if len(self.members) >= self.max_size:
            return False
        self.members.append(member)
        return True

    def remove_member(self, name: str) -> bool:
        """
        Remove a member from the party.
        
        Returns:
            True if removed, False if member not found
        """
        for i, member in enumerate(self.members):
            if member.name == name:
                self.members.pop(i)
                return True
        return False

    def get_member(self, name: str) -> Optional[PartyMember]:
        """Get a party member by name."""
        for member in self.members:
            if member.name == name:
                return member
        return None

    def get_active_members(self) -> List[PartyMember]:
        """Get all alive party members."""
        return [m for m in self.members if m.is_alive]

    def party_strength(self) -> int:
        """Calculate aggregate combat power of party."""
        return sum(m.get_combat_power() for m in self.get_active_members())

    def rest(self) -> None:
        """Heal all party members to full HP."""
        for member in self.members:
            if member.is_alive:
                member.heal(member.max_hp)

    def check_loyalty_departures(self) -> List[str]:
        """
        Check for members who leave due to low loyalty.
        
        Returns:
            List of member names who left
        """
        departing = []
        for member in self.members[:]:
            if member.will_leave_party():
                departing.append(member.name)
                self.members.remove(member)
        return departing

    def get_party_status(self) -> str:
        """Get formatted party status display."""
        if not self.members:
            return "Party: Empty"

        status_lines = [f"Party ({len(self.get_active_members())}/{len(self.members)} alive):"]
        for member in self.members:
            status_char = "✓" if member.is_alive else "✗"
            hp_bar_length = 15
            hp_filled = int((member.current_hp / member.max_hp) * hp_bar_length)
            hp_bar = "█" * hp_filled + "░" * (hp_bar_length - hp_filled)
            loyalty_display = f"[Loyalty: {member.loyalty}]"
            status_lines.append(
                f"  {status_char} {member.name} (L{member.level}) "
                f"HP:{hp_bar} {loyalty_display}"
            )

        return "\n".join(status_lines)

    def to_dict(self) -> dict:
        """Serialize party."""
        return {
            "members": [m.to_dict() for m in self.members],
            "max_size": self.max_size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Party":
        """Deserialize party."""
        party = cls(max_size=data.get("max_size", 4))
        party.members = [PartyMember.from_dict(m) for m in data.get("members", [])]
        return party
