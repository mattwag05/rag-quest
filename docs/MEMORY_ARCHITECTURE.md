# RAG-Quest Memory Architecture Redesign — v0.9 Specification

> **Purpose**: This document is the authoritative planning and implementation guide for
> replacing RAG-Quest's single-store LightRAG retrieval layer with a multi-store memory
> architecture. It is written for Claude Code (or any AI contributor) to use as the
> primary context when planning and implementing the changes across the codebase.
>
> **Project repo**: `~/Desktop/Projects/rag-quest/`
>
> **Prerequisite reading**: `CLAUDE.md` (codebase conventions, session gotchas, directory
> structure), `docs/CHANGELOG.md` (version history), `docs/ROADMAP.md` (release plan).

---

## 1. Problem Statement

RAG-Quest exists to solve a specific failure mode: conventional LLM chatbots can act as
D&D dungeon masters for a short time but lose world context and hallucinate events and
relationships as conversations grow. The project's core goal is **high-fidelity recall
across hundreds of turns** — the narrator on turn 347 must reference events from turn 47
as accurately as a human DM would.

The current architecture relies on LightRAG as a single retrieval backend for both
ingested lore documents and evolving game-state events. This has proven insufficient for
several reasons documented below.

### 1.1 LightRAG Limitations in the Game Context

| Limitation | Impact on RAG-Quest |
|---|---|
| **Entity extraction quality** | LightRAG's graph construction depends on LLM extraction. At 2–4B parameters (Gemma 4 E2B/E4B), extraction is unreliable — implicit relationships are missed, noise is over-extracted, and entity merges corrupt the graph silently. |
| **Static world assumption** | LightRAG was designed for document corpora, not continuously evolving game worlds. It has no native concept of temporal state — "NPC X trusted the player, then betrayed them, then was forgiven" is not representable. Each update appends; historical rollback or timeline queries are impossible. |
| **No typed schema** | LightRAG extracts a generic entity-relationship graph. Game worlds need typed nodes (`NPC`, `Location`, `Faction`, `Item`, `QuestState`). Without schema enforcement, retrieval precision suffers. |
| **Retrieval modes don't map to game queries** | The four retrieval modes (local, global, hybrid, naive) are designed for document Q&A. Game queries ("what enemies are in this dungeon?", "what does this NPC know about me?") don't map to any of them without heavy prompt engineering. |
| **Graph poisoning** | Creative, ambiguous narrator prose fed through `record_event()` compounds extraction errors over time. Bad entity merges and false relationships degrade narrative consistency silently. The `canonize` workflow mitigates this but adds manual overhead. |
| **Scaling cost** | Every inserted chunk triggers LLM extraction calls. Ingesting large lore documents is slow locally and expensive on cloud models. |

### 1.2 Architectural Symptoms in the Current Codebase

- **`WorldRAG.record_event()`** writes every turn's narrator output into LightRAG.
  This is the primary source of graph poisoning — 2B model extraction on creative prose.
- **`WorldRAG.query_world()`** is a single call that mixes lore retrieval with
  game-state retrieval. These have fundamentally different access patterns and cannot
  be tuned independently.
- **`StateParser`** does heuristic regex extraction to derive mechanical state changes
  from narrator text. It's unreliable (see `rag-quest-0gp` damage bug, healing
  false-positive bug) and is doing work that a typed schema would make unnecessary.
- **`GameState.to_dict()` / `from_dict()`** serialize the entire world to a flat JSON
  file. The `from_dict` hardening saga (`safe_enum`, `filter_init_kwargs`) exists
  because unstructured dicts are fragile. A typed SQLite schema eliminates this class
  of bug entirely.
- **The narrator's context-building code** in `narrator.py::process_action` builds
  messages from `NARRATOR_SYSTEM + world_context` where `world_context` is whatever
  LightRAG returns. There is no structured prioritization, budgeting, or
  multi-source composition.

---

## 2. Target Architecture

Replace the single LightRAG retrieval layer with a **four-store memory system** and a
**memory assembler** that composes narrator context from purpose-built stores.

