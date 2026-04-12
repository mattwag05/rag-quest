"""Lore Encyclopedia — browse-then-query catalog of encountered lore.

Browse layer reads from in-memory GameState (locations, NPCs, factions, items).
Detail layer runs on-demand ``WorldRAG.query_world()`` against the selected
entity for a rich description. No new state — pure wrapper.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

CATEGORIES = ("npcs", "locations", "factions", "items")


@dataclass
class LoreEntry:
    """A single browsable catalog entry."""

    category: str  # one of CATEGORIES
    name: str
    summary: str = ""


class LoreEncyclopedia:
    """Read-only wrapper over existing GameState indexes + WorldRAG detail layer."""

    def __init__(self, game_state):
        self._gs = game_state

    # ------------------------------------------------------------------
    # Browse layer
    # ------------------------------------------------------------------

    def list_entries(self, category: Optional[str] = None) -> List[LoreEntry]:
        """Enumerate everything the player has encountered.

        ``category`` may be one of CATEGORIES or None for all categories.
        """
        result: List[LoreEntry] = []

        if category in (None, "locations"):
            for loc in sorted(getattr(self._gs.world, "visited_locations", [])):
                result.append(
                    LoreEntry("locations", loc, _short_loc_summary(self._gs, loc))
                )

        if category in (None, "npcs"):
            npcs_seen = set(getattr(self._gs.world, "npcs_met", set()))
            rel_npcs = set(getattr(self._gs.relationships, "relationships", {}).keys())
            for name in sorted(npcs_seen | rel_npcs):
                result.append(LoreEntry("npcs", name, _npc_summary(self._gs, name)))

        if category in (None, "factions"):
            factions = getattr(self._gs.relationships, "factions", {})
            for fname, faction in sorted(factions.items()):
                description = getattr(faction, "description", "") or ""
                rep = self._gs.relationships.faction_reputation.get(fname, 0)
                summary = f"{description} [rep {rep:+d}]".strip()
                result.append(LoreEntry("factions", fname, summary))

        if category in (None, "items"):
            inv = getattr(self._gs, "inventory", None)
            items = getattr(inv, "items", {}) if inv else {}
            for item_name in sorted(items.keys()):
                item = items[item_name]
                summary = f"[{getattr(item, 'rarity', 'common')}] {getattr(item, 'description', '')}"
                result.append(LoreEntry("items", item_name, summary.strip()))

        return result

    def categories_with_counts(self) -> List[tuple[str, int]]:
        """Cheap count of each category without materializing LoreEntry objects."""
        npc_count = len(
            set(getattr(self._gs.world, "npcs_met", set()))
            | set(getattr(self._gs.relationships, "relationships", {}).keys())
        )
        return [
            ("npcs", npc_count),
            ("locations", len(getattr(self._gs.world, "visited_locations", set()))),
            ("factions", len(getattr(self._gs.relationships, "factions", {}))),
            ("items", len(getattr(self._gs.inventory, "items", {}))),
        ]

    # ------------------------------------------------------------------
    # Detail layer
    # ------------------------------------------------------------------

    def detail(self, entry: LoreEntry) -> str:
        """Run an on-demand WorldRAG query for a rich description."""
        rag = getattr(self._gs, "world_rag", None)
        if rag is None:
            return entry.summary or "No details available."

        question = _build_detail_question(entry)
        try:
            result = rag.query_world(question)
            if result and result.strip():
                return result.strip()
        except Exception:
            pass

        # Graceful fallback: pull a short snippet from game state.
        return entry.summary or "The world remains silent on this matter."


def _build_detail_question(entry: LoreEntry) -> str:
    if entry.category == "npcs":
        return f"Who is {entry.name}? Describe their role, personality, and any relevant history."
    if entry.category == "locations":
        return f"Describe the location {entry.name} in detail — geography, landmarks, and notable inhabitants."
    if entry.category == "factions":
        return f"Tell me about the faction {entry.name} — their goals, values, leaders, and current influence."
    if entry.category == "items":
        return f"Describe the item {entry.name} — its origins, properties, and any lore associated with it."
    return f"Tell me about {entry.name}."


def _short_loc_summary(game_state, location: str) -> str:
    events = [
        e
        for e in getattr(game_state.world, "recent_events", [])
        if location.lower() in e.lower()
    ]
    if events:
        return events[-1][:120]
    return "Visited."


def _npc_summary(game_state, name: str) -> str:
    rel = getattr(game_state.relationships, "relationships", {}).get(name)
    if rel is None:
        return "Encountered."
    disp = getattr(rel.disposition, "value", str(rel.disposition))
    last = (getattr(rel, "last_interaction_summary", "") or "").strip()
    base = f"{disp} · trust {rel.trust}/100"
    if last:
        base = f"{base} — {last[:80]}"
    return base
