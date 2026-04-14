"""Regression tests for rag-quest-678: per-turn relationship deltas must
fold into the absolute ``disposition`` value via read-modify-write, so
the WorldDB row for each NPC stays canonical.

Before the fix, ``state_change_to_writes`` emitted
``rel_type='disposition_delta'`` with the normalized delta, and the
shadow-write consumer dropped it into the DB as a separate row. The
v3 save migration wrote the absolute value as ``rel_type='disposition'``,
so a migrated save would end up with two rows per NPC that the Phase 2
MemoryAssembler would have to reconcile. Now the translator flags the
write as a delta, and the shadow-write consumer folds it into the
existing ``disposition`` row via read-modify-write.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from rag_quest.engine.state_event_mapping import (
    RelationshipWrite,
    state_change_to_writes,
)
from rag_quest.engine.turn import _shadow_write_to_world_db
from rag_quest.knowledge.world_db import WorldDB


def _make_change(**kwargs) -> SimpleNamespace:
    defaults = {
        "location": None,
        "damage_taken": 0,
        "hp_healed": 0,
        "items_gained": [],
        "items_lost": [],
        "quest_offered": None,
        "quest_completed": None,
        "npc_met": None,
        "npc_recruited": None,
        "npc_relationship_change": {},
        "world_event_triggered": None,
        "claim_base": False,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_state_event_mapping_emits_disposition_delta_flag(tmp_path) -> None:
    """state_change_to_writes flags relationship changes as deltas.

    It stays a pure function — the read-modify-write happens at the DB
    boundary.
    """
    change = _make_change(npc_relationship_change={"Aragorn": 25})
    writes = state_change_to_writes(
        change, player_input="help aragorn", location="Bree"
    )

    assert len(writes.relationships) == 1
    rel = writes.relationships[0]
    assert isinstance(rel, RelationshipWrite)
    assert rel.entity_a == "player"
    assert rel.entity_b == "Aragorn"
    assert rel.rel_type == "disposition"  # canonical, no longer _delta
    assert rel.is_delta is True
    assert rel.value == pytest.approx(0.5)  # 25 / 50


def test_shadow_write_folds_delta_into_missing_row(tmp_path) -> None:
    """When no existing disposition row exists, the delta becomes the absolute."""
    db = WorldDB(tmp_path / "fold_missing.db")
    try:
        change = _make_change(npc_relationship_change={"Boromir": 20})
        _shadow_write_to_world_db(
            world_db=db,
            change=change,
            turn=1,
            player_input="defend boromir",
            location="Minas Tirith",
        )

        rows = db._conn.execute(
            "SELECT relationship_type, value FROM relationships"
        ).fetchall()
        assert len(rows) == 1
        row = rows[0]
        assert row["relationship_type"] == "disposition"
        assert row["value"] == pytest.approx(0.4)  # 20/50 from 0.0 baseline
    finally:
        db.close()


def test_shadow_write_folds_delta_into_existing_row(tmp_path) -> None:
    """A second delta on the same NPC accumulates on top of the first."""
    db = WorldDB(tmp_path / "fold_existing.db")
    try:
        # First turn: +0.4 (20/50) from 0.0 → 0.4
        _shadow_write_to_world_db(
            world_db=db,
            change=_make_change(npc_relationship_change={"Legolas": 20}),
            turn=1,
            player_input="compliment legolas",
            location="Lothlorien",
        )
        # Second turn: +0.2 (10/50) from 0.4 → 0.6
        _shadow_write_to_world_db(
            world_db=db,
            change=_make_change(npc_relationship_change={"Legolas": 10}),
            turn=2,
            player_input="share food",
            location="Lothlorien",
        )

        rows = db._conn.execute(
            "SELECT relationship_type, value FROM relationships"
        ).fetchall()
        # Still exactly one row — never a disposition_delta
        assert len(rows) == 1
        assert rows[0]["relationship_type"] == "disposition"
        assert rows[0]["value"] == pytest.approx(0.6)

        # No rows with the old delta rel_type ever land in the DB
        delta_rows = db._conn.execute(
            "SELECT 1 FROM relationships WHERE relationship_type = 'disposition_delta'"
        ).fetchall()
        assert delta_rows == []
    finally:
        db.close()


def test_shadow_write_clamps_fold_at_positive_one(tmp_path) -> None:
    db = WorldDB(tmp_path / "clamp_pos.db")
    try:
        # Three turns of +0.8 each (40/50) — would reach 2.4 without clamping
        for turn, pts in enumerate((40, 40, 40), start=1):
            _shadow_write_to_world_db(
                world_db=db,
                change=_make_change(npc_relationship_change={"Gandalf": pts}),
                turn=turn,
                player_input="heroic deed",
                location="Rivendell",
            )
        row = db._conn.execute(
            "SELECT value FROM relationships WHERE relationship_type = 'disposition'"
        ).fetchone()
        assert row is not None
        assert row["value"] == pytest.approx(1.0)
    finally:
        db.close()


def test_shadow_write_clamps_fold_at_negative_one(tmp_path) -> None:
    db = WorldDB(tmp_path / "clamp_neg.db")
    try:
        for turn, pts in enumerate((-40, -40, -40), start=1):
            _shadow_write_to_world_db(
                world_db=db,
                change=_make_change(npc_relationship_change={"Saruman": pts}),
                turn=turn,
                player_input="betrayal",
                location="Isengard",
            )
        row = db._conn.execute(
            "SELECT value FROM relationships WHERE relationship_type = 'disposition'"
        ).fetchone()
        assert row is not None
        assert row["value"] == pytest.approx(-1.0)
    finally:
        db.close()


def test_non_delta_relationship_write_preserves_absolute_value(tmp_path) -> None:
    """Non-delta writes (e.g. the v3 migration) still behave as setters."""
    db = WorldDB(tmp_path / "abs.db")
    try:
        writes_from_migration = RelationshipWrite(
            entity_a="player",
            entity_b="Frodo",
            rel_type="disposition",
            value=0.75,
            is_delta=False,
        )
        db._ensure_entity("player", "npc", 0)
        db._ensure_entity("Frodo", "npc", 0)
        db.set_relationship(
            writes_from_migration.entity_a,
            writes_from_migration.entity_b,
            writes_from_migration.rel_type,
            writes_from_migration.value,
            0,
        )
        row = db._conn.execute(
            "SELECT value FROM relationships WHERE relationship_type = 'disposition'"
        ).fetchone()
        assert row["value"] == pytest.approx(0.75)
    finally:
        db.close()
