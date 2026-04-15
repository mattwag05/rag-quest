"""Tests for ``WorldDB.get_entity_snapshot_batch`` (rag-quest-696).

The batch helper collapses the three queries per entity that
``MemoryAssembler._pull_entity_snapshots`` issues today
(``get_entity`` + ``get_relationship`` + ``get_events_for_entity``) into
a single round-trip. These tests pin the return shape to the one the
assembler consumes and exercise the edge cases the original fan-out
handled implicitly: unknown entities, no disposition, location-only
mode, and location-entities that overlap with the referenced set.
"""

from __future__ import annotations

import pytest

from rag_quest.knowledge.world_db import EntityType, EventType, WorldDB


@pytest.fixture
def world_db(tmp_path):
    db = WorldDB(tmp_path / "world.db")
    yield db
    db.close()


def test_batch_returns_empty_for_empty_refs_and_no_location(world_db):
    result = world_db.get_entity_snapshot_batch([])

    assert result == []


def test_batch_returns_referenced_entity_with_disposition_and_last_event(world_db):
    world_db.upsert_entity(EntityType.NPC.value, "Gareth", turn=1, location="Millhaven")
    world_db.set_relationship(
        "player", "Gareth", "disposition", -0.5, turn=2, cause="argued"
    )
    world_db.record_event(
        turn=3,
        event_type=EventType.SOCIAL.value,
        summary="Gareth scowled at the player",
        primary_entity="Gareth",
        location="Millhaven",
    )

    result = world_db.get_entity_snapshot_batch(["Gareth"])

    assert len(result) == 1
    snap = result[0]
    assert snap["entity"]["name"] == "Gareth"
    assert snap["entity"]["entity_type"] == "npc"
    assert snap["disposition"] == pytest.approx(-0.5)
    assert snap["last_event"] is not None
    assert snap["last_event"]["summary"] == "Gareth scowled at the player"


def test_batch_handles_entity_with_no_relationship(world_db):
    world_db.upsert_entity(EntityType.NPC.value, "Bran", turn=1)

    result = world_db.get_entity_snapshot_batch(["Bran"])

    assert len(result) == 1
    assert result[0]["entity"]["name"] == "Bran"
    assert result[0]["disposition"] is None
    assert result[0]["last_event"] is None


def test_batch_silently_skips_unknown_entity(world_db):
    world_db.upsert_entity(EntityType.NPC.value, "Gareth", turn=1)

    result = world_db.get_entity_snapshot_batch(["Gareth", "Nonexistent"])

    names = [snap["entity"]["name"] for snap in result]
    assert "Gareth" in names
    assert "Nonexistent" not in names


def test_batch_location_only_mode_returns_entities_present(world_db):
    world_db.upsert_entity(EntityType.NPC.value, "Gareth", turn=1, location="Millhaven")
    world_db.upsert_entity(EntityType.NPC.value, "Elena", turn=1, location="Millhaven")
    world_db.upsert_entity(EntityType.NPC.value, "Rurik", turn=1, location="Ashford")

    result = world_db.get_entity_snapshot_batch([], location="Millhaven")

    names = {snap["entity"]["name"] for snap in result}
    assert names == {"Gareth", "Elena"}


def test_batch_dedupes_ref_that_is_also_at_location(world_db):
    world_db.upsert_entity(EntityType.NPC.value, "Gareth", turn=1, location="Millhaven")

    result = world_db.get_entity_snapshot_batch(["Gareth"], location="Millhaven")

    names = [snap["entity"]["name"] for snap in result]
    assert names.count("Gareth") == 1


def test_batch_orders_referenced_entities_before_location_entities(world_db):
    world_db.upsert_entity(EntityType.NPC.value, "Gareth", turn=1, location="Millhaven")
    world_db.upsert_entity(EntityType.NPC.value, "Elena", turn=1, location="Millhaven")
    world_db.upsert_entity(EntityType.NPC.value, "Rurik", turn=1, location="Millhaven")

    result = world_db.get_entity_snapshot_batch(["Rurik"], location="Millhaven")

    assert result[0]["entity"]["name"] == "Rurik"
    remaining = {snap["entity"]["name"] for snap in result[1:]}
    assert remaining == {"Gareth", "Elena"}


