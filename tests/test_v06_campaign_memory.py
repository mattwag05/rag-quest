"""Tests for v0.6 Campaign Memory: timeline, notetaker, encyclopedia."""

import json
from pathlib import Path

import pytest

from rag_quest.engine.encyclopedia import CATEGORIES, LoreEncyclopedia
from rag_quest.engine.notetaker import NoteEntry, Notetaker, _parse_notetaker_response
from rag_quest.engine.state_parser import StateChange
from rag_quest.engine.timeline import (
    DEFAULT_MAX_EVENTS,
    Bookmark,
    Timeline,
    TimelineEvent,
)

# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------


def test_timeline_records_location_and_item_from_state_change():
    tl = Timeline()
    change = StateChange()
    change.location = "Silver Hollow"
    change.items_gained = ["healing potion"]
    change.npc_met = "Captain Mira"
    change.quest_offered = "Find the lost courier"

    events = tl.record_from_state_change(
        turn=3, change=change, player_input="enter town"
    )
    types = [e.type for e in events]
    assert "location" in types
    assert "item" in types
    assert "npc" in types
    assert "quest" in types
    assert any("Silver Hollow" in e.summary for e in events)


def test_timeline_fallback_when_no_structured_change():
    tl = Timeline()
    change = StateChange()
    events = tl.record_from_state_change(
        turn=1, change=change, player_input="look around"
    )
    assert len(events) == 1
    assert events[0].type == "world_event"
    assert "look around" in events[0].summary


def test_timeline_filter_by_type():
    tl = Timeline()
    change = StateChange()
    change.location = "Forge"
    change.items_gained = ["anvil key"]
    tl.record_from_state_change(turn=1, change=change, player_input="enter forge")
    events = tl.get_events(filter_type="item")
    assert all(e.type == "item" for e in events)


def test_timeline_size_rotation():
    tl = Timeline(max_events=5)
    change = StateChange()
    change.items_gained = ["coin"]
    for i in range(1, 12):
        tl.record_from_state_change(turn=i, change=change, player_input="loot")
    assert len(tl.events) == 5
    # Oldest should have rotated out — earliest remaining should be turn 7+
    assert tl.events[0].turn >= 7


def test_timeline_bookmarks_never_rotate():
    tl = Timeline(max_events=2)
    tl.add_bookmark(
        Bookmark(
            turn=1, timestamp="t", note="n", player_input="p", narrator_prose="prose"
        )
    )
    change = StateChange()
    change.items_gained = ["spam"]
    for i in range(1, 20):
        tl.record_from_state_change(turn=i, change=change, player_input="a")
    assert len(tl.bookmarks) == 1


def test_timeline_round_trip_serialization():
    tl = Timeline()
    change = StateChange()
    change.location = "Atelier"
    tl.record_from_state_change(turn=1, change=change, player_input="arrive")
    tl.add_bookmark(
        Bookmark(
            turn=1,
            timestamp="t",
            note="first",
            player_input="arrive",
            narrator_prose="A hush falls.",
        )
    )
    data = tl.to_dict()
    # JSON safety
    json.dumps(data)
    tl2 = Timeline.from_dict(data)
    assert len(tl2.events) == len(tl.events)
    assert tl2.bookmarks[0].note == "first"


def test_timeline_from_empty_dict():
    tl = Timeline.from_dict(None)
    assert tl.max_events == DEFAULT_MAX_EVENTS
    assert tl.events == []


# ---------------------------------------------------------------------------
# Notetaker
# ---------------------------------------------------------------------------


class _StubLLM:
    def __init__(self, response: str):
        self._response = response

    def complete(self, messages, **kwargs):
        return self._response


def test_notetaker_parses_clean_json():
    payload = (
        '{"session_summary": "Heroes crossed the moors.", '
        '"npc_notes": ["Old Gus — cagey"], '
        '"open_hooks": ["The signal fire still burns"], '
        '"faction_shifts": ["Reavers weakened"]}'
    )
    entry = _parse_notetaker_response(payload, "")
    assert "crossed" in entry.session_summary
    assert entry.npc_notes == ["Old Gus — cagey"]
    assert entry.faction_shifts == ["Reavers weakened"]


def test_notetaker_strips_code_fence():
    payload = '```json\n{"session_summary": "OK", "npc_notes": [], "open_hooks": [], "faction_shifts": []}\n```'
    entry = _parse_notetaker_response(payload, "")
    assert entry.session_summary == "OK"


