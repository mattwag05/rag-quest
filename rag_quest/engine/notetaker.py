"""AI Notetaker — incremental session summarizer with JSON sidecar storage.

Stores structured notes at ``~/.local/share/rag-quest/notes/{world}.json``.
Uses a ``last_summarized_turn`` cursor so long campaigns only summarize new
material. ``/canonize`` promotes player-approved notes into LightRAG.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..prompts.notetaker import NOTETAKER_SYSTEM

NOTES_ROOT = Path.home() / ".local" / "share" / "rag-quest" / "notes"


@dataclass
class NoteEntry:
    """A single incremental summary entry."""

    turn_range: str  # e.g. "12-18"
    session_summary: str
    npc_notes: List[str] = field(default_factory=list)
    open_hooks: List[str] = field(default_factory=list)
    faction_shifts: List[str] = field(default_factory=list)
    created_at: str = ""
    canonized: bool = False

    def to_dict(self) -> dict:
        return {
            "turn_range": self.turn_range,
            "session_summary": self.session_summary,
            "npc_notes": list(self.npc_notes),
            "open_hooks": list(self.open_hooks),
            "faction_shifts": list(self.faction_shifts),
            "created_at": self.created_at,
            "canonized": self.canonized,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NoteEntry":
        return cls(
            turn_range=str(data.get("turn_range", "")),
            session_summary=str(data.get("session_summary", "")),
            npc_notes=list(data.get("npc_notes", [])),
            open_hooks=list(data.get("open_hooks", [])),
            faction_shifts=list(data.get("faction_shifts", [])),
            created_at=str(data.get("created_at", "")),
            canonized=bool(data.get("canonized", False)),
        )


class Notetaker:
    """Incremental campaign note manager.

    Invariants:
    - Canonical JSON sidecar is the source of truth. LightRAG is untouched
      until the player explicitly runs ``/canonize``.
    - ``last_summarized_turn`` tracks the most-recent turn already summarized.
    """

    def __init__(self, world_name: str, llm, notes_dir: Optional[Path] = None):
        self.world_name = world_name
        self.llm = llm
        self.notes_dir = Path(notes_dir) if notes_dir else NOTES_ROOT
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.notes_path = self.notes_dir / f"{_slug(world_name)}.json"

        self.entries: List[NoteEntry] = []
        self.last_summarized_turn: int = 0

        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self.notes_path.exists():
            return
        try:
            data = json.loads(self.notes_path.read_text())
            self.last_summarized_turn = int(data.get("last_summarized_turn", 0))
            self.entries = [NoteEntry.from_dict(e) for e in data.get("entries", [])]
        except Exception:
            # Zero-traceback: corrupt notes file → start empty, leave file alone.
            self.entries = []
            self.last_summarized_turn = 0

    def _save(self) -> None:
        payload = {
            "world_name": self.world_name,
            "last_summarized_turn": self.last_summarized_turn,
            "entries": [e.to_dict() for e in self.entries],
        }
        try:
            self.notes_path.write_text(json.dumps(payload, indent=2))
        except OSError:
            pass  # Best-effort; don't crash the game loop on a disk error.

    # ------------------------------------------------------------------
    # Summarization
    # ------------------------------------------------------------------

    # Minimum new turns required before an auto-refresh fires. Manual
    # `/notes refresh` bypasses this by calling `refresh()` directly.
    AUTO_REFRESH_MIN_TURNS = 10

    def needs_refresh(self, current_turn: int) -> bool:
        """Cheap check used by the auto-save hook to decide whether to run an LLM call.

        Because `refresh()` blocks on the same provider the narrator uses (20-30s on
        local Ollama), we gate auto-refreshes behind a turn threshold so the 5-turn
        auto-save cadence doesn't produce a summary call every single save.
        """
        return current_turn - self.last_summarized_turn >= self.AUTO_REFRESH_MIN_TURNS

    def refresh(
        self,
        current_turn: int,
        conversation_history: List[dict],
        timeline_events: List,
        max_history_turns: int = 10,
    ) -> Optional[NoteEntry]:
        """Run an incremental summary for everything since ``last_summarized_turn``.

        Returns the new NoteEntry, or None if there was nothing new to summarize.
        """
        if current_turn <= self.last_summarized_turn:
            return None

        # Slice recent conversation (2 messages per exchange).
        recent = (
            conversation_history[-(max_history_turns * 2) :]
            if conversation_history
            else []
        )
        convo_text = "\n".join(
            f"{m.get('role', 'user').upper()}: {m.get('content', '')[:300]}"
            for m in recent
        )

        # Structured events since last cursor.
        new_events = [
            e
            for e in timeline_events
            if getattr(e, "turn", 0) > self.last_summarized_turn
        ]
        events_text = (
            "\n".join(f"- T{e.turn} [{e.type}] {e.summary}" for e in new_events[-60:])
            or "(no structured events)"
        )

        prompt = (
            f"Turns since last summary: {self.last_summarized_turn + 1}..{current_turn}\n\n"
            f"STRUCTURED EVENTS:\n{events_text}\n\n"
            f"RECENT DIALOGUE:\n{convo_text}\n\n"
            "Produce a JSON object with keys: session_summary, npc_notes (array), "
            "open_hooks (array), faction_shifts (array). Plain prose inside strings."
        )

        summary_text = ""
        try:
            summary_text = (
                self.llm.complete(
                    [
                        {"role": "system", "content": NOTETAKER_SYSTEM},
                        {"role": "user", "content": prompt},
                    ]
                )
                or ""
            )
        except Exception:
            summary_text = ""

        entry = _parse_notetaker_response(summary_text, events_text)
        entry.turn_range = f"{self.last_summarized_turn + 1}-{current_turn}"
        entry.created_at = datetime.now().isoformat(timespec="seconds")

        self.entries.append(entry)
        self.last_summarized_turn = current_turn
        self._save()
        return entry

    # ------------------------------------------------------------------
    # Canonization
    # ------------------------------------------------------------------

    def pending_for_canonization(self) -> List[NoteEntry]:
        return [e for e in self.entries if not e.canonized]

    def canonize_entry(self, index: int, world_rag) -> bool:
        """Promote a single entry into LightRAG. Returns True on success."""
        pending = self.pending_for_canonization()
        if not (0 <= index < len(pending)):
            return False
        entry = pending[index]

        text_chunks = [
            f"SESSION SUMMARY (turns {entry.turn_range}): {entry.session_summary}"
        ]
        for note in entry.npc_notes:
            text_chunks.append(f"NPC NOTE: {note}")
        for hook in entry.open_hooks:
            text_chunks.append(f"OPEN HOOK: {hook}")
        for shift in entry.faction_shifts:
            text_chunks.append(f"FACTION SHIFT: {shift}")

        body = "\n".join(text_chunks)
        try:
            world_rag.ingest_text(body, source="canonized")
        except Exception:
            return False

        entry.canonized = True
        self._save()
        return True

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def format_latest(self, count: int = 3) -> str:
        if not self.entries:
            return "No campaign notes yet. Play a few turns and save to refresh."
        latest = self.entries[-count:]
        lines = []
        for entry in latest:
            tag = "[canonized]" if entry.canonized else "[local]"
            lines.append(f"Turns {entry.turn_range} {tag}")
            if entry.session_summary:
                lines.append(f"  {entry.session_summary}")
            if entry.npc_notes:
                lines.append(f"  NPCs: {'; '.join(entry.npc_notes[:3])}")
            if entry.open_hooks:
                lines.append(f"  Hooks: {'; '.join(entry.open_hooks[:3])}")
            if entry.faction_shifts:
                lines.append(f"  Factions: {'; '.join(entry.faction_shifts[:3])}")
            lines.append("")
        return "\n".join(lines).rstrip()


def _slug(name: str) -> str:
    return (
        "".join(c if c.isalnum() or c in "-_" else "_" for c in name).strip("_")
        or "world"
    )


def _parse_notetaker_response(text: str, fallback_events: str) -> NoteEntry:
    """Best-effort parse of notetaker LLM output into a NoteEntry.

    The LLM may return JSON, JSON-in-code-fence, or prose. We try JSON first and
    fall back to treating the whole blob as session_summary.
    """
    import re

    if not text:
        return NoteEntry(turn_range="", session_summary=fallback_events)

    # Strip code fences if present.
    stripped = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1)

    try:
        # Find the first {...} block if the model wrapped prose around it.
        brace = stripped.find("{")
        if brace >= 0:
            parsed = json.loads(stripped[brace:])
            return NoteEntry(
                turn_range="",
                session_summary=str(parsed.get("session_summary", "")).strip(),
                npc_notes=_list_of_strings(parsed.get("npc_notes", [])),
                open_hooks=_list_of_strings(parsed.get("open_hooks", [])),
                faction_shifts=_list_of_strings(parsed.get("faction_shifts", [])),
            )
    except (json.JSONDecodeError, ValueError):
        pass

    return NoteEntry(turn_range="", session_summary=stripped[:1500])


def _list_of_strings(value) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