def test_search_any_returns_empty_for_empty_tokens(world_db):
    result = world_db.search_entities_any([])

    assert result == []


def test_search_any_unions_matches_across_tokens(world_db):
    world_db.upsert_entity(EntityType.NPC.value, "Gareth", turn=1)
    world_db.upsert_entity(EntityType.NPC.value, "Elena", turn=1)
    world_db.upsert_entity(EntityType.NPC.value, "Rurik", turn=1)

    result = world_db.search_entities_any(["Gareth", "Elena"])

    names = {ent["name"] for ent in result}
    assert "Gareth" in names
    assert "Elena" in names
    assert "Rurik" not in names


def test_search_any_dedupes_entity_matched_by_multiple_tokens(world_db):
    world_db.upsert_entity(EntityType.NPC.value, "Gareth", turn=1, summary="blacksmith")

    result = world_db.search_entities_any(["Gareth", "blacksmith"])

    hits = [ent for ent in result if ent["name"] == "Gareth"]
    assert len(hits) == 1


def test_search_any_sanitizes_fts_special_chars(world_db):
    world_db.upsert_entity(EntityType.NPC.value, "Gareth", turn=1)

    result = world_db.search_entities_any(['Gareth"; DROP TABLE entities --'])

    assert any(ent["name"] == "Gareth" for ent in result)


def test_search_any_issues_single_query_for_multi_token_input(world_db, monkeypatch):
    world_db.upsert_entity(EntityType.NPC.value, "Gareth", turn=1)
    world_db.upsert_entity(EntityType.NPC.value, "Elena", turn=1)

    call_count = {"n": 0}
    real_conn = world_db._conn

    class CountingConn:
        def __init__(self, inner):
            self._inner = inner

        def execute(self, sql, *args, **kwargs):
            call_count["n"] += 1
            return self._inner.execute(sql, *args, **kwargs)

        def __getattr__(self, name):
            return getattr(self._inner, name)

    monkeypatch.setattr(world_db, "_conn", CountingConn(real_conn))

    world_db.search_entities_any(["Gareth", "Elena", "Rurik", "Bran"])

    assert call_count["n"] == 1


def test_search_any_fts5_fallback_still_matches(world_db, monkeypatch):
    world_db.upsert_entity(EntityType.NPC.value, "Gareth", turn=1)
    world_db.upsert_entity(EntityType.NPC.value, "Elena", turn=1)

    monkeypatch.setattr(world_db, "_fts5_available", False)

    result = world_db.search_entities_any(["Gareth", "Elena"])

    names = {ent["name"] for ent in result}
    assert "Gareth" in names
    assert "Elena" in names


def test_batch_matches_three_query_fan_out_for_same_inputs(world_db):
    """Equivalence check: batch result mirrors what the assembler would build.

    This is the regression guard — if a future schema change breaks the
    batch helper's JOIN, the fan-out comparison catches it immediately.
    """
    world_db.upsert_entity(EntityType.NPC.value, "Gareth", turn=1, location="Millhaven")
    world_db.set_relationship("player", "Gareth", "disposition", 0.3, turn=2)
    world_db.record_event(
        turn=4,
        event_type=EventType.SOCIAL.value,
        summary="Gareth shared a drink",
        primary_entity="Gareth",
    )
    world_db.record_event(
        turn=5,
        event_type=EventType.SOCIAL.value,
        summary="Gareth laughed at a joke",
        primary_entity="Gareth",
    )

    batch = world_db.get_entity_snapshot_batch(["Gareth"])
    assert len(batch) == 1
    snap = batch[0]

    fan_entity = world_db.get_entity("Gareth")
    fan_rel = world_db.get_relationship("player", "Gareth", "disposition")
    fan_events = world_db.get_events_for_entity("Gareth", limit=1)

    assert snap["entity"]["id"] == fan_entity["id"]
    assert snap["entity"]["name"] == fan_entity["name"]
    assert snap["disposition"] == pytest.approx(float(fan_rel["value"]))
    assert snap["last_event"]["id"] == fan_events[0]["id"]
    assert snap["last_event"]["summary"] == fan_events[0]["summary"]
