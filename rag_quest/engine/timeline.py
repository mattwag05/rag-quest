"""Player Journal & Timeline — chronological event log and bookmarked highlights.

Leverages `StateChange` produced by `engine.state_parser` to emit one or more
`TimelineEvent` dataclasses per turn. Bookmarks capture the full narrator prose
for the current turn. Both serialize with the save file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Optional

# Event type constants mirror state-parser categories.
EVENT_TYPES = ("location", "combat", "quest", "npc", "item", "world_event")
DEFAULT_MAX_EVENTS = 2000


@dataclass
class TimelineEvent:
    """A structured, one-line summary of something that happened this turn."""

    turn: int
    timestamp: str
    type: str  # one of EVENT_TYPES
    summary: str
    entities: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "turn": self.turn,
            "timestamp": self.timestamp,
            "type": self.type,
            "summary": self.summary,
            "entities": list(self.entities),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimelineEvent":
        return cls(
            turn=int(data.get("turn", 0)),
            timestamp=str(data.get("timestamp", "")),
            type=str(data.get("type", "world_event")),
            summary=str(data.get("summary", "")),
            entities=list(data.get("entities", [])),
        )


@dataclass
class Bookmark:
    """A player-saved highlight with full narrator prose."""

    turn: int
    timestamp: str
    note: str
    player_input: str
    narrator_prose: str
    location: str = ""

    def to_dict(self) -> dict:
        return {
            "turn": self.turn,
            "timestamp": self.timestamp,
            "note": self.note,
            "player_input": self.player_input,
            "narrator_prose": self.narrator_prose,
            "location": self.location,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Bookmark":
        return cls(
            turn=int(data.get("turn", 0)),
            timestamp=str(data.get("timestamp", "")),
            note=str(data.get("note", "")),
            player_input=str(data.get("player_input", "")),
            narrator_prose=str(data.get("narrator_prose", "")),
            location=str(data.get("location", "")),
        )


class Timeline:
    """Container for TimelineEvents and Bookmarks with size-guarded rotation."""

    def __init__(self, max_events: int = DEFAULT_MAX_EVENTS):
        self.events: List[TimelineEvent] = []
        self.bookmarks: List[Bookmark] = []
        self.max_events = max_events

    def add_event(self, event: TimelineEvent) -> None:
        self.events.append(event)
        # Oldest-first rotation. Bookmarks are never rotated.
        if len(self.events) > self.max_events:
            overflow = len(self.events) - self.max_events
            del self.events[:overflow]

    def record_from_state_change(
        self,
        turn: int,
        change,
        player_input: str = "",
        location: str = "",
    ) -> List[TimelineEvent]:
        """Translate a StateChange into one or more TimelineEvents.

        Returns the newly-added events so callers can display them if desired.
        """
        now = datetime.now().isoformat(timespec="seconds")
        new_events: List[TimelineEvent] = []

        def _emit(
            type_: str, summary: str, entities: Optional[Iterable[str]] = None
        ) -> None:
            ev = TimelineEvent(
                turn=turn,
                timestamp=now,
                type=type_,
                summary=summary,
                entities=list(entities or []),
            )
            self.add_event(ev)
            new_events.append(ev)

        # Location
        if getattr(change, "location", None):
            _emit("location", f"Travelled to {change.location}", [change.location])

        # Combat damage
        if getattr(change, "damage_taken", 0) > 0:
            _emit("combat", f"Took {change.damage_taken} damage", [])

        # Healing
        if getattr(change, "hp_healed", 0) > 0:
            _emit("combat", f"Healed {change.hp_healed} HP", [])

        # Items
        for item in getattr(change, "items_gained", []) or []:
            _emit("item", f"Obtained {item}", [item])
        for item in getattr(change, "items_lost", []) or []:
            _emit("item", f"Lost {item}", [item])

        # Quests
        if getattr(change, "quest_offered", None):
            _emit(
                "quest",
                f"Quest offered: {change.quest_offered}",
                [change.quest_offered],
            )
        if getattr(change, "quest_completed", None):
            _emit(
                "quest",
                f"Quest completed: {change.quest_completed}",
                [change.quest_completed],
            )

        # NPCs
        if getattr(change, "npc_met", None):
            _emit("npc", f"Met {change.npc_met}", [change.npc_met])
        if getattr(change, "npc_recruited", None):
            _emit("npc", f"Recruited {change.npc_recruited}", [change.npc_recruited])

        # World events
        if getattr(change, "world_event_triggered", None):
            _emit(
                "world_event",
                f"World event: {change.world_event_triggered}",
                [change.world_event_triggered],
            )

        # Fallback — if nothing concrete, still record a faint trace from player_input.
        if not new_events and player_input:
            _emit("world_event", player_input[:80], [])

        return new_events

    def add_bookmark(self, bookmark: Bookmark) -> None:
        self.bookmarks.append(bookmark)

    def get_events(
        self, filter_type: Optional[str] = None, limit: Optional[int] = None
    ) -> List[TimelineEvent]:
        result = self.events
        if filter_type and filter_type != "all":
            result = [e for e in result if e.type == filter_type]
        if limit is not None and limit > 0:
            result = result[-limit:]
        return list(result)

    def last_event_on_turn(self, turn: int) -> Optional[TimelineEvent]:
        for ev in reversed(self.events):
            if ev.turn == turn:
                return ev
        return None

    def to_dict(self) -> dict:
        return {
            "events": [e.to_dict() for e in self.events],
            "bookmarks": [b.to_dict() for b in self.bookmarks],
            "max_events": self.max_events,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "Timeline":
        if not data:
            return cls()
        tl = cls(max_events=int(data.get("max_events", DEFAULT_MAX_EVENTS)))
        try:
            tl.events = [TimelineEvent.from_dict(e) for e in data.get("events", [])]
        except Exception:
            tl.events = []
        try:
            tl.bookmarks = [Bookmark.from_dict(b) for b in data.get("bookmarks", [])]
        except Exception:
            tl.bookmarks = []
        return tl
