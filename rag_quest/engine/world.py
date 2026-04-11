"""World state management."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TimeOfDay(Enum):
    """Time of day."""

    DAWN = "Dawn"
    MORNING = "Morning"
    NOON = "Noon"
    AFTERNOON = "Afternoon"
    DUSK = "Dusk"
    NIGHT = "Night"
    MIDNIGHT = "Midnight"


class Weather(Enum):
    """Weather conditions."""

    CLEAR = "Clear"
    CLOUDY = "Cloudy"
    RAINY = "Rainy"
    STORMY = "Stormy"
    FOGGY = "Foggy"
    SNOWY = "Snowy"


@dataclass
class World:
    """Represents the game world state."""

    name: str
    setting: str  # e.g., "Medieval Fantasy", "Cyberpunk", etc.
    tone: str  # e.g., "Dark", "Heroic", "Whimsical"
    current_time: TimeOfDay = TimeOfDay.MORNING
    weather: Weather = Weather.CLEAR
    day_number: int = 1
    visited_locations: set[str] = field(default_factory=set)
    npcs_met: set[str] = field(default_factory=set)
    recent_events: list[str] = field(default_factory=list)
    discovered_items: list[str] = field(default_factory=list)

    def advance_time(self) -> None:
        """Advance to next time period."""
        times = list(TimeOfDay)
        current_idx = times.index(self.current_time)
        next_idx = (current_idx + 1) % len(times)

        if next_idx == 0:  # Wrapped to dawn of next day
            self.day_number += 1

        self.current_time = times[next_idx]

    def add_visited_location(self, location: str) -> None:
        """Record a visited location."""
        self.visited_locations.add(location)

    def add_met_npc(self, npc: str) -> None:
        """Record meeting an NPC."""
        self.npcs_met.add(npc)

    def add_event(self, event: str) -> None:
        """Add a recent event."""
        self.recent_events.append(event)
        if len(self.recent_events) > 10:
            self.recent_events.pop(0)

    def get_context(self) -> str:
        """Get a formatted world context string."""
        lines = [
            f"Day {self.day_number} - {self.current_time.value}",
            f"Weather: {self.weather.value}",
            f"Setting: {self.setting} ({self.tone})",
        ]
        return " | ".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "setting": self.setting,
            "tone": self.tone,
            "current_time": self.current_time.name,
            "weather": self.weather.name,
            "day_number": self.day_number,
            "visited_locations": list(self.visited_locations),
            "npcs_met": list(self.npcs_met),
            "recent_events": self.recent_events,
            "discovered_items": self.discovered_items,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "World":
        """Create from dictionary."""
        data = data.copy()
        data["current_time"] = TimeOfDay[data["current_time"]]
        data["weather"] = Weather[data["weather"]]
        data["visited_locations"] = set(data.get("visited_locations", []))
        data["npcs_met"] = set(data.get("npcs_met", []))
        return cls(**data)