def test_notetaker_refresh_cursor_advances(tmp_path):
    llm = _StubLLM(
        '{"session_summary": "stuff happened", "npc_notes": [], "open_hooks": [], "faction_shifts": []}'
    )
    nt = Notetaker(world_name="TestRealm", llm=llm, notes_dir=tmp_path)
    assert nt.last_summarized_turn == 0
    entry = nt.refresh(
        current_turn=5,
        conversation_history=[{"role": "user", "content": "hi"}],
        timeline_events=[],
    )
    assert entry is not None
    assert nt.last_summarized_turn == 5
    # Second call with same turn → None
    assert (
        nt.refresh(current_turn=5, conversation_history=[], timeline_events=[]) is None
    )


def test_notetaker_persists_across_instances(tmp_path):
    llm = _StubLLM(
        '{"session_summary": "persisted", "npc_notes": [], "open_hooks": [], "faction_shifts": []}'
    )
    nt = Notetaker(world_name="Persistent", llm=llm, notes_dir=tmp_path)
    nt.refresh(current_turn=3, conversation_history=[], timeline_events=[])
    # New instance reads from disk
    nt2 = Notetaker(world_name="Persistent", llm=llm, notes_dir=tmp_path)
    assert nt2.last_summarized_turn == 3
    assert nt2.entries[-1].session_summary == "persisted"


def test_notetaker_canonize_promotes_and_tags(tmp_path):
    llm = _StubLLM(
        '{"session_summary": "promote me", "npc_notes": [], "open_hooks": [], "faction_shifts": []}'
    )
    nt = Notetaker(world_name="Canon", llm=llm, notes_dir=tmp_path)
    nt.refresh(current_turn=2, conversation_history=[], timeline_events=[])

    ingested = []

    class FakeRAG:
        def ingest_text(self, text, source):
            ingested.append((source, text))

    assert len(nt.pending_for_canonization()) == 1
    ok = nt.canonize_entry(0, FakeRAG())
    assert ok
    assert len(nt.pending_for_canonization()) == 0
    assert ingested and ingested[0][0] == "canonized"
    assert "promote me" in ingested[0][1]


def test_notetaker_survives_corrupt_file(tmp_path):
    world_file = tmp_path / "Broken.json"
    world_file.write_text("not json at all")
    llm = _StubLLM(
        '{"session_summary": "ok", "npc_notes": [], "open_hooks": [], "faction_shifts": []}'
    )
    nt = Notetaker(world_name="Broken", llm=llm, notes_dir=tmp_path)
    assert nt.entries == []
    assert nt.last_summarized_turn == 0


# ---------------------------------------------------------------------------
# Encyclopedia
# ---------------------------------------------------------------------------


class _FakeWorld:
    def __init__(self):
        self.visited_locations = {"Silver Hollow", "Deepwater"}
        self.npcs_met = {"Mira"}
        self.recent_events = ["Moved to Silver Hollow", "Took 5 damage"]


class _FakeNPCRel:
    def __init__(self):
        self.disposition = type("D", (), {"value": "Friendly"})()
        self.trust = 70
        self.last_interaction_summary = "helped with quest"


class _FakeRelMgr:
    def __init__(self):
        self.relationships = {"Mira": _FakeNPCRel()}
        self.factions = {}
        self.faction_reputation = {}


class _FakeItem:
    def __init__(self, rarity, description):
        self.rarity = rarity
        self.description = description


class _FakeInventory:
    def __init__(self):
        self.items = {"healing potion": _FakeItem("common", "Restores 10 HP.")}


class _FakeGameState:
    def __init__(self):
        self.world = _FakeWorld()
        self.relationships = _FakeRelMgr()
        self.inventory = _FakeInventory()
        self.world_rag = None


def test_encyclopedia_lists_all_categories():
    enc = LoreEncyclopedia(_FakeGameState())
    counts = dict(enc.categories_with_counts())
    assert counts["locations"] == 2
    assert counts["npcs"] == 1
    assert counts["items"] == 1
    assert counts["factions"] == 0


def test_encyclopedia_detail_falls_back_when_rag_absent():
    enc = LoreEncyclopedia(_FakeGameState())
    entries = enc.list_entries("npcs")
    detail = enc.detail(entries[0])
    # No RAG, so we fall back to summary
    assert "Friendly" in detail


def test_encyclopedia_detail_uses_rag_when_present():
    gs = _FakeGameState()

    class FakeRAG:
        def query_world(self, question):
            return f"Rich lore about {question}"

    gs.world_rag = FakeRAG()
    enc = LoreEncyclopedia(gs)
    loc_entry = enc.list_entries("locations")[0]
    result = enc.detail(loc_entry)
    assert "Rich lore" in result


def test_encyclopedia_categories_constant():
    assert set(CATEGORIES) == {"npcs", "locations", "factions", "items"}
