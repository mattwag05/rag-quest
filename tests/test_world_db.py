"""Unit tests for rag_quest.knowledge.world_db.WorldDB.

Phase 1 of the v0.9 memory architecture redesign. Covers schema creation,
entity upserts with canonical-name dedup, relationship history, event
logging, FTS5 search, migration from an in-memory GameState, and foreign
key enforcement. No network / no LLM / no LightRAG.
"""

from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest

from rag_quest.knowledge.world_db import WorldDB, canonical_name

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(tmp_path) -> WorldDB:
    db = WorldDB(tmp_path / "test.db")
    yield db
    db.close()


# ---------------------------------------------------------------------------
# Schema & lifecycle
# ---------------------------------------------------------------------------


def test_schema_creation_is_idempotent(tmp_path):
    path = tmp_path / "idempotent.db"
    db1 = WorldDB(path)
    db1.upsert_entity("npc", "Gareth", turn=1)
    db1.close()

    db2 = WorldDB(path)  # reopen — must not error, rows preserved
    assert db2.get_entity("Gareth") is not None
    db2.close()


def test_metadata_round_trip(db):
    assert db.get_metadata("migrated_from_v3_save") is None
    db.set_metadata("migrated_from_v3_save", "1")
    assert db.get_metadata("migrated_from_v3_save") == "1"
    db.set_metadata("migrated_from_v3_save", "2")
    assert db.get_metadata("migrated_from_v3_save") == "2"


# ---------------------------------------------------------------------------
# Canonical name normalization
# ---------------------------------------------------------------------------


def test_canonical_name_strips_articles_and_collapses_ws():
    assert canonical_name("Gareth") == "gareth"
    assert canonical_name("The Blacksmith") == "blacksmith"
    assert canonical_name("  a  Dusty   Tome ") == "dusty tome"
    assert canonical_name("") == ""
    assert canonical_name("An Elven Bow") == "elven bow"


# ---------------------------------------------------------------------------
# Entity CRUD
# ---------------------------------------------------------------------------


def test_upsert_entity_inserts_then_updates(db):
    id1 = db.upsert_entity(
        "npc",
        "Gareth",
        turn=5,
        location="Millhaven",
        summary="A grumpy blacksmith",
    )
    id2 = db.upsert_entity(
        "npc",
        "Gareth",
        turn=10,
        summary="A grumpy blacksmith who owes the player a favor",
    )
    assert id1 == id2

    row = db.get_entity("Gareth")
    assert row is not None
    assert row["current_location"] == "Millhaven"  # preserved — wasn't overridden
    assert row["last_seen_turn"] == 10
    assert "owes the player" in row["summary"]


def test_upsert_entity_rejects_bad_type(db):
    with pytest.raises(ValueError):
        db.upsert_entity("spaceship", "The Normandy", turn=1)


def test_upsert_entity_rejects_empty_name(db):
    with pytest.raises(ValueError):
        db.upsert_entity("npc", "", turn=1)
    with pytest.raises(ValueError):
        db.upsert_entity("npc", "   ", turn=1)


def test_get_entity_with_article_variant(db):
    db.upsert_entity("npc", "The Blacksmith Gareth", turn=1, summary="Runs the forge")
    assert db.get_entity("Blacksmith Gareth") is not None
    assert db.get_entity("blacksmith gareth") is not None
    assert db.get_entity("the blacksmith gareth") is not None


def test_get_entities_at_filters_by_type(db):
    db.upsert_entity("npc", "Mira", turn=1, location="Tavern")
    db.upsert_entity("npc", "Gareth", turn=1, location="Tavern")
    db.upsert_entity("item", "Tankard", turn=1, location="Tavern")

    npcs = db.get_entities_at("Tavern", entity_type="npc")
    assert {r["name"] for r in npcs} == {"Mira", "Gareth"}

    all_at = db.get_entities_at("Tavern")
    assert len(all_at) == 3


