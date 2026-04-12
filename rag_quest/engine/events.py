"""Dynamic world events system for RAG-Quest."""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class EventType(Enum):
    """Types of world events."""
    WEATHER = "Weather"
    POLITICAL = "Political"
    ECONOMIC = "Economic"
    MAGICAL = "Magical"
    NATURAL_DISASTER = "Natural Disaster"
    SOCIAL = "Social"
    COMBAT = "Combat"
    SUPERNATURAL = "Supernatural"


class EventSeverity(Enum):
    """How severe an event is."""
    MINOR = "Minor"
    MODERATE = "Moderate"
    MAJOR = "Major"


@dataclass
class WorldEvent:
    """Something happening in the world independent of the player."""
    name: str
    description: str
    event_type: EventType
    severity: EventSeverity
    duration_turns: int
    turns_remaining: int = 0
    effects: Dict[str, int] = field(default_factory=dict)
    is_active: bool = False
    started_turn: int = 0

    def activate(self, current_turn: int) -> None:
        """Activate the event."""
        self.is_active = True
        self.started_turn = current_turn
        self.turns_remaining = self.duration_turns

    def tick(self) -> None:
        """Advance the event by one turn."""
        self.turns_remaining -= 1
        if self.turns_remaining <= 0:
            self.is_active = False

    def is_expired(self) -> bool:
        """Check if event has expired."""
        return not self.is_active and self.turns_remaining <= 0

    def to_dict(self) -> dict:
        """Serialize event."""
        return {
            "name": self.name,
            "description": self.description,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "duration_turns": self.duration_turns,
            "turns_remaining": self.turns_remaining,
            "effects": self.effects,
            "is_active": self.is_active,
            "started_turn": self.started_turn,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorldEvent":
        """Deserialize event."""
        data = data.copy()
        data["event_type"] = EventType(data["event_type"])
        data["severity"] = EventSeverity(data["severity"])
        return cls(**data)


class EventManager:
    """Generates and manages world events."""

    def __init__(self):
        self.active_events: List[WorldEvent] = []
        self.event_history: List[WorldEvent] = []
        self.event_templates = self._init_event_templates()

    def _init_event_templates(self) -> List[WorldEvent]:
        """Initialize built-in event templates."""
        return [
            WorldEvent(
                name="Merchant Caravan Arrives",
                description="A merchant caravan rolls into town with exotic goods",
                event_type=EventType.ECONOMIC,
                severity=EventSeverity.MINOR,
                duration_turns=5,
                effects={"shop_prices": -15, "item_variety": 20}
            ),
            WorldEvent(
                name="Goblin Raid",
                description="Local goblin tribes raid the area",
                event_type=EventType.COMBAT,
                severity=EventSeverity.MODERATE,
                duration_turns=3,
                effects={"combat_encounters": 30, "enemy_difficulty": 10}
            ),
            WorldEvent(
                name="Festival of Light",
                description="A celebration of light and joy sweeps through the region",
                event_type=EventType.SOCIAL,
                severity=EventSeverity.MINOR,
                duration_turns=4,
                effects={"npc_friendliness": 20, "healing_availability": 15}
            ),
            WorldEvent(
                name="Dark Storm",
                description="A supernatural storm rolls in, shrouding the land in darkness",
                event_type=EventType.WEATHER,
                severity=EventSeverity.MAJOR,
                duration_turns=5,
                effects={"visibility": -30, "enemy_difficulty": 15, "morale": -10}
            ),
            WorldEvent(
                name="Plague Outbreak",
                description="A mysterious illness spreads through the land",
                event_type=EventType.NATURAL_DISASTER,
                severity=EventSeverity.MAJOR,
                duration_turns=7,
                effects={"hp_drain": 1, "healer_availability": 30, "npc_sickness": 10}
            ),
            WorldEvent(
                name="Royal Decree",
                description="The monarch issues a controversial decree",
                event_type=EventType.POLITICAL,
                severity=EventSeverity.MAJOR,
                duration_turns=6,
                effects={"faction_conflicts": 20}
            ),
            WorldEvent(
                name="Magic Surge",
                description="Magical energy floods the world, empowering all magic",
                event_type=EventType.MAGICAL,
                severity=EventSeverity.MODERATE,
                duration_turns=4,
                effects={"spell_power": 20, "mana_recovery": 25}
            ),
            WorldEvent(
                name="Vampire Rise",
                description="The undead emerge from their slumber",
                event_type=EventType.SUPERNATURAL,
                severity=EventSeverity.MAJOR,
                duration_turns=8,
                effects={"night_encounters": 40, "undead_difficulty": 20, "holy_power": 15}
            ),
            WorldEvent(
                name="Harvest Blessing",
                description="Crops flourish and food becomes abundant",
                event_type=EventType.ECONOMIC,
                severity=EventSeverity.MINOR,
                duration_turns=3,
                effects={"food_prices": -20, "health_recovery": 10}
            ),
            WorldEvent(
                name="Dragon Sighting",
                description="A legendary dragon has been spotted in the region",
                event_type=EventType.COMBAT,
                severity=EventSeverity.MAJOR,
                duration_turns=10,
                effects={"legendary_encounters": 50, "reward_multiplier": 50}
            ),
        ]

    def check_for_events(self, turn_number: int, event_chance: float = 0.1) -> Optional[WorldEvent]:
        """
        Check if a new world event should occur this turn.
        
        Args:
            turn_number: Current game turn
            event_chance: Probability (0-1) of event occurring
        
        Returns:
            New WorldEvent if triggered, None otherwise
        """
        if random.random() > event_chance:
            return None

        # Select random event
        event_template = random.choice(self.event_templates)
        
        # Create a new instance
        event = WorldEvent(
            name=event_template.name,
            description=event_template.description,
            event_type=event_template.event_type,
            severity=event_template.severity,
            duration_turns=event_template.duration_turns,
            effects=event_template.effects.copy()
        )
        
        event.activate(turn_number)
        self.active_events.append(event)
        return event

    def apply_effects(self, game_state) -> Dict[str, int]:
        """
        Apply effects from all active events to game state.
        
        Returns:
            Dictionary of applied effects
        """
        cumulative_effects = {}

        for event in self.active_events:
            if event.is_active:
                for effect_key, effect_value in event.effects.items():
                    cumulative_effects[effect_key] = cumulative_effects.get(effect_key, 0) + effect_value

        # Apply specific effects
        if "shop_prices" in cumulative_effects:
            # Would affect merchant prices
            pass
        if "enemy_difficulty" in cumulative_effects:
            # Would increase enemy stats
            pass
        if "npc_friendliness" in cumulative_effects:
            # Would improve NPC relationships
            pass

        return cumulative_effects

    def expire_events(self) -> List[str]:
        """
        Remove ended events and return their names.
        
        Returns:
            List of expired event names
        """
        expired = []
        remaining = []

        for event in self.active_events:
            event.tick()
            if event.is_expired():
                expired.append(event.name)
                self.event_history.append(event)
            else:
                remaining.append(event)

        self.active_events = remaining
        return expired

    def get_active_event_descriptions(self) -> List[str]:
        """Get formatted descriptions of all active events."""
        return [
            f"[{event.severity.value}] {event.name}: {event.description} "
            f"({event.turns_remaining} turns remaining)"
            for event in self.active_events if event.is_active
        ]

    def to_dict(self) -> dict:
        """Serialize event manager."""
        return {
            "active_events": [e.to_dict() for e in self.active_events],
            "event_history": [e.to_dict() for e in self.event_history],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EventManager":
        """Deserialize event manager."""
        mgr = cls()
        mgr.active_events = [WorldEvent.from_dict(e) for e in data.get("active_events", [])]
        mgr.event_history = [WorldEvent.from_dict(e) for e in data.get("event_history", [])]
        return mgr
