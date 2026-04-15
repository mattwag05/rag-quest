"""SQLite-backed entity registry and event log.

Phase 1 of the v0.9 memory architecture redesign (see
``docs/MEMORY_ARCHITECTURE.md``). ``WorldDB`` is populated by shadow-writes
from the existing ``StateChange`` flow in ``engine/turn.py::collect_post_turn_effects``.
Phase 2 wired ``MemoryAssembler`` as the narrator's read path. Phase 3
(shipped in v0.9.1) retired the dead ``WorldRAG.record_event`` method and
flipped ``memory.assembler_enabled`` on by default, so the shadow-write
is now the only per-turn write path and WorldDB is the authoritative
event store.

Design rules:

- Synchronous, stdlib ``sqlite3`` only. No new dependencies.
- ``PRAGMA foreign_keys = ON`` and WAL journal mode.
- Schema creation is idempotent via ``IF NOT EXISTS``.
- Canonical name normalization (lowercase, strip leading articles, collapse
  whitespace) so ``"the blacksmith Gareth"``, ``"Gareth the blacksmith"``, and
  ``"Gareth"`` dedupe onto one entity row when the state parser re-extracts
  them turn after turn.
- All query methods return ``dict`` rows. JSON columns are deserialized at
  read time; malformed blobs decode to ``{}``/``[]`` rather than raising.
- Failures in optional paths (FTS5 trigger install, etc.) log via
  ``log_swallowed_exc`` so ``RAG_QUEST_DEBUG=1`` surfaces them. Hot-path
  writes never swallow — a broken insert should reach the turn-helper
  swallow block, not hide inside the DB layer.
"""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable, Iterator

SCHEMA_VERSION = 1


class EntityType(StrEnum):
    """Canonical entity kinds stored in ``WorldDB.entities``.

    The ``CHECK(entity_type IN (...))`` clause in the entities DDL is
    derived from these values, and every call site in
    ``engine/state_event_mapping.py`` uses the enum instead of string
    literals so a typo is caught at import time rather than as a runtime
    CHECK violation (rag-quest-csi).
    """

    NPC = "npc"
    LOCATION = "location"
    FACTION = "faction"
    ITEM = "item"
    QUEST = "quest"
    BASE = "base"


class EventType(StrEnum):
    """Canonical event kinds stored in ``WorldDB.events``.

    Same derivation story as :class:`EntityType` — the CHECK clause in
    the events DDL is built from these members at schema-creation time.
    """

    COMBAT = "combat"
    QUEST_OFFER = "quest_offer"
    QUEST_COMPLETE = "quest_complete"
    SOCIAL = "social"
    DISCOVERY = "discovery"
    TRADE = "trade"
    TRAVEL = "travel"
    WORLD_EVENT = "world_event"
    ITEM = "item"
    DEATH = "death"
    LEVEL_UP = "level_up"
    BASE_CLAIM = "base_claim"
    MODULE_UNLOCK = "module_unlock"
    MODULE_COMPLETE = "module_complete"
    BOOKMARK = "bookmark"


# Derived lookup sets — a single source of truth means the validation
# sets, the DDL CHECK clauses, and the state_event_mapping literals all
# agree by construction.
_ENTITY_TYPES = frozenset(e.value for e in EntityType)
_EVENT_TYPES = frozenset(e.value for e in EventType)


def _sql_check_in_clause(column: str, values: Iterable[str]) -> str:
    """Render ``column IN ('a','b',...)`` for use inside a DDL CHECK.

    Values are quoted as SQL string literals. Apostrophes are doubled so
    a member with a ``'`` would still round-trip cleanly (none currently
    have one, but the helper stays safe if one is added).
    """
    escaped = ", ".join("'" + v.replace("'", "''") + "'" for v in sorted(values))
    return f"{column} IN ({escaped})"