def test_metadata_json_round_trip(db):
    db.upsert_entity(
        "item",
        "Sword of Flames",
        turn=1,
        metadata={"rarity": "legendary", "damage": 15, "element": "fire"},
    )
    row = db.get_entity("Sword of Flames")
    assert row is not None
    assert row["metadata"] == {
        "rarity": "legendary",
        "damage": 15,
        "element": "fire",
    }


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


def test_set_relationship_creates_then_updates_with_history(db):
    db.set_relationship("player", "Gareth", "disposition", 0.5, turn=5)
    rel = db.get_relationship("player", "Gareth", "disposition")
    assert rel is not None
    assert pytest.approx(rel["value"]) == 0.5

    history = db.get_relationship_history("player", "Gareth")
    assert len(history) == 1
    assert history[0]["new_value"] == 0.5
    assert history[0]["old_value"] is None

    db.set_relationship(
        "player", "Gareth", "disposition", -0.2, turn=10, cause="betrayal"
    )
    rel = db.get_relationship("player", "Gareth", "disposition")
    assert pytest.approx(rel["value"]) == -0.2

    history = db.get_relationship_history("player", "Gareth")
    assert len(history) == 2
    assert history[1]["old_value"] == 0.5
    assert history[1]["new_value"] == -0.2
    assert history[1]["cause"] == "betrayal"
    assert history[0]["turn_number"] <= history[1]["turn_number"]


def test_set_relationship_no_op_when_value_unchanged(db):
    db.set_relationship("player", "Gareth", "disposition", 0.5, turn=5)
    db.set_relationship("player", "Gareth", "disposition", 0.5, turn=6)
    history = db.get_relationship_history("player", "Gareth")
    assert len(history) == 1


def test_set_relationship_auto_creates_entities(db):
    db.set_relationship("player", "Mira", "disposition", 0.8, turn=1)
    assert db.get_entity("player", "npc") is not None
    assert db.get_entity("Mira", "npc") is not None


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


def test_record_event_round_trip(db):
    db.record_event(
        turn=5,
        event_type="combat",
        summary="Defeated a pack of wolves",
        primary_entity="wolf pack",
        location="Mountain Pass",
        player_input="attack the wolves",
        mechanical_changes={"hp_delta": -5, "xp_gained": 50},
        secondary_entities=["wolf alpha", "wolf omega"],
        is_notable=True,
    )
    events = db.get_recent_events(5)
    assert len(events) == 1
    ev = events[0]
    assert ev["event_type"] == "combat"
    assert ev["summary"] == "Defeated a pack of wolves"
    assert ev["primary_entity"] == "wolf pack"
    assert ev["location"] == "Mountain Pass"
    assert ev["mechanical_changes"] == {"hp_delta": -5, "xp_gained": 50}
    assert ev["secondary_entities"] == ["wolf alpha", "wolf omega"]
    assert ev["is_notable"] is True


def test_record_event_rejects_bad_type(db):
    with pytest.raises(ValueError):
        db.record_event(turn=1, event_type="nonsense", summary="x")


def test_record_event_rejects_empty_summary(db):
    with pytest.raises(ValueError):
        db.record_event(turn=1, event_type="combat", summary="")


def test_get_recent_events_orders_by_turn_desc(db):
    for turn in (1, 2, 3):
        db.record_event(turn=turn, event_type="travel", summary=f"Turn {turn}")
    events = db.get_recent_events(5)
    assert [e["turn_number"] for e in events] == [3, 2, 1]


def test_get_events_at_location(db):
    db.record_event(turn=1, event_type="travel", summary="A", location="Town")
    db.record_event(turn=2, event_type="combat", summary="B", location="Forest")
    db.record_event(turn=3, event_type="social", summary="C", location="Town")
    at_town = db.get_events_at_location("Town")
    assert [e["summary"] for e in at_town] == ["C", "A"]


def test_get_events_by_type(db):
    db.record_event(turn=1, event_type="combat", summary="A")
    db.record_event(turn=2, event_type="quest_offer", summary="B")
    db.record_event(turn=3, event_type="combat", summary="C")
    combats = db.get_events_by_type("combat")
    assert {e["summary"] for e in combats} == {"A", "C"}