```
                    ┌─────────────────────────┐
                    │   Memory Assembler       │
                    │   (narrator context      │
                    │    builder)              │
                    └────┬───┬───┬───┬────────┘
                         │   │   │   │
              ┌──────────┘   │   │   └──────────┐
              ▼              ▼   ▼              ▼
    ┌──────────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐
    │ Entity       │ │ Event  │ │ Lore   │ │ Narrative    │
    │ Registry     │ │ Log    │ │Library │ │ Moments      │
    │ (SQLite)     │ │(SQLite)│ │(Light- │ │ (Vector,     │
    │              │ │        │ │ RAG)   │ │  optional)   │
    │ NPCs, locs,  │ │ append │ │        │ │              │
    │ factions,    │ │ only,  │ │ read-  │ │ full narrator│
    │ items, quests│ │ per-   │ │ mostly │ │ prose for    │
    │ w/ current   │ │ turn   │ │        │ │ notable      │
    │ state +      │ │ struct │ │ user   │ │ moments,     │
    │ disposition  │ │ events │ │ lore,  │ │ semantic     │
    │ history      │ │        │ │ canon- │ │ similarity   │
    └──────────────┘ └────────┘ │ ized   │ │ retrieval    │
                                │ notes, │ └──────────────┘
                                │ module │
                                │ lore   │
                                └────────┘
```

### 2.1 Design Principles

1. **Each store is optimized for one retrieval pattern.** Structured lookups go to
   SQLite. Semantic prose retrieval goes to vector search. Authored lore goes to
   LightRAG. No store tries to do everything.
2. **The LLM is never in the extraction loop for game state.** Entity and event data
   is written structurally at event time (from `StateChange`), not extracted from prose
   later. This eliminates the 2B extraction quality problem.
3. **Temporal state is a first-class concept.** Every entity and relationship carries
   a `last_changed_turn` and history can be queried by turn range.
4. **Context budget is explicit.** The memory assembler allocates context window tokens
   across sources with tunable knobs, not a single opaque RAG query.
5. **LightRAG stays for what it's good at.** Ingesting human-authored prose documents
   (uploaded lore, canonized notes, module lore files) and making them semantically
   searchable.

---

## 3. Store Specifications

### 3.1 Entity Registry (SQLite)

**Purpose**: Source of truth for "who/what/where is X right now."

**Replaces**: `World.npcs_met`, `RelationshipManager.relationships`,
`RelationshipManager.factions`, portions of `Inventory`, `QuestLog`, `World.bases`.

#### Schema

```sql
-- Core entity table — every named thing in the game
CREATE TABLE entities (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type   TEXT NOT NULL CHECK(entity_type IN ('npc','location','faction','item','quest','base')),
    name          TEXT NOT NULL,
    canonical_name TEXT NOT NULL,  -- lowercase, stripped, for dedup/matching
    current_location TEXT,         -- where this entity currently is (NULL for locations/factions)
    status        TEXT DEFAULT 'active',  -- active, dead, destroyed, completed, etc.
    summary       TEXT,            -- 1-2 sentence description, updated as state changes
    created_at_turn INTEGER NOT NULL,
    last_seen_turn  INTEGER,
    metadata      TEXT,            -- JSON blob for type-specific attributes (race, class, HP for NPCs; weight for items; etc.)
    UNIQUE(entity_type, canonical_name)
);

-- Relationships between entities (NPC-to-player, NPC-to-faction, etc.)
CREATE TABLE relationships (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_a_id   INTEGER NOT NULL REFERENCES entities(id),
    entity_b_id   INTEGER NOT NULL REFERENCES entities(id),
    relationship_type TEXT NOT NULL,  -- 'disposition', 'member_of', 'located_at', 'owns', 'quest_giver', etc.
    value         REAL,              -- numeric value where applicable (disposition -1.0 to 1.0)
    last_changed_turn INTEGER NOT NULL,
    UNIQUE(entity_a_id, entity_b_id, relationship_type)
);

-- Disposition/relationship history for temporal queries
CREATE TABLE relationship_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    relationship_id INTEGER NOT NULL REFERENCES relationships(id),
    old_value     REAL,
    new_value     REAL,
    turn_number   INTEGER NOT NULL,
    cause         TEXT               -- "player confronted Gareth about cursed sword"
);

-- FTS5 virtual table for fast name/summary searching
CREATE VIRTUAL TABLE entities_fts USING fts5(
    name, summary, content=entities, content_rowid=id
);
```

#### Access Patterns

- **Name lookup**: `SELECT * FROM entities WHERE canonical_name LIKE ?` — when the player
  mentions "the blacksmith" or "Gareth"
- **Location query**: `SELECT * FROM entities WHERE current_location = ? AND entity_type = 'npc'`
  — "who is in Millhaven right now?"
- **Relationship query**: `SELECT r.*, e.name FROM relationships r JOIN entities e ON ...
  WHERE entity_a_id = ? ORDER BY last_changed_turn DESC` — "what is the player's standing
  with this NPC/faction?"
- **History query**: `SELECT * FROM relationship_history WHERE relationship_id = ?
  ORDER BY turn_number` — "how has this relationship changed over time?"

