"""NPC relationship and faction system for RAG-Quest."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class Disposition(Enum):
    """NPC relationship status."""

    HOSTILE = "Hostile"
    UNFRIENDLY = "Unfriendly"
    NEUTRAL = "Neutral"
    FRIENDLY = "Friendly"
    ALLIED = "Allied"

    @classmethod
    def from_trust(cls, trust: int) -> "Disposition":
        """Determine disposition based on trust score."""
        if trust >= 80:
            return cls.ALLIED
        elif trust >= 60:
            return cls.FRIENDLY
        elif trust >= 40:
            return cls.NEUTRAL
        elif trust >= 20:
            return cls.UNFRIENDLY
        else:
            return cls.HOSTILE


@dataclass
class Faction:
    """A group/organization NPCs belong to."""

    name: str
    description: str
    values: List[str] = field(default_factory=list)
    members: List[str] = field(default_factory=list)
    color: str = "cyan"

    def to_dict(self) -> dict:
        """Serialize faction."""
        return {
            "name": self.name,
            "description": self.description,
            "values": self.values,
            "members": self.members,
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Faction":
        """Deserialize faction. Strips extra keys from newer save builds."""
        from ._serialization import filter_init_kwargs

        data = dict(data)
        data.setdefault("name", "Unknown Faction")
        data.setdefault("description", "")
        return cls(**filter_init_kwargs(cls, data))


@dataclass
class NPC:
    """Represents an NPC that can be tracked."""

    name: str
    role: str
    disposition: Disposition = Disposition.NEUTRAL
    trust: int = 50  # 0-100
    interactions_count: int = 0
    last_interaction_summary: str = ""
    faction_affiliations: List[str] = field(default_factory=list)
    gifts_given: List[str] = field(default_factory=list)
    quests_completed_for: List[str] = field(default_factory=list)
    dialogue_options_unlocked: List[str] = field(default_factory=list)

    def modify_trust(self, amount: int, reason: str = "") -> None:
        """Modify trust with NPC."""
        self.trust = max(0, min(100, self.trust + amount))
        self.disposition = Disposition.from_trust(self.trust)
        if reason:
            self.last_interaction_summary = reason
        self.interactions_count += 1

    def give_gift(self, gift_name: str) -> None:
        """Record giving a gift to NPC."""
        self.gifts_given.append(gift_name)
        self.modify_trust(10, f"Gave gift: {gift_name}")

    def complete_quest(self, quest_name: str) -> None:
        """Record completing a quest for NPC."""
        self.quests_completed_for.append(quest_name)
        self.modify_trust(15, f"Completed quest: {quest_name}")

    def unlock_dialogue_option(self, option: str) -> None:
        """Unlock a dialogue option at higher trust levels."""
        if option not in self.dialogue_options_unlocked:
            self.dialogue_options_unlocked.append(option)

    def can_recruit(self) -> bool:
        """Check if NPC can be recruited (friendly or allied)."""
        return self.disposition in [Disposition.FRIENDLY, Disposition.ALLIED]

    def get_shop_discount(self) -> float:
        """Get shop price multiplier based on trust (0.5 to 1.0)."""
        return max(0.5, 1.0 - (self.trust / 200))

    def to_dict(self) -> dict:
        """Serialize NPC."""
        return {
            "name": self.name,
            "role": self.role,
            "disposition": self.disposition.value,
            "trust": self.trust,
            "interactions_count": self.interactions_count,
            "last_interaction_summary": self.last_interaction_summary,
            "faction_affiliations": self.faction_affiliations,
            "gifts_given": self.gifts_given,
            "quests_completed_for": self.quests_completed_for,
            "dialogue_options_unlocked": self.dialogue_options_unlocked,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NPC":
        """Deserialize NPC with safe defaults for corrupted/partial saves."""
        from ._serialization import filter_init_kwargs, safe_enum

        data = dict(data)
        data["disposition"] = safe_enum(
            Disposition, data.get("disposition"), Disposition.NEUTRAL
        )
        data.setdefault("name", "Unknown")
        data.setdefault("role", "Unknown")
        return cls(**filter_init_kwargs(cls, data))


@dataclass
class NPCRelationship:
    """Tracks relationship with a specific NPC."""

    npc_name: str
    disposition: Disposition = Disposition.NEUTRAL
    trust: int = 50  # 0-100
    interactions_count: int = 0
    last_interaction_summary: str = ""
    faction_affiliations: List[str] = field(default_factory=list)
    gifts_given: List[str] = field(default_factory=list)
    quests_completed_for: List[str] = field(default_factory=list)
    dialogue_options_unlocked: List[str] = field(default_factory=list)

    def modify_trust(self, amount: int, reason: str = "") -> None:
        """
        Modify trust with NPC.

        Args:
            amount: Change to trust (-100 to +100)
            reason: Reason for change (stored in last interaction)
        """
        self.trust = max(0, min(100, self.trust + amount))
        self.disposition = Disposition.from_trust(self.trust)
        if reason:
            self.last_interaction_summary = reason
        self.interactions_count += 1

    def give_gift(self, gift_name: str) -> None:
        """Record giving a gift to NPC."""
        self.gifts_given.append(gift_name)
        self.modify_trust(10, f"Gave gift: {gift_name}")

    def complete_quest(self, quest_name: str) -> None:
        """Record completing a quest for NPC."""
        self.quests_completed_for.append(quest_name)
        self.modify_trust(15, f"Completed quest: {quest_name}")

    def unlock_dialogue_option(self, option: str) -> None:
        """Unlock a dialogue option at higher trust levels."""
        if option not in self.dialogue_options_unlocked:
            self.dialogue_options_unlocked.append(option)

    def can_recruit(self) -> bool:
        """Check if NPC can be recruited (friendly or allied)."""
        return self.disposition in [Disposition.FRIENDLY, Disposition.ALLIED]

    def get_shop_discount(self) -> float:
        """Get shop price multiplier based on trust (0.5 to 1.0)."""
        return max(0.5, 1.0 - (self.trust / 200))

    def to_dict(self) -> dict:
        """Serialize relationship."""
        return {
            "npc_name": self.npc_name,
            "disposition": self.disposition.value,
            "trust": self.trust,
            "interactions_count": self.interactions_count,
            "last_interaction_summary": self.last_interaction_summary,
            "faction_affiliations": self.faction_affiliations,
            "gifts_given": self.gifts_given,
            "quests_completed_for": self.quests_completed_for,
            "dialogue_options_unlocked": self.dialogue_options_unlocked,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NPCRelationship":
        """Deserialize relationship with safe defaults for corrupted saves."""
        from ._serialization import filter_init_kwargs, safe_enum

        data = dict(data)
        data["disposition"] = safe_enum(
            Disposition, data.get("disposition"), Disposition.NEUTRAL
        )
        data.setdefault("npc_name", "Unknown")
        return cls(**filter_init_kwargs(cls, data))


class RelationshipManager:
    """Manages all NPC relationships and faction standings."""

    def __init__(self):
        self.relationships: Dict[str, NPCRelationship] = {}
        self.npcs: Dict[str, NPC] = {}
        self.factions: Dict[str, Faction] = {}
        self.faction_reputation: Dict[str, int] = (
            {}
        )  # Faction name -> reputation (-100 to 100)

    def add_npc(self, npc_name: str, role: str = "Unknown") -> NPC:
        """Add an NPC to track relationships with."""
        npc = NPC(name=npc_name, role=role)
        self.npcs[npc_name] = npc
        return npc

    def add_faction(
        self,
        name: str,
        description: str,
        values: List[str] = None,
        members: List[str] = None,
    ) -> Faction:
        """Create a new faction."""
        faction = Faction(
            name=name,
            description=description,
            values=values or [],
            members=members or [],
        )
        self.factions[name] = faction
        self.faction_reputation[name] = 0
        return faction

    def get_or_create_relationship(self, npc_name: str) -> NPCRelationship:
        """Get existing relationship or create new neutral one."""
        if npc_name not in self.relationships:
            self.relationships[npc_name] = NPCRelationship(npc_name)
        return self.relationships[npc_name]

    def modify_relationship(self, npc_name: str, amount: int, reason: str = "") -> None:
        """Modify relationship with an NPC."""
        rel = self.get_or_create_relationship(npc_name)
        rel.modify_trust(amount, reason)

        # Propagate faction reputation changes
        for faction_name in rel.faction_affiliations:
            if faction_name in self.faction_reputation:
                self.faction_reputation[faction_name] += amount // 2

    def modify_faction_reputation(self, faction_name: str, amount: int) -> None:
        """Modify reputation with a faction."""
        if faction_name in self.faction_reputation:
            self.faction_reputation[faction_name] = max(
                -100, min(100, self.faction_reputation[faction_name] + amount)
            )

    def get_disposition(self, npc_name: str) -> Disposition:
        """Get NPC's current disposition toward player."""
        rel = self.get_or_create_relationship(npc_name)
        return rel.disposition

    def check_faction_standing(self, faction_name: str) -> int:
        """Get player's reputation with a faction."""
        return self.faction_reputation.get(faction_name, 0)

    def get_available_interactions(self, npc_name: str) -> List[str]:
        """Get available dialogue options with an NPC based on trust."""
        rel = self.get_or_create_relationship(npc_name)
        interactions = []

        if rel.disposition == Disposition.HOSTILE:
            interactions = ["Attempt to intimidate", "Try to flee"]
        elif rel.disposition == Disposition.UNFRIENDLY:
            interactions = ["Greet cautiously", "Offer bribe"]
        elif rel.disposition == Disposition.NEUTRAL:
            interactions = ["Greet", "Ask for directions", "Trade"]
        elif rel.disposition == Disposition.FRIENDLY:
            interactions = [
                "Chat",
                "Ask for help",
                "Trade",
                "Exchange gifts",
                "Request information",
            ]
        elif rel.disposition == Disposition.ALLIED:
            interactions = [
                "Chat",
                "Ask for help",
                "Trade",
                "Exchange gifts",
                "Request information",
                "Recruit to party",
                "Request favor",
            ]

        interactions.extend(rel.dialogue_options_unlocked)
        return list(set(interactions))

    def get_relationship_summary(self, npc_name: str) -> str:
        """Get formatted relationship summary."""
        rel = self.get_or_create_relationship(npc_name)
        return (
            f"{npc_name} ({rel.disposition.value})\n"
            f"  Trust: {rel.trust}/100\n"
            f"  Interactions: {rel.interactions_count}\n"
            f"  Factions: {', '.join(rel.faction_affiliations) or 'None'}\n"
            f"  Last interaction: {rel.last_interaction_summary or 'None'}"
        )

    def relationship_summary(self) -> str:
        """Get formatted display of all relationships."""
        if not self.relationships:
            return "No relationships recorded."

        lines = ["=== NPC Relationships ==="]
        for npc_name, rel in sorted(self.relationships.items()):
            trust_bar_length = 10
            trust_filled = int((rel.trust / 100) * trust_bar_length)
            trust_bar = "█" * trust_filled + "░" * (trust_bar_length - trust_filled)
            lines.append(
                f"{npc_name}: {rel.disposition.value} [{trust_bar}] ({rel.trust}/100)"
            )

        lines.append("\n=== Faction Reputation ===")
        for faction_name, rep in sorted(self.faction_reputation.items()):
            rep_display = f"{rep:+d}" if rep != 0 else "Neutral"
            lines.append(f"{faction_name}: {rep_display}")

        return "\n".join(lines)

    def change_disposition(self, npc_name: str, disposition: str) -> None:
        """Change NPC disposition (backwards compatibility alias).

        Args:
            npc_name: Name of the NPC
            disposition: Disposition level as string
        """
        # Map disposition strings to trust values
        disposition_map = {
            "hostile": 10,
            "unfriendly": 30,
            "neutral": 50,
            "friendly": 70,
            "allied": 90,
        }

        trust_value = disposition_map.get(disposition.lower(), 50)
        change = trust_value - 50  # Center around neutral
        self.modify_relationship(
            npc_name, change, f"Disposition changed to {disposition}"
        )

    def create_faction(
        self,
        name: str,
        description: str,
        values: List[str] = None,
        members: List[str] = None,
    ) -> Faction:
        """Create a new faction (backwards compatibility alias for add_faction).

        Args:
            name: Faction name
            description: Faction description
            values: List of faction values
            members: List of initial members

        Returns:
            Created Faction object
        """
        return self.add_faction(name, description, values, members)

    def to_dict(self) -> dict:
        """Serialize relationship manager."""
        return {
            "npcs": {name: npc.to_dict() for name, npc in self.npcs.items()},
            "relationships": {
                name: rel.to_dict() for name, rel in self.relationships.items()
            },
            "factions": {name: fac.to_dict() for name, fac in self.factions.items()},
            "faction_reputation": self.faction_reputation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RelationshipManager":
        """Deserialize relationship manager."""
        mgr = cls()
        mgr.npcs = {
            name: NPC.from_dict(npc_data)
            for name, npc_data in data.get("npcs", {}).items()
        }
        mgr.relationships = {
            name: NPCRelationship.from_dict(rel)
            for name, rel in data.get("relationships", {}).items()
        }
        mgr.factions = {
            name: Faction.from_dict(fac)
            for name, fac in data.get("factions", {}).items()
        }
        mgr.faction_reputation = data.get("faction_reputation", {})
        return mgr