# ---------------------------------------------------------------------------
# FTS5
# ---------------------------------------------------------------------------


def _fts5_available() -> bool:
    try:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE t USING fts5(x)")
        conn.close()
        return True
    except sqlite3.OperationalError:
        return False


@pytest.mark.skipif(not _fts5_available(), reason="sqlite3 FTS5 unavailable")
def test_search_entities_fts5(db):
    db.upsert_entity(
        "npc", "Gareth", turn=1, summary="A grumpy blacksmith in Millhaven"
    )
    db.upsert_entity(
        "npc", "Mira", turn=1, summary="The tavern keeper, a friendly soul"
    )
    db.upsert_entity("location", "Iron Forge", turn=1, summary="Gareth's place of work")

    hits = db.search_entities("blacksmith")
    assert any(h["name"] == "Gareth" for h in hits)

    hits = db.search_entities("tavern")
    assert any(h["name"] == "Mira" for h in hits)


@pytest.mark.skipif(not _fts5_available(), reason="sqlite3 FTS5 unavailable")
def test_search_events_fts5(db):
    db.record_event(
        turn=1, event_type="combat", summary="Defeated a troll on the bridge"
    )
    db.record_event(
        turn=2, event_type="quest_offer", summary="Quest offered: Save the village"
    )
    hits = db.search_events("troll")
    assert len(hits) >= 1
    assert "troll" in hits[0]["summary"].lower()


# ---------------------------------------------------------------------------
# Migration from a v3 GameState
# ---------------------------------------------------------------------------


def _fake_game_state():
    """Build a lightweight SimpleNamespace that looks enough like GameState
    for ``migrate_from_game_state``. Uses duck typing so tests don't depend
    on the full engine import graph."""
    world = SimpleNamespace(
        visited_locations={"Millhaven", "Iron Forge"},
        npcs_met={"Gareth", "Mira"},
        bases=[
            SimpleNamespace(
                name="Iron Keep", location_ref="Millhaven", services=["smith", "healer"]
            )
        ],
    )
    rel_gareth = SimpleNamespace(trust=30)  # hostile-ish
    rel_mira = SimpleNamespace(trust=75)  # friendly
    relationships = SimpleNamespace(
        npcs={
            "Gareth": SimpleNamespace(role="blacksmith"),
            "Mira": SimpleNamespace(role="tavern keeper"),
        },
        factions={
            "Iron Guild": SimpleNamespace(
                description="Controls metalwork in Millhaven"
            ),
        },
        relationships={"Gareth": rel_gareth, "Mira": rel_mira},
    )
    inventory = SimpleNamespace(
        items={
            "Longsword": SimpleNamespace(
                description="A sturdy blade",
                rarity="common",
                quantity=1,
                weight=3.0,
            ),
        }
    )
    quest_log = SimpleNamespace(
        quests=[
            SimpleNamespace(
                title="Find the Lost Shipment",
                description="Mira's cart of ale never arrived.",
                status=SimpleNamespace(name="ACTIVE"),
            ),
        ]
    )
    timeline_events = [
        SimpleNamespace(
            turn=1,
            type="location",
            summary="Travelled to Millhaven",
            entities=["Millhaven"],
        ),
        SimpleNamespace(turn=2, type="npc", summary="Met Gareth", entities=["Gareth"]),
    ]
    timeline = SimpleNamespace(events=timeline_events)
    return SimpleNamespace(
        turn_number=47,
        world=world,
        relationships=relationships,
        inventory=inventory,
        quest_log=quest_log,
        timeline=timeline,
    )