#### Data Source

Populated by the **state parser** output (`StateChange`) at the end of each turn. The
state parser already extracts NPC names, locations, items gained/lost, quest changes, and
relationship deltas. Instead of applying these to in-memory `GameState` Python objects,
write them to SQLite. The in-memory objects can remain as a cache/view over the database
for the current turn.

### 3.2 Event Log (SQLite)

**Purpose**: Append-only record of everything that happened, queryable by entity, location,
type, and turn range. This is the "journal" that enables 100-turn recall.

**Replaces**: `WorldRAG.record_event()`, and subsumes the `Timeline` system (which becomes
a view/UI layer over this table).

#### Schema

```sql
CREATE TABLE events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_number     INTEGER NOT NULL,
    event_type      TEXT NOT NULL CHECK(event_type IN (
        'combat','quest_offer','quest_complete','social','discovery',
        'trade','travel','world_event','item','death','level_up',
        'base_claim','module_unlock','module_complete','bookmark'
    )),
    primary_entity  TEXT,           -- canonical name of main entity involved
    location        TEXT,           -- where it happened
    summary         TEXT NOT NULL,  -- 1-2 sentence human-readable description
    player_input    TEXT,           -- what the player typed
    mechanical_changes TEXT,        -- JSON: {hp_delta, items_gained, items_lost, xp_gained, ...}
    secondary_entities TEXT,        -- JSON array of other entity canonical names involved
    is_notable      INTEGER DEFAULT 0  -- flag for narrative moments store ingestion
);

CREATE INDEX idx_events_turn ON events(turn_number);
CREATE INDEX idx_events_entity ON events(primary_entity);
CREATE INDEX idx_events_location ON events(location);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_notable ON events(is_notable) WHERE is_notable = 1;

-- FTS5 for semantic-ish searching over event summaries
CREATE VIRTUAL TABLE events_fts USING fts5(
    summary, player_input, content=events, content_rowid=id
);
```

#### Notability Criteria

An event is flagged `is_notable = 1` when any of these are true:
- Combat with outcome (victory, defeat, flee)
- Quest offered, completed, or failed
- NPC disposition changed by more than ±0.3 in a single turn
- First visit to a location
- Character level-up
- Base claimed
- Module unlocked or completed
- Player explicitly bookmarked it

Notable events are candidates for the Narrative Moments vector store (Store 4).

#### Event Summary Generation

The event summary is derived at write time, not retrieved later. Sources, in order
of preference:

1. **Mechanical derivation from `StateChange`**: If the state parser detects "player
   gained Sword of Flames from a chest", the summary is composed deterministically:
   `"Found Sword of Flames in the Ancient Vault."` No LLM call needed.
2. **Narrator-generated structured output** (future, see §6.2): The narrator includes
   a brief event summary in a structured response block.
3. **Truncated narrator prose** (fallback): First 1-2 sentences of the narrator's
   response, stripped of markdown.

### 3.3 Lore Library (LightRAG — existing, scoped down)

**Purpose**: Semantic retrieval over human-authored prose that describes the world's
history, geography, culture, and setting. **Read-mostly** — written at lore ingestion,
module loading, and canonization. Never written to during normal turn processing.

**Retains**: All current LightRAG ingestion paths:
- `WorldRAG.ingest_file()` for uploaded lore docs (PDF/txt/md)
- `WorldRAG.ingest_text(body, source="canonized")` for the canonize workflow
- Module lore ingestion via `load_modules()`

**Removes**: `WorldRAG.record_event()` — game events no longer flow into LightRAG.

**Query pattern**: `WorldRAG.query_world(question, context)` is retained but called only
by the memory assembler for lore-flavored context, not for game-state queries.

**No schema changes to LightRAG itself.** The `WorldRAG` wrapper class narrows its
API surface but the underlying LightRAG instance is unchanged.

### 3.4 Narrative Moments Store (Vector, optional)

**Purpose**: Semantic similarity retrieval over the narrator's actual prose output for
notable moments. This is the "emotional memory" layer — it answers "has something like
this happened before?" rather than "what are the facts about entity X?"

**Implementation options** (in order of recommendation):

1. **SQLite FTS5** (simplest, zero new dependencies): Use the `events_fts` table from
   Store 2, filtered to notable events. FTS5 is not true vector similarity but handles
   keyword/phrase matching well enough for a first pass. RAG-Quest already has a SQLite
   dependency via Store 1+2.

