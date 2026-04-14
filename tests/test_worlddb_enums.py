"""Regression tests for rag-quest-csi: WorldDB entity/event type
vocabulary is defined once as ``EntityType`` / ``EventType`` StrEnums
and derives (a) the module-level validation sets, (b) the DDL CHECK
clauses, and (c) the ``state_event_mapping`` call sites. Drift between
any of those three is a runtime CHECK violation in production, so
these tests lock the contract down.
"""

from __future__ import annotations

import sqlite3

import pytest

from rag_quest.knowledge.world_db import (
    _ENTITY_TYPES,
    _EVENT_TYPES,
    EntityType,
    EventType,
    WorldDB,
    _sql_check_in_clause,
)


def test_enums_exist_and_have_expected_members() -> None:
    assert {e.value for e in EntityType} == {
        "npc",
        "location",
        "faction",
        "item",
        "quest",
        "base",
    }
    assert {e.value for e in EventType} == {
        "combat",
        "quest_offer",
        "quest_complete",
        "social",
        "discovery",
        "trade",
        "travel",
        "world_event",
        "item",
        "death",
        "level_up",
        "base_claim",
        "module_unlock",
        "module_complete",
        "bookmark",
    }


def test_validation_sets_derive_from_enums() -> None:
    """``_ENTITY_TYPES`` / ``_EVENT_TYPES`` must stay frozen projections."""
    assert _ENTITY_TYPES == frozenset(e.value for e in EntityType)
    assert _EVENT_TYPES == frozenset(e.value for e in EventType)


def test_sql_check_helper_quotes_values() -> None:
    clause = _sql_check_in_clause("event_type", ["combat", "social"])
    # Sorted order — keeps the DDL deterministic across runs
    assert clause == "event_type IN ('combat', 'social')"


def test_ddl_check_clauses_reject_bogus_types(tmp_path) -> None:
    """A CHECK violation should raise sqlite3.IntegrityError."""
    db = WorldDB(tmp_path / "ddl.db")
    try:
        # Bypass the Python-side validation and hit the DDL CHECK directly
        with pytest.raises(sqlite3.IntegrityError):
            db._conn.execute(
                "INSERT INTO entities "
                "(entity_type, name, canonical_name, created_at_turn) "
                "VALUES ('not_a_real_type', 'Bogus', 'bogus', 0)"
            )

        with pytest.raises(sqlite3.IntegrityError):
            db._conn.execute(
                "INSERT INTO events (turn_number, event_type, summary) "
                "VALUES (0, 'not_a_real_event', 'nope')"
            )
    finally:
        db.close()


def test_ddl_check_clauses_accept_every_enum_value(tmp_path) -> None:
    """Every declared enum member must round-trip through the DDL."""
    db = WorldDB(tmp_path / "accept.db")
    try:
        for i, entity_type in enumerate(EntityType):
            db._conn.execute(
                "INSERT INTO entities "
                "(entity_type, name, canonical_name, created_at_turn) "
                "VALUES (?, ?, ?, 0)",
                (entity_type.value, f"Thing{i}", f"thing{i}"),
            )
        for i, event_type in enumerate(EventType):
            db._conn.execute(
                "INSERT INTO events (turn_number, event_type, summary) "
                "VALUES (?, ?, ?)",
                (i, event_type.value, f"Event {i}"),
            )
        db._conn.commit()

        assert db._conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == len(
            list(EntityType)
        )
        assert db._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == len(
            list(EventType)
        )
    finally:
        db.close()


def test_state_event_mapping_emits_enum_compatible_strings() -> None:
    """``state_change_to_writes`` uses enum values that survive the CHECK."""
    from types import SimpleNamespace

    from rag_quest.engine.state_event_mapping import state_change_to_writes

    change = SimpleNamespace(
        location="Bree",
        damage_taken=5,
        hp_healed=0,
        items_gained=["Herb"],
        items_lost=[],
        quest_offered="Find the Ranger",
        quest_completed=None,
        npc_met="Butterbur",
        npc_recruited=None,
        npc_relationship_change={},
        world_event_triggered="Storm rolls in",
        claim_base=False,
    )
    writes = state_change_to_writes(change, player_input="look around", location="Bree")

    # Every emitted entity_type must be a member of EntityType
    for ent in writes.entities:
        assert ent.entity_type in _ENTITY_TYPES
    # Every emitted event_type must be a member of EventType
    for evt in writes.events:
        assert evt.event_type in _EVENT_TYPES