def test_migrate_from_game_state_populates_all_stores(db):
    gs = _fake_game_state()
    db.migrate_from_game_state(gs)

    # Entities
    assert db.get_entity("Millhaven", "location") is not None
    assert db.get_entity("Iron Forge", "location") is not None
    assert db.get_entity("Gareth", "npc") is not None
    assert db.get_entity("Mira", "npc") is not None
    assert db.get_entity("Iron Guild", "faction") is not None
    assert db.get_entity("Longsword", "item") is not None
    assert db.get_entity("Find the Lost Shipment", "quest") is not None
    assert db.get_entity("Iron Keep", "base") is not None

    # Relationship — trust=30 normalizes to (30-50)/50 = -0.4
    rel = db.get_relationship("player", "Gareth", "disposition")
    assert rel is not None
    assert pytest.approx(rel["value"], abs=1e-6) == -0.4

    rel = db.get_relationship("player", "Mira", "disposition")
    assert pytest.approx(rel["value"], abs=1e-6) == 0.5

    # Events from timeline
    events = db.get_recent_events(10)
    assert len(events) == 2
    assert {e["summary"] for e in events} == {
        "Travelled to Millhaven",
        "Met Gareth",
    }


def test_migrate_is_idempotent_via_metadata_flag(db):
    gs = _fake_game_state()
    db.migrate_from_game_state(gs)
    db.set_metadata("migrated_from_v3_save", "1")

    # Running the migration a second time re-upserts but doesn't duplicate
    # — canonical_name dedup means entity rows stay unique.
    db.migrate_from_game_state(gs)
    npcs = db.get_entities_at("", entity_type="npc")  # location="" won't match
    gareth_rows = db._conn.execute(
        "SELECT COUNT(*) FROM entities WHERE entity_type='npc' AND canonical_name='gareth'"
    ).fetchone()
    assert gareth_rows[0] == 1


# ---------------------------------------------------------------------------
# Foreign key enforcement
# ---------------------------------------------------------------------------


def test_transaction_commits_all_writes_atomically(db):
    """A successful `transaction()` block flushes a single commit at the end."""
    with db.transaction():
        db.upsert_entity("npc", "Gareth", turn=1)
        db.upsert_entity("npc", "Mira", turn=1)
        db.record_event(turn=1, event_type="travel", summary="Arrived at Millhaven")
    assert db.get_entity("Gareth") is not None
    assert db.get_entity("Mira") is not None
    assert len(db.get_recent_events(5)) == 1


def test_transaction_rolls_back_on_exception(db):
    """If the `transaction()` block raises, none of its writes commit."""
    with pytest.raises(RuntimeError):
        with db.transaction():
            db.upsert_entity("npc", "Bob", turn=1)
            db.record_event(turn=1, event_type="travel", summary="x")
            raise RuntimeError("boom")
    assert db.get_entity("Bob") is None
    assert db.get_recent_events(5) == []


def test_migration_self_guards_via_metadata_flag(db):
    gs = _fake_game_state()
    assert db.migrate_from_game_state(gs) is True
    # Second call detects the flag and bails out.
    assert db.migrate_from_game_state(gs) is False


def test_record_event_canonicalizes_primary_entity(db):
    db.record_event(
        turn=1,
        event_type="social",
        summary="Met The Blacksmith",
        primary_entity="The Blacksmith",
    )
    # Stored canonical so the index lookup works without LOWER().
    rows = db._conn.execute("SELECT primary_entity FROM events").fetchall()
    assert rows[0]["primary_entity"] == "blacksmith"
    # And get_events_for_entity finds it via either spelling.
    assert len(db.get_events_for_entity("The Blacksmith")) == 1
    assert len(db.get_events_for_entity("blacksmith")) == 1


def test_foreign_key_enforced_on_relationship_delete(db):
    db.upsert_entity("npc", "Gareth", turn=1)
    db.upsert_entity("npc", "Mira", turn=1)
    db.set_relationship("Gareth", "Mira", "rival", 0.0, turn=1)

    # Deleting Gareth while a relationship still references him must fail.
    with pytest.raises(sqlite3.IntegrityError):
        db._conn.execute("DELETE FROM entities WHERE canonical_name='gareth'")
        db._conn.commit()