2. **ChromaDB** (better semantic matching, new dependency): Embed notable narrator
   prose passages using a small embedding model. ChromaDB runs embedded (no server)
   and persists to disk. More accurate similarity retrieval but adds a dependency and
   requires an embedding model.

3. **Defer entirely**: Ship v0.9 without this store. The entity registry + event log
   already provide dramatically better memory than the current system. Add semantic
   retrieval in v0.10 if needed.

**Recommendation**: Start with option 1 (FTS5 on the events table), validate that
the memory assembler produces good narrator context without true vector search, and
upgrade to option 2 later if semantic gaps appear in playtesting.

#### Data Ingested

For notable events only:
- Full narrator prose response (the `Narrator.last_response` text)
- Turn number, location, event type as metadata
- Player input as additional searchable text

---

## 4. Memory Assembler

**New module**: `rag_quest/knowledge/memory_assembler.py`

**Purpose**: Replaces `WorldRAG.query_world()` as the narrator's context source. Composes
a context window from all four stores, with explicit token budgeting.

### 4.1 Assembly Pipeline

On each turn, when the narrator needs context for the player's action:

```
Step 1: PARSE REFERENCES
   - Extract entity names from player input via keyword/name matching
     against the entity registry (simple SQL LIKE queries, no LLM)
   - Identify the current location

Step 2: PULL ENTITY SNAPSHOTS
   - For each referenced entity: current state, relationship to player,
     last interaction turn, 1-2 sentence summary
   - For the current location: description, known NPCs present, recent
     events at this location

Step 3: PULL RECENT EVENTS
   - Last N turns from the event log (N=5 for "fast" profile, N=10 for
     "balanced", N=15 for "deep")
   - Always included regardless of relevance — this is continuity

Step 4: PULL RELEVANT HISTORICAL EVENTS
   - Events involving any referenced entity, ordered by recency
   - Events at the current location, ordered by recency
   - Cap at a token budget (see §4.2)

Step 5: PULL NARRATIVE ECHOES (if Store 4 is active)
   - FTS5 or vector search over notable events using the player's input
   - Return top 2-3 matches with their narrator prose
   - Skip if they overlap with events already pulled in Steps 3-4

Step 6: PULL LORE CONTEXT
   - Query LightRAG for lore relevant to the current location and
     referenced entities
   - This is the only step that touches LightRAG

Step 7: ASSEMBLE AND BUDGET
   - Compose all retrieved content into a structured context string
   - Enforce a total token budget based on the model's context window
   - Priority order for truncation (cut from bottom first):
     1. Lore context (can be summarized or dropped)
     2. Narrative echoes
     3. Historical events (keep most recent, drop oldest)
     4. Entity snapshots (never drop referenced entities)
     5. Recent events (never drop)
     6. Current state (never drop)
```

### 4.2 Token Budget Allocation

Default allocation for an 8K context window model (tunable per RAG profile):

| Section | Tokens | Notes |
|---|---|---|
| System prompt | ~1,000 | `NARRATOR_SYSTEM` prompt |
| Current game state | ~800 | Character stats, location, inventory summary, active quests |
| Recent events (last N turns) | ~1,000 | Continuity — always present |
| Entity snapshots | ~1,500 | Referenced NPCs, locations, factions with disposition and history |
| Relevant historical events | ~1,000 | Events involving referenced entities from any turn |
| Narrative echoes | ~500 | Semantic matches from notable moments |
| Lore context | ~800 | LightRAG query results for world flavor |
| Conversation history | ~400 | Last 2-4 exchange pairs (reduced from current 6) |
| Player action + response space | ~1,000 | The actual input and room for the model to respond |

**RAG profile overrides**:
- **fast**: Smaller budgets for history and lore, larger for response space. 5 recent turns.
- **balanced**: Default allocation above. 10 recent turns.
- **deep**: Larger budgets for history, lore, and narrative echoes. 15 recent turns.

### 4.3 Context Output Format

The assembled context is injected into the narrator's system prompt as a structured
block (not raw prose dump):

```
## CURRENT STATE
Location: The Iron Forge, Millhaven
Time: Day 47, Evening
HP: 22/30 | Level: 4 | Gold: 150

## ENTITIES PRESENT
- Gareth (blacksmith, disposition: hostile -0.5)
  Last interaction: Turn 84 — player confronted him about the cursed sword.
  He claimed ignorance. Member of the Iron Guild.
- Mira (tavern keeper, disposition: friendly +0.6)
  Gave you the quest "Find the Lost Shipment" on turn 102.

## RECENT EVENTS (turns 343-347)
- T345: Defeated a pack of wolves on the mountain pass. Gained 50 XP.
- T346: Arrived in Millhaven. Visited the market.
- T347: (current turn)

## RELEVANT HISTORY
- T47: Purchased a longsword from Gareth for 30 gold.
- T83: Discovered the sword was cursed after it drained 5 HP during combat.
- T84: Confronted Gareth. He denied knowledge of the curse. Relationship dropped.
- T112: Destroyed the cursed sword at the Temple of Purification.

## WORLD LORE
Millhaven is a trading town at the confluence of the Mill and Haven rivers.
The Iron Guild controls most metalwork in the region and has a reputation
for quality but questionable sourcing of materials...

## PLAYER ACTION
"I walk into Gareth's forge and slam the remains of the cursed sword on his anvil."
```