_LEADING_ARTICLE = re.compile(r"^(?:the|a|an)\s+", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")


def canonical_name(name: str) -> str:
    """Normalize an entity name for dedup/matching.

    Lowercases, strips leading articles, collapses internal whitespace. The
    result is stable across the variants the state parser tends to emit
    ("Gareth", "Gareth the Blacksmith", "the blacksmith Gareth"). Reversed
    wording ("the blacksmith Gareth" → "blacksmith gareth") does NOT collapse
    to the same canonical as "Gareth" — that level of entity resolution is
    §9 of the architecture doc and belongs to Phase 2+.
    """
    if not name:
        return ""
    cleaned = _WHITESPACE.sub(" ", name.strip())
    cleaned = _LEADING_ARTICLE.sub("", cleaned)
    return cleaned.lower()


def _to_json(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return None


def _from_json(value: Any, fallback: Any) -> Any:
    if value is None or value == "":
        return fallback
    if not isinstance(value, str):
        return fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


class WorldDB:
    """SQLite-backed world state and event store.

    One instance per world. Lifetime matches the loaded ``GameState`` —
    constructed when a CLI session starts or a web session hydrates, closed
    in the same cleanup block that tears down ``WorldRAG``.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        try:
            self._conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.Error:
            from .._debug import log_swallowed_exc

            log_swallowed_exc("worlddb.wal_pragma")
        # When True, individual write methods skip their inline `commit()` so
        # the surrounding `transaction()` block can flush them all at once.
        # Cuts the per-turn shadow-write cost from ~7 fsyncs to 1.
        self._in_transaction = False
        self._fts5_available = self._check_fts5()
        self._create_schema()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Batch a series of writes into a single SQLite transaction.

        Inside the block, every write method's inline ``commit()`` becomes a
        no-op. The block commits once on successful exit, or rolls back the
        whole batch if an exception escapes. Used by the per-turn shadow
        write and the v3 migration so neither pays for N fsyncs per turn /
        per migrated row, and so a mid-migration crash can't duplicate
        previously-written events on retry.
        """
        if self._in_transaction:
            # Re-entrant call: just yield. The outermost block owns commit.
            yield
            return
        self._in_transaction = True
        try:
            yield
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            self._in_transaction = False

    def _commit(self) -> None:
        """Commit immediately unless we're inside a ``transaction()`` block."""
        if not self._in_transaction:
            self._conn.commit()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _check_fts5(self) -> bool:
        try:
            self._conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_probe USING fts5(x)"
            )
            self._conn.execute("DROP TABLE IF EXISTS _fts5_probe")
            return True
        except sqlite3.OperationalError:
            from .._debug import log_swallowed_exc

            log_swallowed_exc("worlddb.fts5_probe")
            return False

    def _create_schema(self) -> None:
        c = self._conn
        entity_check = _sql_check_in_clause("entity_type", _ENTITY_TYPES)
        event_check = _sql_check_in_clause("event_type", _EVENT_TYPES)
        c.executescript(f"""
            CREATE TABLE IF NOT EXISTS db_metadata (
                key   TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS entities (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type      TEXT NOT NULL
                                    CHECK({entity_check}),
                name             TEXT NOT NULL,
                canonical_name   TEXT NOT NULL,
                current_location TEXT,
                status           TEXT DEFAULT 'active',
                summary          TEXT,
                created_at_turn  INTEGER NOT NULL,
                last_seen_turn   INTEGER,
                metadata         TEXT,
                UNIQUE(entity_type, canonical_name)
            );
            CREATE INDEX IF NOT EXISTS idx_entities_location
                ON entities(current_location);
            CREATE INDEX IF NOT EXISTS idx_entities_type
                ON entities(entity_type);

            CREATE TABLE IF NOT EXISTS relationships (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_a_id       INTEGER NOT NULL REFERENCES entities(id),
                entity_b_id       INTEGER NOT NULL REFERENCES entities(id),
                relationship_type TEXT NOT NULL,
                value             REAL,
                last_changed_turn INTEGER NOT NULL,
                UNIQUE(entity_a_id, entity_b_id, relationship_type)
            );

            CREATE TABLE IF NOT EXISTS relationship_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                relationship_id INTEGER NOT NULL REFERENCES relationships(id),
                old_value       REAL,
                new_value       REAL,
                turn_number     INTEGER NOT NULL,
                cause           TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_rel_history_rel
                ON relationship_history(relationship_id);

            CREATE TABLE IF NOT EXISTS events (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_number        INTEGER NOT NULL,
                event_type         TEXT NOT NULL
                                      CHECK({event_check}),
                primary_entity     TEXT,
                location           TEXT,
                summary            TEXT NOT NULL,
                player_input       TEXT,
                mechanical_changes TEXT,
                secondary_entities TEXT,
                is_notable         INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_events_turn
                ON events(turn_number);
            CREATE INDEX IF NOT EXISTS idx_events_entity
                ON events(primary_entity);
            CREATE INDEX IF NOT EXISTS idx_events_location
                ON events(location);
            CREATE INDEX IF NOT EXISTS idx_events_type
                ON events(event_type);
            """)

        if self._fts5_available:
            try:
                c.executescript("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
                        name, summary, content='entities', content_rowid='id'
                    );
                    CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
                        summary, player_input, content='events', content_rowid='id'
                    );

                    CREATE TRIGGER IF NOT EXISTS entities_ai
                    AFTER INSERT ON entities BEGIN
                        INSERT INTO entities_fts(rowid, name, summary)
                        VALUES (new.id, new.name, COALESCE(new.summary, ''));
                    END;

                    CREATE TRIGGER IF NOT EXISTS entities_ad
                    AFTER DELETE ON entities BEGIN
                        INSERT INTO entities_fts(entities_fts, rowid, name, summary)
                        VALUES('delete', old.id, old.name, COALESCE(old.summary, ''));
                    END;

                    CREATE TRIGGER IF NOT EXISTS entities_au
                    AFTER UPDATE ON entities BEGIN
                        INSERT INTO entities_fts(entities_fts, rowid, name, summary)
                        VALUES('delete', old.id, old.name, COALESCE(old.summary, ''));
                        INSERT INTO entities_fts(rowid, name, summary)
                        VALUES (new.id, new.name, COALESCE(new.summary, ''));
                    END;

                    CREATE TRIGGER IF NOT EXISTS events_ai
                    AFTER INSERT ON events BEGIN
                        INSERT INTO events_fts(rowid, summary, player_input)
                        VALUES (new.id, new.summary, COALESCE(new.player_input, ''));
                    END;

                    CREATE TRIGGER IF NOT EXISTS events_ad
                    AFTER DELETE ON events BEGIN
                        INSERT INTO events_fts(events_fts, rowid, summary, player_input)
                        VALUES('delete', old.id, old.summary, COALESCE(old.player_input, ''));
                    END;
                    """)
            except sqlite3.OperationalError:
                from .._debug import log_swallowed_exc

                log_swallowed_exc("worlddb.fts5_install")
                self._fts5_available = False

        c.execute(
            "INSERT OR IGNORE INTO db_metadata(key, value) VALUES(?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )
        c.commit()

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_metadata(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM db_metadata WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set_metadata(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO db_metadata(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self._commit()

    # ------------------------------------------------------------------
    # Entities
    # ------------------------------------------------------------------

    def upsert_entity(
        self,
        entity_type: str,
        name: str,
        *,
        turn: int,
        location: str | None = None,
        status: str = "active",
        summary: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Insert or update an entity. Returns the entity id.

        Matches on ``(entity_type, canonical_name)``. On update, only
        non-``None`` fields overwrite; ``last_seen_turn`` is always bumped
        to ``turn``.
        """
        if entity_type not in _ENTITY_TYPES:
            raise ValueError(f"Unknown entity_type: {entity_type!r}")
        canon = canonical_name(name)
        if not canon:
            raise ValueError("entity name must be non-empty after normalization")

        existing = self._conn.execute(
            "SELECT id, current_location, status, summary, metadata "
            "FROM entities WHERE entity_type = ? AND canonical_name = ?",
            (entity_type, canon),
        ).fetchone()

        metadata_json = _to_json(metadata) if metadata is not None else None

        if existing is None:
            cur = self._conn.execute(
                "INSERT INTO entities "
                "(entity_type, name, canonical_name, current_location, "
                " status, summary, created_at_turn, last_seen_turn, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entity_type,
                    name,
                    canon,
                    location,
                    status,
                    summary,
                    turn,
                    turn,
                    metadata_json,
                ),
            )
            self._commit()
            return int(cur.lastrowid)

        entity_id = int(existing["id"])
        new_location = (
            location if location is not None else existing["current_location"]
        )
        new_status = status if status else existing["status"]
        new_summary = summary if summary is not None else existing["summary"]
        new_metadata = (
            metadata_json if metadata_json is not None else existing["metadata"]
        )
        self._conn.execute(
            "UPDATE entities SET "
            "current_location = ?, status = ?, summary = ?, "
            "last_seen_turn = ?, metadata = ? WHERE id = ?",
            (
                new_location,
                new_status,
                new_summary,
                turn,
                new_metadata,
                entity_id,
            ),
        )
        self._commit()
        return entity_id

    def get_entity(self, name: str, entity_type: str | None = None) -> dict | None:
        canon = canonical_name(name)
        if not canon:
            return None
        if entity_type is not None:
            row = self._conn.execute(
                "SELECT * FROM entities "
                "WHERE entity_type = ? AND canonical_name = ? "
                "LIMIT 1",
                (entity_type, canon),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM entities WHERE canonical_name = ? LIMIT 1",
                (canon,),
            ).fetchone()
        return self._entity_row(row)

    def get_entities_at(
        self, location: str, entity_type: str | None = None
    ) -> list[dict]:
        if entity_type is not None:
            rows = self._conn.execute(
                "SELECT * FROM entities "
                "WHERE current_location = ? AND entity_type = ? "
                "ORDER BY last_seen_turn DESC",
                (location, entity_type),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM entities "
                "WHERE current_location = ? "
                "ORDER BY last_seen_turn DESC",
                (location,),
            ).fetchall()
        return [self._entity_row(r) for r in rows if r is not None]

    def search_entities(self, query: str, limit: int = 10) -> list[dict]:
        query = (query or "").strip()
        if not query:
            return []
        if self._fts5_available:
            try:
                rows = self._conn.execute(
                    "SELECT e.* FROM entities_fts f "
                    "JOIN entities e ON e.id = f.rowid "
                    "WHERE entities_fts MATCH ? "
                    "ORDER BY e.last_seen_turn DESC "
                    "LIMIT ?",
                    (query, int(limit)),
                ).fetchall()
                return [self._entity_row(r) for r in rows]
            except sqlite3.OperationalError:
                from .._debug import log_swallowed_exc

                log_swallowed_exc("worlddb.search_entities_fts")
        like = f"%{query.lower()}%"
        rows = self._conn.execute(
            "SELECT * FROM entities "
            "WHERE LOWER(name) LIKE ? OR LOWER(COALESCE(summary, '')) LIKE ? "
            "ORDER BY last_seen_turn DESC LIMIT ?",
            (like, like, int(limit)),
        ).fetchall()
        return [self._entity_row(r) for r in rows]

    def _entity_row(self, row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        d = dict(row)
        d["metadata"] = _from_json(d.get("metadata"), {})
        return d

    def search_entities_any(
        self, tokens: Iterable[str], limit_per_token: int = 3
    ) -> list[dict]:
        """Match any of ``tokens`` against the entity registry in one query.

        Replaces ``MemoryAssembler._extract_entity_references``'s per-token
        fan-out (one ``search_entities`` per word) with a single FTS5
        ``MATCH`` on ``token1 OR token2 OR ...`` (rag-quest-pvt). When
        FTS5 isn't compiled in, falls back to a single ``LIKE ? OR LIKE ? ...``
        query over ``name`` / ``canonical_name`` / ``summary``.

        Tokens are sanitized via ``[^A-Za-z0-9' -]`` before reaching the
        FTS5 parser so special characters from state parser output can't
        break the query (and can't be used as an injection vector when the
        raw player input is forwarded). Empty / whitespace-only tokens are
        dropped.
        """
        sanitized: list[str] = []
        seen: set[str] = set()
        for token in tokens or []:
            if not token:
                continue
            for part in re.findall(r"[A-Za-z0-9'-]+", str(token)):
                if len(part) < 2:
                    continue
                key = part.lower()
                if key in seen:
                    continue
                seen.add(key)
                sanitized.append(part)
        if not sanitized:
            return []

        total_limit = max(1, int(limit_per_token) * len(sanitized))

        if self._fts5_available:
            match_expr = " OR ".join(f'"{t}"' for t in sanitized)
            try:
                rows = self._conn.execute(
                    "SELECT e.* FROM entities_fts f "
                    "JOIN entities e ON e.id = f.rowid "
                    "WHERE entities_fts MATCH ? "
                    "ORDER BY e.last_seen_turn DESC "
                    "LIMIT ?",
                    (match_expr, total_limit),
                ).fetchall()
                return [self._entity_row(r) for r in rows if r is not None]
            except sqlite3.OperationalError:
                from .._debug import log_swallowed_exc

                log_swallowed_exc("worlddb.search_entities_any_fts")

        like_clauses: list[str] = []
        params: list[Any] = []
        for token in sanitized:
            like = f"%{token.lower()}%"
            like_clauses.append(
                "LOWER(name) LIKE ? OR canonical_name LIKE ? "
                "OR LOWER(COALESCE(summary, '')) LIKE ?"
            )
            params.extend([like, like, like])
        sql = (
            "SELECT * FROM entities WHERE "
            + " OR ".join(f"({c})" for c in like_clauses)
            + " ORDER BY last_seen_turn DESC LIMIT ?"
        )
        params.append(total_limit)
        rows = self._conn.execute(sql, params).fetchall()
        return [self._entity_row(r) for r in rows if r is not None]

    def get_entity_snapshot_batch(
        self, names: Iterable[str], location: str = ""
    ) -> list[dict]:
        """Batch the entity + disposition + last-event fan-out into one query.

        Replaces ``MemoryAssembler._pull_entity_snapshots``'s ~3 queries per
        entity (``get_entity`` + ``get_relationship`` + ``get_events_for_entity``)
        with a single ``LEFT JOIN`` across entities / relationships / events.
        Return shape matches what the assembler already consumes:

            ``[{"entity": {...}, "disposition": float|None, "last_event": {...}|None}, ...]``

        Order contract: referenced entities in the order they appear in
        ``names`` first, then any additional entities at ``location`` (in
        ``last_seen_turn`` DESC order). Entities that are both referenced
        and present at ``location`` appear exactly once, in the referenced
        slot.
        """
        ref_canons: list[str] = []
        seen_canons: set[str] = set()
        for name in names or []:
            canon = canonical_name(name or "")
            if not canon or canon in seen_canons:
                continue
            seen_canons.add(canon)
            ref_canons.append(canon)

        if not ref_canons and not location:
            return []

        player_row = self._conn.execute(
            "SELECT id FROM entities WHERE canonical_name = ? LIMIT 1",
            ("player",),
        ).fetchone()
        player_id = int(player_row["id"]) if player_row is not None else None

        where_clauses: list[str] = []
        params: list[Any] = [player_id if player_id is not None else -1]
        if ref_canons:
            placeholders = ",".join("?" * len(ref_canons))
            where_clauses.append(f"e.canonical_name IN ({placeholders})")
            params.extend(ref_canons)
        if location:
            where_clauses.append("e.current_location = ?")
            params.append(location)
        where_sql = " OR ".join(where_clauses)

        sql = f"""
            SELECT
                e.*,
                r.value AS _disposition,
                ev.id                 AS _ev_id,
                ev.turn_number        AS _ev_turn,
                ev.event_type         AS _ev_type,
                ev.primary_entity     AS _ev_primary,
                ev.location           AS _ev_location,
                ev.summary            AS _ev_summary,
                ev.player_input       AS _ev_player_input,
                ev.mechanical_changes AS _ev_mechanical,
                ev.secondary_entities AS _ev_secondary,
                ev.is_notable         AS _ev_notable
            FROM entities e
            LEFT JOIN relationships r
                ON r.entity_a_id = ?
               AND r.entity_b_id = e.id
               AND r.relationship_type = 'disposition'
            LEFT JOIN events ev
                ON ev.id = (
                    SELECT id FROM events
                    WHERE primary_entity = e.canonical_name
                    ORDER BY turn_number DESC, id DESC
                    LIMIT 1
                )
            WHERE {where_sql}
            ORDER BY e.last_seen_turn DESC
        """

        rows = self._conn.execute(sql, params).fetchall()

        by_canon: dict[str, dict] = {}
        for row in rows:
            entity = self._entity_row(row)
            if entity is None:
                continue
            canon = entity.get("canonical_name") or ""
            disposition = (
                float(row["_disposition"]) if row["_disposition"] is not None else None
            )
            last_event: dict | None = None
            if row["_ev_id"] is not None:
                last_event = self._event_row(
                    {  # type: ignore[arg-type]
                        "id": row["_ev_id"],
                        "turn_number": row["_ev_turn"],
                        "event_type": row["_ev_type"],
                        "primary_entity": row["_ev_primary"],
                        "location": row["_ev_location"],
                        "summary": row["_ev_summary"],
                        "player_input": row["_ev_player_input"],
                        "mechanical_changes": row["_ev_mechanical"],
                        "secondary_entities": row["_ev_secondary"],
                        "is_notable": row["_ev_notable"],
                    }
                )
            by_canon[canon] = {
                "entity": entity,
                "disposition": disposition,
                "last_event": last_event,
            }

        out: list[dict] = []
        emitted: set[str] = set()
        for canon in ref_canons:
            snap = by_canon.get(canon)
            if snap is None:
                continue
            out.append(snap)
            emitted.add(canon)
        for canon, snap in by_canon.items():
            if canon in emitted:
                continue
            out.append(snap)
        return out

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    def set_relationship(
        self,
        entity_a: str,
        entity_b: str,
        rel_type: str,
        value: float,
        turn: int,
        cause: str | None = None,
        *,
        entity_a_type: str = "npc",
        entity_b_type: str = "npc",
    ) -> None:
        """Set or update a relationship. Records history if value changed.

        Auto-creates either entity if it doesn't exist yet (common when the
        state parser extracts a new NPC name that hasn't been upserted
        directly). The default type for both sides is ``npc``; override via
        ``entity_a_type`` / ``entity_b_type`` for player↔faction etc.
        """
        a_id = self._ensure_entity(entity_a, entity_a_type, turn)
        b_id = self._ensure_entity(entity_b, entity_b_type, turn)

        existing = self._conn.execute(
            "SELECT id, value FROM relationships "
            "WHERE entity_a_id = ? AND entity_b_id = ? AND relationship_type = ?",
            (a_id, b_id, rel_type),
        ).fetchone()

        if existing is None:
            cur = self._conn.execute(
                "INSERT INTO relationships "
                "(entity_a_id, entity_b_id, relationship_type, value, last_changed_turn) "
                "VALUES (?, ?, ?, ?, ?)",
                (a_id, b_id, rel_type, float(value), turn),
            )
            self._conn.execute(
                "INSERT INTO relationship_history "
                "(relationship_id, old_value, new_value, turn_number, cause) "
                "VALUES (?, ?, ?, ?, ?)",
                (cur.lastrowid, None, float(value), turn, cause),
            )
            self._commit()
            return

        rel_id = int(existing["id"])
        old_value = existing["value"]
        if old_value is not None and abs(old_value - float(value)) < 1e-9:
            return
        self._conn.execute(
            "UPDATE relationships SET value = ?, last_changed_turn = ? WHERE id = ?",
            (float(value), turn, rel_id),
        )
        self._conn.execute(
            "INSERT INTO relationship_history "
            "(relationship_id, old_value, new_value, turn_number, cause) "
            "VALUES (?, ?, ?, ?, ?)",
            (rel_id, old_value, float(value), turn, cause),
        )
        self._commit()

    def _ensure_entity(self, name: str, entity_type: str, turn: int) -> int:
        existing = self.get_entity(name, entity_type)
        if existing is not None:
            return int(existing["id"])
        return self.upsert_entity(entity_type, name, turn=turn)

    def get_relationship(
        self, entity_a: str, entity_b: str, rel_type: str | None = None
    ) -> dict | None:
        a = self.get_entity(entity_a)
        b = self.get_entity(entity_b)
        if a is None or b is None:
            return None
        if rel_type is not None:
            row = self._conn.execute(
                "SELECT * FROM relationships "
                "WHERE entity_a_id = ? AND entity_b_id = ? AND relationship_type = ? "
                "LIMIT 1",
                (a["id"], b["id"], rel_type),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM relationships "
                "WHERE entity_a_id = ? AND entity_b_id = ? "
                "ORDER BY last_changed_turn DESC LIMIT 1",
                (a["id"], b["id"]),
            ).fetchone()
        return dict(row) if row is not None else None

    def get_relationship_history(self, entity_a: str, entity_b: str) -> list[dict]:
        a = self.get_entity(entity_a)
        b = self.get_entity(entity_b)
        if a is None or b is None:
            return []
        rows = self._conn.execute(
            "SELECT rh.* FROM relationship_history rh "
            "JOIN relationships r ON r.id = rh.relationship_id "
            "WHERE r.entity_a_id = ? AND r.entity_b_id = ? "
            "ORDER BY rh.turn_number ASC",
            (a["id"], b["id"]),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def record_event(
        self,
        turn: int,
        event_type: str,
        *,
        summary: str,
        primary_entity: str | None = None,
        location: str | None = None,
        player_input: str | None = None,
        mechanical_changes: dict | None = None,
        secondary_entities: Iterable[str] | None = None,
        is_notable: bool = False,
    ) -> int:
        if event_type not in _EVENT_TYPES:
            raise ValueError(f"Unknown event_type: {event_type!r}")
        if not summary:
            raise ValueError("event summary is required")
        sec_list = list(secondary_entities) if secondary_entities else None
        # Store `primary_entity` in canonical form so `get_events_for_entity`
        # can use the `idx_events_entity` index without wrapping the column
        # in `LOWER()` (which defeats the index). Display names are still
        # preserved on the `entities` table.
        primary_canonical = canonical_name(primary_entity) if primary_entity else None
        cur = self._conn.execute(
            "INSERT INTO events "
            "(turn_number, event_type, primary_entity, location, summary, "
            " player_input, mechanical_changes, secondary_entities, is_notable) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                int(turn),
                event_type,
                primary_canonical,
                location,
                summary,
                player_input,
                _to_json(mechanical_changes),
                _to_json(sec_list),
                1 if is_notable else 0,
            ),
        )
        self._commit()
        return int(cur.lastrowid)

    def get_recent_events(self, n: int = 10) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM events ORDER BY turn_number DESC, id DESC LIMIT ?",
            (int(n),),
        ).fetchall()
        return [self._event_row(r) for r in rows]

    def get_events_for_entity(self, entity_name: str, limit: int = 20) -> list[dict]:
        canon = canonical_name(entity_name)
        if not canon:
            return []
        # `primary_entity` is stored canonical, so the `idx_events_entity`
        # index handles this without a function wrap. The secondary-entities
        # JSON column still needs a LIKE — that's a Phase 2 concern (a join
        # table would be the right fix when the assembler needs it).
        rows = self._conn.execute(
            "SELECT * FROM events "
            "WHERE primary_entity = ? "
            "   OR LOWER(COALESCE(secondary_entities, '')) LIKE ? "
            "ORDER BY turn_number DESC, id DESC LIMIT ?",
            (canon, f'%"{entity_name.lower()}"%', int(limit)),
        ).fetchall()
        return [self._event_row(r) for r in rows]

    def get_events_at_location(self, location: str, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM events WHERE location = ? "
            "ORDER BY turn_number DESC, id DESC LIMIT ?",
            (location, int(limit)),
        ).fetchall()
        return [self._event_row(r) for r in rows]

    def get_events_by_type(self, event_type: str, limit: int = 20) -> list[dict]:
        if event_type not in _EVENT_TYPES:
            return []
        rows = self._conn.execute(
            "SELECT * FROM events WHERE event_type = ? "
            "ORDER BY turn_number DESC, id DESC LIMIT ?",
            (event_type, int(limit)),
        ).fetchall()
        return [self._event_row(r) for r in rows]

    def search_events(self, query: str, limit: int = 10) -> list[dict]:
        query = (query or "").strip()
        if not query:
            return []
        if self._fts5_available:
            try:
                rows = self._conn.execute(
                    "SELECT e.* FROM events_fts f "
                    "JOIN events e ON e.id = f.rowid "
                    "WHERE events_fts MATCH ? "
                    "ORDER BY e.turn_number DESC LIMIT ?",
                    (query, int(limit)),
                ).fetchall()
                return [self._event_row(r) for r in rows]
            except sqlite3.OperationalError:
                from .._debug import log_swallowed_exc

                log_swallowed_exc("worlddb.search_events_fts")
        like = f"%{query.lower()}%"
        rows = self._conn.execute(
            "SELECT * FROM events "
            "WHERE LOWER(summary) LIKE ? OR LOWER(COALESCE(player_input, '')) LIKE ? "
            "ORDER BY turn_number DESC LIMIT ?",
            (like, like, int(limit)),
        ).fetchall()
        return [self._event_row(r) for r in rows]

    def _event_row(self, row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        d = dict(row)
        d["mechanical_changes"] = _from_json(d.get("mechanical_changes"), {})
        d["secondary_entities"] = _from_json(d.get("secondary_entities"), [])
        d["is_notable"] = bool(d.get("is_notable"))
        return d

    # ------------------------------------------------------------------
    # Migration from v3 saves
    # ------------------------------------------------------------------

    def migrate_from_game_state(self, game_state: Any, *, force: bool = False) -> bool:
        """One-time migration: populate entities + events from an in-memory GameState.

        Covers ``World.npcs_met``, ``World.visited_locations``, ``World.bases``,
        ``RelationshipManager`` (npcs + relationships + factions),
        ``Inventory.items``, ``QuestLog.quests``, and ``Timeline.events``.

        Lossy — only the shapes the current GameState preserves. The new turn
        loop fills in full detail from this point forward.

        Self-guarding: checks the ``migrated_from_v3_save`` metadata flag and
        bails out if migration has already run. The entire population +
        flag-set runs in a single transaction so a crash mid-migration rolls
        back cleanly and the next load retries from a clean slate (otherwise
        ``record_event`` rows from the timeline walk would duplicate on
        retry, since events have no UNIQUE constraint).

        Returns ``True`` if migration ran, ``False`` if it was skipped because
        the flag was already set. Pass ``force=True`` to bypass the gate
        (used by tests).
        """
        if not force and self.get_metadata("migrated_from_v3_save") == "1":
            return False

        with self.transaction():
            self._do_migration(game_state)
            self.set_metadata("migrated_from_v3_save", "1")
        return True

    def _do_migration(self, game_state: Any) -> None:
        turn = int(getattr(game_state, "turn_number", 0) or 0)
        world = getattr(game_state, "world", None)

        if world is not None:
            for loc in getattr(world, "visited_locations", set()) or set():
                try:
                    self.upsert_entity("location", loc, turn=turn)
                except Exception:
                    from .._debug import log_swallowed_exc

                    log_swallowed_exc("worlddb.migrate.location")

            for npc in getattr(world, "npcs_met", set()) or set():
                try:
                    self.upsert_entity("npc", npc, turn=turn)
                except Exception:
                    from .._debug import log_swallowed_exc

                    log_swallowed_exc("worlddb.migrate.npc_met")

            for base in getattr(world, "bases", []) or []:
                try:
                    self.upsert_entity(
                        "base",
                        getattr(base, "name", "") or "",
                        turn=turn,
                        location=getattr(base, "location_ref", None),
                        summary=", ".join(getattr(base, "services", []) or []) or None,
                    )
                except Exception:
                    from .._debug import log_swallowed_exc

                    log_swallowed_exc("worlddb.migrate.base")

        relationships = getattr(game_state, "relationships", None)
        if relationships is not None:
            for npc_name, npc in (getattr(relationships, "npcs", {}) or {}).items():
                try:
                    role = getattr(npc, "role", None)
                    self.upsert_entity(
                        "npc",
                        npc_name,
                        turn=turn,
                        summary=role if role else None,
                    )
                except Exception:
                    from .._debug import log_swallowed_exc

                    log_swallowed_exc("worlddb.migrate.rel_npc")

            for name, fac in (getattr(relationships, "factions", {}) or {}).items():
                try:
                    self.upsert_entity(
                        "faction",
                        name,
                        turn=turn,
                        summary=getattr(fac, "description", None),
                    )
                except Exception:
                    from .._debug import log_swallowed_exc

                    log_swallowed_exc("worlddb.migrate.faction")

            # Player disposition toward each NPC — normalize 0–100 trust to
            # the -1.0 … +1.0 range the architecture doc specifies.
            rels = getattr(relationships, "relationships", {}) or {}
            if rels:
                try:
                    self._ensure_entity("player", "npc", turn)
                except Exception:
                    from .._debug import log_swallowed_exc

                    log_swallowed_exc("worlddb.migrate.player_entity")
                for npc_name, rel in rels.items():
                    try:
                        trust = int(getattr(rel, "trust", 50) or 50)
                        value = (trust - 50) / 50.0
                        self.set_relationship(
                            "player",
                            npc_name,
                            "disposition",
                            value,
                            turn,
                            cause="migrated from v3 save",
                        )
                    except Exception:
                        from .._debug import log_swallowed_exc

                        log_swallowed_exc("worlddb.migrate.relationship")

        inventory = getattr(game_state, "inventory", None)
        if inventory is not None:
            for item_name, item in (getattr(inventory, "items", {}) or {}).items():
                try:
                    self.upsert_entity(
                        "item",
                        item_name,
                        turn=turn,
                        summary=getattr(item, "description", None),
                        metadata={
                            "rarity": getattr(item, "rarity", "common"),
                            "quantity": getattr(item, "quantity", 1),
                            "weight": getattr(item, "weight", 1.0),
                        },
                    )
                except Exception:
                    from .._debug import log_swallowed_exc

                    log_swallowed_exc("worlddb.migrate.item")

        quest_log = getattr(game_state, "quest_log", None)
        if quest_log is not None:
            for quest in getattr(quest_log, "quests", []) or []:
                try:
                    status = getattr(quest, "status", None)
                    status_name = (
                        status.name.lower()
                        if status is not None and hasattr(status, "name")
                        else "active"
                    )
                    self.upsert_entity(
                        "quest",
                        getattr(quest, "title", "") or "Untitled",
                        turn=turn,
                        status=status_name,
                        summary=getattr(quest, "description", None),
                    )
                except Exception:
                    from .._debug import log_swallowed_exc

                    log_swallowed_exc("worlddb.migrate.quest")

        timeline = getattr(game_state, "timeline", None)
        if timeline is not None:
            for ev in getattr(timeline, "events", []) or []:
                try:
                    ev_type = _timeline_type_to_event_type(getattr(ev, "type", ""))
                    entities = list(getattr(ev, "entities", []) or [])
                    self.record_event(
                        turn=int(getattr(ev, "turn", 0) or 0),
                        event_type=ev_type,
                        summary=str(getattr(ev, "summary", "") or "(migrated event)"),
                        primary_entity=entities[0] if entities else None,
                        secondary_entities=entities[1:] if len(entities) > 1 else None,
                    )
                except Exception:
                    from .._debug import log_swallowed_exc

                    log_swallowed_exc("worlddb.migrate.event")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def checkpoint(self) -> None:
        """Truncate the WAL so the ``.db`` file is self-contained after save.

        Called from ``_save_game`` alongside the JSON dump so the on-disk
        state is consistent if the process dies between turns. Cheap in
        normal operation — WAL is only populated since the last checkpoint.
        """
        try:
            self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self._conn.commit()
        except sqlite3.Error:
            from .._debug import log_swallowed_exc

            log_swallowed_exc("worlddb.checkpoint")

    def close(self) -> None:
        try:
            self._conn.commit()
        except sqlite3.Error:
            from .._debug import log_swallowed_exc

            log_swallowed_exc("worlddb.close_commit")
        try:
            self._conn.close()
        except sqlite3.Error:
            from .._debug import log_swallowed_exc

            log_swallowed_exc("worlddb.close")


def _timeline_type_to_event_type(t: str) -> str:
    """Map Timeline event types to WorldDB ``event_type`` values.

    Timeline uses a shorter taxonomy (``location``, ``combat``, ``quest``,
    ``npc``, ``item``, ``world_event``). Map each to the corresponding
    ``events.event_type`` CHECK-constraint value — quest/npc get collapsed
    to the most common subcase (offer / social) because v3 Timeline doesn't
    distinguish.
    """
    t = (t or "").lower()
    mapping = {
        "location": "travel",
        "combat": "combat",
        "quest": "quest_offer",
        "npc": "social",
        "item": "item",
        "world_event": "world_event",
    }
    return mapping.get(t, "world_event")
