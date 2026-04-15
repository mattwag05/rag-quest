"""Structured context block builder for the narrator (v0.9 Phase 2).

Implements ``docs/MEMORY_ARCHITECTURE.md`` §4. The narrator's only
read path into WorldDB; LightRAG is queried exactly once per turn for
lore flavor (Step 6). Step 5 narrative echoes are deferred — see
beads ``rag-quest-50j``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Optional

from ..engine.relationships import Disposition
from .world_db import WorldDB, canonical_name

ProfileName = Literal["fast", "balanced", "deep"]


@dataclass(frozen=True)
class AssemblyProfile:
    """Tunable budgets per RAG profile (``docs/MEMORY_ARCHITECTURE.md`` §4.2)."""

    name: str
    recent_event_count: int
    entity_snapshot_tokens: int
    historical_event_tokens: int
    lore_tokens: int


PROFILES: dict[str, AssemblyProfile] = {
    "fast": AssemblyProfile(
        name="fast",
        recent_event_count=5,
        entity_snapshot_tokens=800,
        historical_event_tokens=500,
        lore_tokens=400,
    ),
    "balanced": AssemblyProfile(
        name="balanced",
        recent_event_count=10,
        entity_snapshot_tokens=1500,
        historical_event_tokens=1000,
        lore_tokens=800,
    ),
    "deep": AssemblyProfile(
        name="deep",
        recent_event_count=15,
        entity_snapshot_tokens=2000,
        historical_event_tokens=1500,
        lore_tokens=1200,
    ),
}


_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]+")
_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "my",
        "your",
        "his",
        "her",
        "its",
        "our",
        "their",
        "to",
        "of",
        "in",
        "on",
        "at",
        "for",
        "with",
        "from",
        "by",
        "into",
        "onto",
        "out",
        "up",
        "down",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "shall",
        "should",
        "can",
        "could",
        "may",
        "might",
        "must",
        "this",
        "that",
        "these",
        "those",
        "go",
        "goes",
        "going",
        "went",
        "come",
        "came",
        "look",
        "looks",
        "looking",
        "say",
        "says",
        "said",
        "tell",
        "tells",
        "told",
        "ask",
        "asks",
        "asked",
        "what",
        "where",
        "when",
        "who",
        "why",
        "how",
        "if",
        "then",
        "than",
        "as",
        "so",
        "not",
        "no",
        "yes",
    }
)


def _disposition_label(value: float) -> str:
    """Map a [-1, +1] disposition value to the existing 5-tier label.

    Bridges to ``Disposition.from_trust`` (which expects a 0..100 trust
    score) so the labels stay in lockstep with the ``relationships``
    module instead of drifting via a parallel threshold ladder.
    """
    trust = int(round((max(-1.0, min(1.0, value)) + 1.0) * 50.0))
    return Disposition.from_trust(trust).value.lower()


def _estimate_tokens(text: str) -> int:
    """``len // 4`` heuristic. Good enough for budgeting prose."""
    return max(1, len(text) // 4)


class MemoryAssembler:
    """Builds the narrator's context block from WorldDB facts + LightRAG lore.

    Construct one per session and call :meth:`assemble` per turn. Reads
    from ``WorldDB`` on demand so the previous turn's shadow-writes are
    immediately visible — no per-turn cache invalidation needed.
    """

    def __init__(
        self,
        world_db: WorldDB,
        world_rag: Optional[Any] = None,
        profile: ProfileName = "balanced",
    ) -> None:
        self.world_db = world_db
        self.world_rag = world_rag
        self.profile = PROFILES.get(profile, PROFILES["balanced"])
        # One-slot (turn_number, hash(player_input), location) → assembled
        # block. Turn advance invalidates automatically; repeated `look` /
        # `wait` inputs hit the cache and skip the full rebuild.
        self._cache: tuple[tuple, str] | None = None

    def _extract_entity_references(self, player_input: str) -> list[str]:
        """Step 1: name-match player input tokens against the registry.

        Strips stopwords + sub-2-char tokens, then issues a single
        ``WorldDB.search_entities_any`` OR-match and dedupes by canonical
        name so the same entity doesn't appear twice when multiple tokens
        point at it.
        """
        tokens: list[str] = []
        for token in _WORD_RE.findall(player_input or ""):
            if token.lower() in _STOPWORDS:
                continue
            if len(token) < 2:
                continue
            tokens.append(token)
        if not tokens:
            return []
        try:
            hits = self.world_db.search_entities_any(tokens, limit_per_token=3)
        except Exception:
            from .._debug import log_swallowed_exc

            log_swallowed_exc("memory_assembler.search_entities_any")
            return []
        seen: set[str] = set()
        out: list[str] = []
        for hit in hits:
            if not hit:
                continue
            canon = hit.get("canonical_name") or canonical_name(hit.get("name", ""))
            if canon in seen:
                continue
            seen.add(canon)
            out.append(hit.get("name") or canon)
        return out

    def _pull_entity_snapshots(self, refs: Iterable[str], location: str) -> list[dict]:
        """Step 2: snapshot referenced entities + everyone at ``location``.

        Delegates to ``WorldDB.get_entity_snapshot_batch`` which folds
        entity lookup + disposition + last event into a single SQL query.
        """
        try:
            return self.world_db.get_entity_snapshot_batch(list(refs), location)
        except Exception:
            from .._debug import log_swallowed_exc

            log_swallowed_exc("memory_assembler.get_entity_snapshot_batch")
            return []

    def _pull_recent_events(self) -> list[dict]:
        """Step 3: continuity tail. Always included, never dropped."""
        try:
            return self.world_db.get_recent_events(self.profile.recent_event_count)
        except Exception:
            from .._debug import log_swallowed_exc

            log_swallowed_exc("memory_assembler.get_recent_events")
            return []

    def _pull_relevant_history(
        self,
        refs: Iterable[str],
        location: str,
        already_seen_ids: set[int],
    ) -> list[dict]:
        """Step 4: events touching the referenced entities or current location."""
        budget = self.profile.historical_event_tokens
        out: list[dict] = []
        used = 0
        seen_ids: set[int] = set(already_seen_ids)

        def _consume(events: Iterable[dict]) -> bool:
            nonlocal used
            for ev in events:
                if not ev:
                    continue
                ev_id = ev.get("id")
                if ev_id in seen_ids:
                    continue
                summary = ev.get("summary") or ""
                cost = _estimate_tokens(summary)
                if used + cost > budget:
                    return True
                seen_ids.add(ev_id)
                out.append(ev)
                used += cost
            return False

        for name in refs:
            if used >= budget:
                return out
            try:
                events = self.world_db.get_events_for_entity(name, limit=20)
            except Exception:
                events = []
            if _consume(events):
                return out

        if used >= budget:
            return out
        if location:
            try:
                events = self.world_db.get_events_at_location(location, limit=20)
            except Exception:
                events = []
            _consume(events)

        return out

    # Step 5 — narrative echoes (FTS5 / vector search) — deferred to rag-quest-50j

    def _pull_lore(self, player_input: str, location: str, refs: list[str]) -> str:
        """Step 6: single LightRAG lore query. Only LightRAG call site."""
        if self.world_rag is None:
            return ""
        question_parts = [player_input.strip()]
        if location:
            question_parts.append(f"at {location}")
        if refs:
            question_parts.append("involving " + ", ".join(refs))
        question = " ".join(p for p in question_parts if p)
        try:
            result = self.world_rag.query_world(question)
        except Exception:
            from .._debug import log_swallowed_exc

            log_swallowed_exc("memory_assembler.lore")
            return ""
        if not result:
            return ""
        text = str(result)
        max_chars = self.profile.lore_tokens * 4
        return text[:max_chars]

    # ------------------------------------------------------------------
    # Step 7 — assemble + format
    # ------------------------------------------------------------------

    def assemble(self, player_input: str, game_state: Any) -> str:
        """Return the structured §4.3 context block for the narrator.

        Always includes CURRENT STATE, RECENT EVENTS, and PLAYER ACTION.
        ENTITIES PRESENT, RELEVANT HISTORY, and WORLD LORE sections are
        elided when their data sources are empty.
        """
        character = getattr(game_state, "character", None)
        location = getattr(character, "location", "") or ""

        turn_number = getattr(game_state, "turn_number", None)
        cache_key = (turn_number, player_input or "", location)
        if self._cache is not None and self._cache[0] == cache_key:
            return self._cache[1]

        refs = self._extract_entity_references(player_input)
        snapshots = self._pull_entity_snapshots(refs, location)
        recent = self._pull_recent_events()
        recent_ids = {ev["id"] for ev in recent if ev and ev.get("id") is not None}
        history = self._pull_relevant_history(refs, location, recent_ids)
        lore = self._pull_lore(player_input, location, refs)

        # Referenced entities sit at the head of `snapshots` (Step 2
        # appends location entities after refs), so truncating the tail
        # matches the §4.1 "never drop referenced entities" policy.
        snap_lines = [self._format_snapshot(s) for s in snapshots]
        snap_budget = self.profile.entity_snapshot_tokens
        snap_used = 0
        kept_snaps: list[str] = []
        for line in snap_lines:
            cost = _estimate_tokens(line)
            if snap_used + cost > snap_budget and kept_snaps:
                break
            kept_snaps.append(line)
            snap_used += cost

        sections: list[str] = []
        sections.append(self._format_current_state(character))

        if kept_snaps:
            sections.append("## ENTITIES PRESENT\n" + "\n".join(kept_snaps))

        if recent:
            sections.append(
                "## RECENT EVENTS\n" + "\n".join(self._format_event(e) for e in recent)
            )

        if history:
            sections.append(
                "## RELEVANT HISTORY\n"
                + "\n".join(self._format_event(e) for e in history)
            )

        if lore:
            sections.append("## WORLD LORE\n" + lore)

        sections.append(f'## PLAYER ACTION\n"{player_input}"')

        block = "\n\n".join(sections)
        self._cache = (cache_key, block)
        return block

    def _format_current_state(self, character: Any) -> str:
        location = getattr(character, "location", None) or "Unknown"
        name = getattr(character, "name", None) or "Adventurer"
        hp = getattr(character, "current_hp", None)
        max_hp = getattr(character, "max_hp", None)
        hp_line = f"{hp}/{max_hp} HP" if hp is not None and max_hp is not None else ""
        lines = ["## CURRENT STATE", f"Location: {location}", f"Character: {name}"]
        if hp_line:
            lines.append(f"HP: {hp_line}")
        return "\n".join(lines)

    def _format_snapshot(self, snap: dict) -> str:
        entity = snap.get("entity") or {}
        name = entity.get("name") or "?"
        ent_type = entity.get("entity_type") or ""
        disposition = snap.get("disposition")
        if ent_type and disposition is not None:
            line = (
                f"- {name} ({ent_type}, disposition: "
                f"{_disposition_label(disposition)} {disposition:+.1f})"
            )
        elif ent_type:
            line = f"- {name} ({ent_type})"
        else:
            line = f"- {name}"
        last_event = snap.get("last_event")
        if last_event and last_event.get("summary"):
            line += (
                f"\n  Last interaction: turn {last_event.get('turn_number', '?')} — "
                f"{last_event.get('summary')}"
            )
        return line

    def _format_event(self, event: dict) -> str:
        turn = event.get("turn_number", "?")
        summary = event.get("summary") or ""
        return f"- T{turn}: {summary}"


def maybe_attach_to_narrator(narrator: Any, game_state: Any, config: dict) -> None:
    """Wire a ``MemoryAssembler`` onto ``narrator`` when the flag is set.

    Idempotent. Bails out cleanly when ``game_state.world_db`` is
    missing (legacy save, init failed) so the three construction sites
    in CLI / web onboarding / web sessions can all call this after
    WorldDB opens without branching.
    """
    world_db = getattr(game_state, "world_db", None)
    if world_db is None:
        return
    memory_cfg = (config or {}).get("memory") or {}
    if not memory_cfg.get("assembler_enabled", False):
        return
    profile = str(memory_cfg.get("profile", "balanced"))
    world_rag = getattr(game_state, "world_rag", None) or getattr(
        narrator, "world_rag", None
    )
    narrator.memory_assembler = MemoryAssembler(world_db, world_rag, profile=profile)