This format gives the narrator structured facts to work with. Even a 2B model can
produce a coherent, contextually accurate response from this — it doesn't need to
"remember" anything, just narrate based on the provided context.

---

## 5. Migration Plan

### 5.1 Phasing Strategy

The migration is structured so that **every phase ships a working game**. No big-bang
rewrite. Each phase adds the new system alongside the old one, validates it, then
cuts over.

#### Phase 1: Add SQLite Stores (additive, nothing breaks)

**Scope**: Create the SQLite database, entity registry, and event log. Write to them
alongside the existing `GameState` in-memory objects and JSON saves.

**Files to create**:
- `rag_quest/knowledge/world_db.py` — `WorldDB` class wrapping SQLite connection,
  schema creation, and typed query methods
- `rag_quest/knowledge/memory_assembler.py` — `MemoryAssembler` class (initially
  a thin wrapper that just queries the new stores; does NOT replace
  `WorldRAG.query_world()` yet)

**Files to modify**:
- `rag_quest/engine/game.py` — Initialize `WorldDB` alongside `WorldRAG` at game
  start. Pass it to the state-application layer.
- `rag_quest/engine/narrator.py` — After `StateChange` is applied, also write
  entities and events to `WorldDB`.
- `rag_quest/engine/saves.py` — SQLite DB file lives alongside the JSON save:
  `~/.local/share/rag-quest/saves/{world_name}.db`

**Validation**: Run the game normally. Inspect the SQLite database after 20+ turns to
verify entity and event data is being recorded correctly. JSON saves still work as
before. `WorldRAG` is untouched.

**Save format**: Bump to v4. Old saves load with an empty SQLite DB that gets
populated from the existing `GameState` data (one-time migration in `from_dict`).

#### Phase 2: Build the Memory Assembler

**Scope**: Build the full memory assembler pipeline. Wire it into the narrator as an
alternative context source. Run both `WorldRAG.query_world()` and the memory assembler
in parallel during development; log both outputs for comparison.

**Files to create/modify**:
- `rag_quest/knowledge/memory_assembler.py` — Full implementation of §4 pipeline
- `rag_quest/engine/narrator.py` — `process_action` and `stream_action` call the
  memory assembler instead of `WorldRAG.query_world()` for game-state context.
  LightRAG is still queried, but only for lore (via the assembler's Step 6).

**Key decision point**: After playtesting with the assembler, compare narrator output
quality against the old LightRAG-only path. If the assembler produces better context
(it should), proceed to Phase 3.

#### Phase 3: Remove `record_event()` and Cut Over — ✅ complete in v0.9.1

**Scope**: Stop writing game events to LightRAG. The assembler is the sole context
source. LightRAG is scoped to lore-only.

**Discovery during v0.9.1 work**: Phase 3 was already de-facto achieved as a
side-effect of Phase 1. Wiring `engine/turn.py::_shadow_write_to_world_db`
immediately made `WorldRAG.record_event` a zero-caller method — no narrator
code path ever invoked it in v0.9.0. The cutover work reduced to:

1. Delete the dead `WorldRAG.record_event` method from
   `rag_quest/knowledge/world_rag.py`.
2. Flip `memory.assembler_enabled` to `True` in `ConfigManager.DEFAULT_CONFIG`
   so the `MemoryAssembler` read path is the default.
3. Clean up stale doc references (this doc, `AGENTS.md`, `docs/ARCHITECTURE.md`).

**Not in Phase 3** (intentionally deferred):

- `rag_quest/engine/timeline.py` still owns its own in-memory list and its own
  translator from `StateChange` → `TimelineEvent`. Pointing it at
  `state_event_mapping` + `WorldDB.events` is a Phase 3.1 cleanup (beads
  `rag-quest-50j` or a successor). Current duplication is tolerable because
  timeline writes are cheap and the translator output shapes differ slightly.
- Step 5 narrative echoes via FTS5 on `events.summary` remain on the
  assembler TODO list (`rag-quest-50j`) for v0.9.2.

#### Phase 4: SQLite as Save Format (optional, high-value)

**Scope**: Replace the JSON save file with the SQLite database as the primary save
format. `GameState.to_dict()` / `from_dict()` remain for the web API but serialize
from database queries rather than in-memory object trees.

**Impact**: Eliminates the entire `from_dict` hardening problem. Typed columns mean
corrupted data is caught at write time (via CHECK constraints and foreign keys), not
at load time via defensive parsing. `.rqworld` export bundles the SQLite DB file.

**This phase is optional for v0.9.** The JSON save can coexist with the SQLite DB
indefinitely — JSON for portability and backward compatibility, SQLite for memory
queries. Phase 4 is a v1.0 candidate.

### 5.2 Backward Compatibility

**v3 saves loading in v4**: When a v3 (or earlier) save is loaded and no SQLite DB
exists, the game performs a one-time migration:

1. Create the SQLite database with empty schema.
2. Walk `GameState` in-memory objects and populate the entity registry:
   - `World.npcs_met` → entity rows with `type='npc'`
   - `RelationshipManager.relationships` → `relationships` rows
   - `RelationshipManager.factions` → entity rows with `type='faction'`
   - `Inventory.items` → entity rows with `type='item'`
   - `QuestLog.quests` → entity rows with `type='quest'`
   - `World.bases` → entity rows with `type='base'`
   - `World.visited_locations` → entity rows with `type='location'`
3. Walk `Timeline.events` and populate the event log.
4. Mark migration complete in the database metadata.

This is lossy (no relationship history, no event details beyond what Timeline captured)
but provides a working baseline for the memory assembler. New turns generate full
event data going forward.

---

## 6. Future Evolution

### 6.1 Structured Narrator Output

The state parser is currently doing heuristic regex extraction to derive `StateChange`
from narrator prose. This is fragile (see the damage false-positive bug `rag-quest-0gp`,
healing false-positive bug, and the ongoing pattern of parser fixes in the changelog).

With the SQLite schema in place, there's a natural evolution: **have the narrator
output structured state changes explicitly** alongside its prose response.

This can be done via a **tool-use / function-calling pattern** in the system prompt:

```
When narrating, also output a JSON block at the end of your response describing
any mechanical changes:
```json
{
  "location_changed": "The Iron Forge",
  "damage_taken": 0,
  "damage_dealt": 5,
  "items_gained": [],
  "items_lost": [],
  "npcs_met": ["Gareth"],
  "quest_updates": [],
  "event_summary": "Player confronted Gareth about the cursed sword."
}
```

Even 2B models can produce structured JSON when the schema is clearly specified in
the system prompt. The state parser becomes a **fallback** for when structured output
is malformed or missing, rather than the primary mechanism.

**This is not part of the v0.9 scope.** It's the natural next step after the memory
architecture is stable. The SQLite schema provides the validation layer that makes
structured output trustworthy — you can CHECK-constraint the JSON against the entity
registry.

### 6.2 Embedding-Based Narrative Moments

If FTS5 proves insufficient for the "has something like this happened before?" retrieval
pattern, upgrade to ChromaDB or a similar embedded vector store:

- Embed notable event narrator prose using a small embedding model (e.g., `nomic-embed-text`
  via Ollama, or `all-MiniLM-L6-v2` via sentence-transformers)
- Store embeddings alongside the event record, keyed by event ID
- Query with the player's current input embedded through the same model
- Return top-k semantically similar historical moments

This adds a dependency and an embedding model requirement but dramatically improves
the "emotional memory" retrieval quality. Defer until playtesting reveals specific
gaps in the FTS5 approach.

---

## 7. Implementation Notes

### 7.1 File Locations and Conventions

**New files**:
- `rag_quest/knowledge/world_db.py` — `WorldDB` class
- `rag_quest/knowledge/memory_assembler.py` — `MemoryAssembler` class

**SQLite DB location**: `~/.local/share/rag-quest/saves/{world_name}.db`
(alongside the existing `{world_name}.json` save file)

**Follow existing conventions**:
- Synchronous architecture (no async). SQLite is naturally sync.
- `log_swallowed_exc()` for any non-critical exception handling
- Rich for terminal output, zero tracebacks to users
- `pyflakes rag_quest/` must stay exit 0
- `black` + `isort` auto-formatting via PostToolUse hook
- Update `docs/CHANGELOG.md` in the same commit as code changes
- Bump `rag_quest/__version__` AND `pyproject.toml` version together

### 7.2 Testing Strategy

- **Unit tests** for `WorldDB`: schema creation, entity CRUD, event insertion,
  relationship history, FTS5 queries, migration from v3 saves
- **Unit tests** for `MemoryAssembler`: context assembly from mock data, token
  budgeting, entity reference parsing, fallback behavior when stores are empty
- **Integration tests**: 20+ turn game simulation verifying that:
  - Entities mentioned on turn N are retrievable on turn N+100
  - Relationship changes are tracked with turn-level granularity
  - Event queries by entity, location, and type return correct results
  - The assembled narrator context includes relevant historical events
- **Regression tests**: Existing test suite must continue passing. The new stores
  are additive in Phase 1-2; no existing behavior changes.

### 7.3 Dependencies

**No new runtime dependencies for Phase 1-3.** SQLite is in Python's stdlib (`sqlite3`).
FTS5 is compiled into the default SQLite on macOS and most Linux distributions.

**Phase 4 (optional)** may benefit from `apsw` for advanced SQLite features, but
stdlib `sqlite3` is sufficient for all described functionality.

**Narrative Moments vector store (§6.2)** would add `chromadb` or
`sentence-transformers` as optional dependencies if/when implemented.

### 7.4 Interaction with Existing Subsystems

| Subsystem | Phase 1-2 (coexistence) | Phase 3 (cutover) |
|---|---|---|
| `WorldRAG` | Phase 1-2: defined `record_event()` but nothing called it post-Phase-1. | ✅ v0.9.1: `record_event()` deleted. Scoped to lore ingestion + lore queries only. |
| `GameState` | Unchanged. Still the in-memory authority. SQLite writes shadow it. | Still the in-memory authority, but populated from SQLite on load. |
| `StateParser` | Unchanged. Its `StateChange` output feeds both `GameState` and `WorldDB`. | Unchanged in Phase 3. Future: fallback for structured narrator output (§6.1). |
| `Timeline` | Unchanged. Maintains its own in-memory list. | Still owns its own list in v0.9.1 — Timeline cutover deferred to a v0.9.2 cleanup. |
| `Notetaker` | Unchanged. Reads from `Timeline` and conversation history. | Unchanged in v0.9.1. Will follow Timeline's cutover. |
| `Narrator` | Phase 2: uses `MemoryAssembler` when wired. | ✅ v0.9.1: `MemoryAssembler` is the default context source. `record_event()` call removed. |
| `Canonize` | Unchanged. Writes to LightRAG via `WorldRAG.ingest_text()`. | Unchanged. This is the correct path — canonized notes are lore. |
| `Saves` | JSON save continues. SQLite DB is an additional file. | JSON save continues (or replaced in Phase 4). |
| `Web endpoints` | Unchanged. `GameState.to_dict()` still works. | Unchanged unless Phase 4 replaces JSON saves. |
| `ModuleRegistry` | Unchanged. Module lore ingested to LightRAG. Status in `GameState`. | Unchanged. Module status could move to SQLite in Phase 4. |

### 7.5 `WorldDB` API Surface (Draft)

```python
class WorldDB:
    """SQLite-backed world state and event store."""

    def __init__(self, db_path: str):
        """Open or create the database. Run schema migrations."""

    # --- Entity Registry ---
    def upsert_entity(self, entity_type: str, name: str, *,
                      location: str = None, status: str = "active",
                      summary: str = None, turn: int, metadata: dict = None) -> int:
        """Insert or update an entity. Returns entity ID."""

    def get_entity(self, name: str, entity_type: str = None) -> dict | None:
        """Look up an entity by name (fuzzy match via canonical_name)."""

    def get_entities_at(self, location: str, entity_type: str = None) -> list[dict]:
        """All entities at a given location."""

    def search_entities(self, query: str, limit: int = 10) -> list[dict]:
        """FTS5 search over entity names and summaries."""

    # --- Relationships ---
    def set_relationship(self, entity_a: str, entity_b: str,
                         rel_type: str, value: float, turn: int,
                         cause: str = None) -> None:
        """Set or update a relationship. Records history if value changed."""

    def get_relationship(self, entity_a: str, entity_b: str,
                         rel_type: str = None) -> dict | None:
        """Get current relationship between two entities."""

    def get_relationship_history(self, entity_a: str, entity_b: str) -> list[dict]:
        """Full disposition/relationship history between two entities."""

    # --- Event Log ---
    def record_event(self, turn: int, event_type: str, *,
                     primary_entity: str = None, location: str = None,
                     summary: str, player_input: str = None,
                     mechanical_changes: dict = None,
                     secondary_entities: list[str] = None,
                     is_notable: bool = False) -> int:
        """Append an event to the log. Returns event ID."""

    def get_recent_events(self, n: int = 10) -> list[dict]:
        """Last N events by turn number."""

    def get_events_for_entity(self, entity_name: str,
                              limit: int = 20) -> list[dict]:
        """Events involving a specific entity."""

    def get_events_at_location(self, location: str,
                               limit: int = 20) -> list[dict]:
        """Events at a specific location."""

    def get_events_by_type(self, event_type: str,
                           limit: int = 20) -> list[dict]:
        """Events of a specific type."""

    def search_events(self, query: str, limit: int = 10) -> list[dict]:
        """FTS5 search over event summaries."""

    # --- Migration ---
    def migrate_from_game_state(self, game_state) -> None:
        """One-time migration from v3 GameState to populate the database."""

    # --- Lifecycle ---
    def close(self) -> None:
        """Close the database connection."""
```

### 7.6 `MemoryAssembler` API Surface (Draft)

```python
class MemoryAssembler:
    """Composes narrator context from multiple memory stores."""

    def __init__(self, world_db: WorldDB, world_rag: WorldRAG,
                 rag_profile: str = "balanced"):
        """Initialize with store references and profile."""

    def assemble_context(self, player_input: str,
                         game_state,  # for current stats/location/inventory
                         turn_number: int) -> str:
        """
        Build the full narrator context string.

        Returns a structured text block (see §4.3 format) ready for
        injection into the narrator's system prompt.
        """

    def _parse_entity_references(self, player_input: str) -> list[str]:
        """Extract entity names from player input via DB lookup."""

    def _pull_entity_snapshots(self, entity_names: list[str],
                                current_location: str) -> str:
        """Format entity state for context."""

    def _pull_recent_events(self, n: int) -> str:
        """Format last N events for context."""

    def _pull_historical_events(self, entity_names: list[str],
                                 location: str, budget_tokens: int) -> str:
        """Format relevant historical events within token budget."""

    def _pull_narrative_echoes(self, player_input: str,
                                budget_tokens: int) -> str:
        """FTS5/vector search for similar past moments."""

    def _pull_lore_context(self, entity_names: list[str],
                            location: str, budget_tokens: int) -> str:
        """Query LightRAG for world lore."""

    def _budget_and_compose(self, sections: dict[str, str],
                             max_tokens: int) -> str:
        """Enforce total token budget with priority-based truncation."""
```

---

## 8. Success Criteria

The memory architecture redesign is successful when:

1. **100-turn recall**: An NPC mentioned on turn 20 and not seen again until turn 120
   is correctly described with their relationship history, location, and prior
   interactions in the narrator's response on turn 120.

2. **Zero graph poisoning**: No game-generated content flows through LLM extraction
   pipelines. Entity and event data is written structurally from `StateChange` output.

3. **Temporal queries work**: "What happened with Gareth?" returns a chronologically
   ordered history regardless of how many turns have passed.

4. **Context quality improves**: Side-by-side comparison of narrator responses with
   old `query_world()` context vs. new assembled context shows more relevant,
   accurate, and specific contextual grounding.

5. **No regression**: All existing tests pass. Game plays identically for the end user.
   New features are additive.

6. **Performance**: SQLite queries complete in <10ms. Memory assembler completes full
   context assembly in <100ms. No perceptible latency increase per turn.

---

## 9. Open Questions

- **Token counting**: The memory assembler needs to estimate token counts for budget
  enforcement. Options: use `len(text.split())` as a rough proxy (fast, inaccurate),
  or use a tokenizer library (accurate, adds dependency). Recommend starting with
  word-count proxy (1 word ≈ 1.3 tokens) and refining later.

- **Entity deduplication**: The state parser extracts names like "the blacksmith",
  "Gareth", "Gareth the blacksmith". The entity registry needs canonical name matching
  to avoid duplicate entries. Strategy: normalize to lowercase, strip articles and
  titles, and use FTS5 for fuzzy matching on insert. Exact dedup logic needs design.

- **Multi-session continuity**: If a player loads a save from 50 turns ago and
  continues, the event log has a gap. This is fine — the log records what happened,
  not what didn't. But the memory assembler should handle sparse event logs gracefully.

- **Web API implications**: The web endpoints (`/session/{id}/state`,
  `/session/{id}/turn`) currently return `GameState.to_dict()`. Phase 1-3 don't
  change this. Phase 4 would need new endpoints or a compatibility shim.

---

*Last updated: April 13, 2026*
*For: Claude Code and AI contributors working on RAG-Quest v0.9*
