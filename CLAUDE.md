# CLAUDE.md — RAG-Quest AI Developer Guide

Guide for AI assistants working on RAG-Quest. Authoritative version lives in `rag_quest/__init__.py` — do not hardcode version strings elsewhere; import `rag_quest.__version__`.

## Project Overview

**RAG-Quest** is an AI-powered D&D-style text RPG that uses LightRAG to eliminate hallucinations in narrative generation.

**Core Design Philosophy**: LightRAG does the heavy lifting. The LLM narrator is intentionally kept small (Gemma 4 E2B/E4B, 2-4B parameters) because it doesn't memorize the world. Instead, LightRAG's dual-level retrieval (entity matching + vector similarity) injects precise knowledge per query. This architecture enables RAG-Quest to run on consumer hardware while producing narrative quality comparable to much larger models.

**Status**: Production-ready. All core systems verified and working.

Per-version history lives in [`docs/CHANGELOG.md`](docs/CHANGELOG.md). For anything not
captured there, `git log --oneline` is the source of truth.

Forward-looking version plans live in [`docs/ROADMAP.md`](docs/ROADMAP.md). The editable
"Future Roadmap" section holds pre-development v0.9+ slots — update it when scoping new
features, not CHANGELOG.md (CHANGELOG is for shipped work).

### Updating the changelog

**When making user-visible changes, update `docs/CHANGELOG.md` in the same commit as the code.**
Applies to: features, bug fixes, breaking changes, UX/CLI changes, new commands, provider
behavior changes, save-format changes. Skip for: internal refactors, test-only changes,
doc tweaks, formatting.

- Add entries under the `## [Unreleased]` heading (create it if missing), grouped as
  `### Added` / `### Changed` / `### Fixed` / `### Removed`.
- Write entries from the user's perspective — what changed for them, not what you edited.
- When bumping `rag_quest.__version__`, rename `[Unreleased]` to the new version and start
  a fresh `[Unreleased]` block above it.
- One line per change; link to the relevant file or command when helpful.

## Technology Stack

- **Python 3.11+** — Core language
- **LightRAG** — Knowledge graph backend (the cornerstone)
- **httpx** — Async HTTP (used synchronously via ThreadPoolExecutor)
- **Rich** — Terminal UI and formatting
- **PyMuPDF** — PDF text extraction
- **pytest** — Testing framework

## Directory Structure

```
rag-quest/
├── rag_quest/                    # Main package
│   ├── __init__.py              # Single source of truth for __version__
│   ├── __main__.py              # Entry point (python -m rag_quest)
│   ├── startup.py               # Welcome screen & Ollama detection
│   ├── config.py                # ConfigManager & setup wizard
│   ├── ui.py                    # Terminal UI, help, commands
│   ├── tutorial.py              # Interactive 9-step TUI tutorial
│   ├── llm/                     # LLM provider implementations
│   │   ├── __init__.py
│   │   ├── base.py              # BaseLLMProvider
│   │   ├── ollama_provider.py   # Local Ollama (recommended)
│   │   ├── openai_provider.py   # OpenAI integration
│   │   ├── openrouter_provider.py # OpenRouter integration
│   │   └── _sse.py              # stream_openai_chat — OpenAI-compatible SSE parser
│   ├── knowledge/               # LightRAG integration
│   │   ├── __init__.py
│   │   ├── world_rag.py         # WorldRAG wrapper
│   │   ├── chunking.py          # RAG profile configs
│   │   └── ingest.py            # PDF/txt/md ingestion
│   ├── engine/                  # Game logic & state
│   │   ├── __init__.py
│   │   ├── character.py         # Player character (6 attributes, classes, races)
│   │   ├── world.py             # World state
│   │   ├── inventory.py         # Item management
│   │   ├── quests.py            # Quest chains
│   │   ├── party.py             # Multi-character parties
│   │   ├── relationships.py     # NPC relationships & factions
│   │   ├── events.py            # Dynamic world events
│   │   ├── combat.py            # D&D combat with dice rolls
│   │   ├── encounters.py        # Enemy generation & loot
│   │   ├── narrator.py          # AI narrator & LLM integration
│   │   ├── state_parser.py      # Extracts mechanical state changes from narrator text
│   │   ├── tts.py               # Text-to-speech support
│   │   ├── game.py              # Main game loop & commands
│   │   ├── achievements.py      # 11 achievements
│   │   ├── dungeon.py           # Procedural dungeon generation
│   │   ├── timeline.py          # v0.6: TimelineEvent / Bookmark / Timeline container
│   │   ├── notetaker.py         # v0.6: AI Notetaker — incremental JSON summary + canonize
│   │   ├── encyclopedia.py      # v0.6: LoreEncyclopedia — browse-then-RAG-query
│   │   ├── bases.py             # v0.7: Base entity — hub stronghold with storage/services
│   │   ├── turn.py              # v0.8: shared CLI/web turn helpers
│   │   ├── _debug.py            # log_swallowed_exc
│   │   ├── _serialization.py    # safe_enum / filter_init_kwargs
│   │   └── saves.py             # Save/load & serialization
│   ├── multiplayer/             # Local multiplayer
│   │   ├── __init__.py
│   │   ├── session.py           # MultiplayerSession
│   │   ├── trading.py           # Item trading between players
│   │   └── sync.py              # State synchronization
│   ├── worlds/                  # World sharing
│   │   ├── __init__.py
│   │   ├── exporter.py          # Export to .rqworld
│   │   ├── importer.py          # Import from .rqworld
│   │   └── templates.py         # Built-in templates
│   ├── web/                     # v0.8: optional FastAPI wrapper
│   │   ├── app.py               # FastAPI app, SessionStore, run()
│   │   ├── sessions.py          # load_session_from_slot
│   │   └── static/              # Vanilla-JS browser client
│   │       └── index.html
│   ├── prompts/                 # System prompts
│   │   ├── __init__.py
│   │   └── templates.py         # Prompt templates
│   └── saves/                   # Save slot storage
├── lore/                        # Example lore files
│   └── EXAMPLE_WORLD.md
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md
│   ├── CHANGELOG.md             # Per-version history
│   ├── QUICKSTART.md
│   ├── CONTRIBUTING.md
│   ├── ROADMAP.md
├── pyproject.toml               # Project config
├── RAG-Quest_User_Guide.docx    # Downloadable user guide (root, not in docs/)
├── README.md                    # User-facing docs
├── AGENTS.md                    # LLM provider guide
├── LICENSE                      # MIT License
└── CLAUDE.md                    # This file
```

## Core Classes & Patterns

### Startup & Welcome (startup.py)

**print_welcome_screen()** — Displays friendly ASCII art banner, version, and intro message.

**check_ollama_health()** — Detects if Ollama is running on localhost:11434.

**get_available_ollama_models()** — Lists available models in Ollama.

**print_ollama_setup_needed()** — Displays helpful setup instructions if Ollama isn't running.

### Configuration Management (config.py)

**ConfigManager** — Persistent configuration with fallback to environment variables.

```python
class ConfigManager:
    def get(self, key: str) -> Any:
        # e.g., "llm.provider", "rag.profile"
        return self._config[key]
    
    def set(self, key: str, value: Any) -> None:
        self._config[key] = value
        self._save()  # Immediately persist to file
```

**get_config()** — Returns singleton ConfigManager instance.

**setup_first_run()** — Interactive setup wizard with three start modes:
1. **Fresh Adventure** — Blank world, custom name
2. **Quick Start** — Choose from 4 templates
3. **Upload Lore** — Ingest custom files

Config location: `~/.config/rag-quest/config.json`

### Game State

**GameState** — Central state container: `character`, `world`, `inventory`, `quest_log`, `party`, `relationships`, `conversation_history`. Fully serializable via `to_dict()` / `from_dict()`. Saves are JSON at: `~/.local/share/rag-quest/saves/{world_name}.json`

### Character System

**Character** — Player character with:
- Attributes: name, race, class, level, HP, XP
- Six D&D attributes: STR, DEX, CON, INT, WIS, CHA
- Location, inventory references, status effects
- Methods: `take_damage()`, `heal()`, `level_up()`, `get_status()`

**Race & Class** — 5 races (Human, Elf, Dwarf, Orc, Halfling) and 5 classes (Fighter, Rogue, Mage, Cleric, Ranger) with stat bonuses.

### World System

**World** — World state container:
- name, setting, tone, time_of_day, weather
- visited_locations, npcs_met
- recent_events (last 5 for narrative context)
- Methods: `advance_time()`, `add_visited_location()`, `get_context()`

**Events** — Dynamic world events with consequences, recorded in RAG knowledge graph.

### Combat System

**CombatEncounter** — Handles D&D combat:
- Dice rolling (d4-d20, attack rolls vs AC)
- Initiative calculation
- Damage calculation with critical hits
- Turn-based combat flow

**Enemy** — NPC/monster with HP, attack, defense, loot drops.

**Encounter Generation** — Location-based enemy tables, difficulty scaling, loot tables.

### Quest System

**Quest** — Quest object with:
- title, description, objectives
- status (pending, active, completed)
- reward_xp, reward_items
- Methods: `check_objectives()`, `complete()`

**QuestLog** — Maintains active and completed quests, methods: `add_quest()`, `complete_quest()`, `get_active_quests()`

### NPC & Relationship System

**RelationshipManager** — Tracks NPC dispositions. `add_npc(name, role, disposition)` (−1.0 enemy → +1.0 ally). `change_disposition(name, delta)` adjusts trust.

**Faction System** — Faction reputation tracking with methods: `create_faction()`, `change_reputation()`, `get_reputation()`.

### Narrator (narrator.py)

**Narrator** — Lightweight AI narrator that:
1. Receives player action (natural language)
2. Queries RAG for relevant world context
3. Builds LLM prompt with game state + RAG context + conversation history
4. Calls LLM provider (synchronous)
5. Records event back to RAG
6. Returns narrative response

**State Parser (`engine/state_parser.py`)** — Post-processes narrator output into a `StateChange`:
location moves, damage taken / healed, items gained/lost, quests offered/completed, NPCs
met/recruited, relationship deltas, world events. The game loop applies the `StateChange` to
`GameState` after each turn so inventory/quest/location stay in sync with the narrative.

### LLM Providers (llm/)

All providers inherit from **BaseLLMProvider**:

```python
class BaseLLMProvider(ABC):
    def complete(self,
                messages: list[dict],
                temperature: float = None,
                max_tokens: int = None,
                **kwargs) -> str:  # SYNCHRONOUS
        """Call LLM and return response."""
```

**Implementations**:
- **OllamaProvider** — Local inference via `http://localhost:11434/api/generate`
- **OpenAIProvider** — OpenAI API, models like gpt-4, gpt-3.5-turbo
- **OpenRouterProvider** — OpenRouter.ai, 100+ models

All now **synchronous** (were async before v0.5.0).

**Streaming (v0.8)** — `BaseLLMProvider.stream_complete(messages)` returns
an iterator of text chunks. The base class has a safe fallback that
yields a single chunk from `.complete()`, so every provider can be
streamed without a type check. Real streaming is implemented in:
- `OllamaProvider.stream_complete` — parses Ollama's line-delimited JSON
  (`"stream": True`), with the same thinking-model fallback as `.complete()`.
- `OpenAIProvider` / `OpenRouterProvider` — share the new
  `rag_quest.llm._sse.stream_openai_chat` helper which parses
  OpenAI-compatible SSE (`data: { ... }` events, `data: [DONE]` sentinel).

The narrator exposes streaming via `Narrator.stream_action(player_input)`
which yields chunks and populates `last_response` / `last_change` /
`conversation_history` after the generator is exhausted. The state
parser runs on the joined text so mechanics stay deterministic
regardless of which provider yielded the tokens.

`ui.stream_narrator_response(iterator)` wraps a Rich `Live` panel update
loop — `run_game` uses it instead of `process_action` + `print_narrator_response`
so players see prose render live.

**LLM Provider Gotchas** (ran into these, don't repeat them):
- **Ollama message format** — Narrator must send `messages=[{"role": "user", "content": ...}]`,
  not a bare `prompt=...`. Bare prompts return HTTP 400 from Ollama's `/api/chat` endpoint.
- **Thinking models (Qwen 3.5, DeepSeek-R1)** — `OllamaProvider` strips `<think>...</think>`
  blocks from the response before returning. Don't re-emit them in the UI.
- **Version strings** — Always import from `rag_quest.__version__`. The ASCII banner, `--version`
  output, and any user-visible version must come from the package, never hardcoded.

### Web stack (v0.8, `rag_quest/web/`)

Optional FastAPI wrapper around the engine. The base install stays slim
— `pip install -e '.[web]'` pulls in `fastapi` + `uvicorn`. Everything
else is vanilla stdlib.

**Layout**:
- `rag_quest/web/app.py` — `_build_app()` returns a configured
  `FastAPI` instance; module-level `app` is either that instance or
  `None` when the extras are missing. `SessionStore` (module dataclass)
  holds loaded `GameState` objects keyed by save name and closes the
  previous session's `WorldRAG`/`llm` when re-loading the same slot.
  `run(host, port)` launches uvicorn.
- `rag_quest/web/sessions.py` — encapsulates the
  "read save → build provider → build WorldRAG → build Narrator →
  hydrate GameState" chain behind `load_session_from_slot(slot_id)`,
  raising `SessionLoadError` on any failure.
- `rag_quest/web/static/` — vanilla-JS single-page client
  (`index.html` + `README.md`). Mounted at `/` via
  `StaticFiles(html=True)` **after** every API route so it can't
  shadow them. Server-supplied text renders through
  `textContent`/`createElement` only — `innerHTML` is never used
  because LLM output and save-file data flow through the page.

**Endpoints**:
- `GET /healthz` — health + version
- `GET /saves` — list save slots (delegates to `sessions.list_save_slots`)
- `POST /session/load` — hydrate a slot and park it in `SessionStore`
- `GET /session/{id}/state` — `GameState.to_dict()` dump
- `POST /session/{id}/turn` — non-streaming turn via `advance_one_turn`
- `GET /session/{id}/turn/stream` — SSE streaming turn (GET + query
  string because browser `EventSource` only speaks GET)

**CLI turn-loop parity (v0.8, `rag_quest/engine/turn.py`)** — The pure
mechanics of a turn live in three helpers that both the CLI loop and
the web endpoints call:

- `collect_pre_turn_effects(game_state) -> PreTurnEffects`: increments
  `turn_number`, runs `events.check_for_events(event_chance=0.08)`,
  `events.expire_events()`, and `party.check_loyalty_departures()`.
  Each subsystem is individually wrapped in `log_swallowed_exc` so
  one failure can't cascade.
- `collect_post_turn_effects(game_state, player_input) -> PostTurnEffects`:
  reads `narrator.last_change`, feeds it to
  `timeline.record_from_state_change`, runs
  `world.module_registry.reevaluate(quest_log)` and
  `achievements.check_achievements(game_state.to_dict())`.
- `advance_one_turn(game_state, player_input) -> TurnResult`: non-
  streaming flow (`pre → narrator.process_action → post`) used by
  `POST /turn`. Streaming callers (CLI `run_game` and
  `GET /turn/stream`) compose pre + `Narrator.stream_action` + post
  manually because streaming owns the narrator call.

**Contract**: these helpers do **not** import Rich and do **not**
print. All UI output lives in the `run_game` wrapper. Any new per-turn
subsystem goes here so CLI and web stay in sync automatically.

**SSE wire format**:

```jsonc
// pre_turn event (always first)
{"type":"pre_turn","new_event":{"name","description"}|null,
 "expired_events":[...],"departed_party_members":[...]}
// chunk events (narrator tokens)
{"type":"chunk","text":"..."}
// done event (always last)
{"type":"done","state_change":{...},
 "post_turn":{"module_transitions":[...],"achievements_unlocked":[...]},
 "state":{...}}
```

`POST /turn` returns the same shape flattened:
`{response, state_change, pre_turn, post_turn, state}`.

**Gotchas**:
- **`SessionStore` and `_isolate_session_store` fixture** — tests
  monkeypatch `app.state.sessions` per-test; mixing that with module-
  level `app.state.sessions = SessionStore()` at import time means
  anything storing a long-lived reference to `app.state.sessions`
  (instead of re-fetching via `store: SessionStore = instance.state.sessions`
  inside each handler) will silently break under test isolation.
- **FastAPI + `from __future__ import annotations`** — do NOT add the
  future import to `rag_quest/web/app.py`. FastAPI's body-parameter
  detection needs real Pydantic classes at runtime, not string
  forward references. Engine-type imports use explicit `TYPE_CHECKING`
  blocks instead.
- **MagicMock subsystems in web tests** — the shared turn helper
  touches `game_state.events`, `game_state.party`, `game_state.world`,
  `game_state.timeline`, `game_state.achievements`. Test fixtures
  must wire all five to safe mocks via `wire_turn_subsystems(gs)` from `tests/conftest.py`,
  otherwise MagicMock auto-creates return values that blow up
  `json.dumps` in the streaming endpoint (and jsonable_encoder
  sometimes silently stringifies them in the non-streaming path,
  hiding the problem).
- **Static mount ordering** — the `StaticFiles(html=True)` mount in
  `_build_app()` must be registered **last** or it shadows every API
  route. `tests/test_v08_web_static.py::test_api_routes_still_resolve_with_static_mount`
  is the regression guard.

### Knowledge Layer (knowledge/)

**WorldRAG** — LightRAG wrapper. Key methods: `initialize(world_name)`, `ingest_text(text, source)`, `ingest_file(path)` (.txt/.md/.pdf), `query_world(question, context) -> str`, `record_event(event)`.

**RAG Profiles** — Configurable chunking and query strategies:
- **fast**: 4000-char chunks, vector-only search
- **balanced**: 2000-char chunks, entity-focused search (recommended)
- **deep**: 1000-char chunks, hybrid entity+relationship search

**Implementation Detail**: LightRAG is async internally. `WorldRAG` uses `ThreadPoolExecutor` to run async operations from synchronous code via `_run_async()` helper.

### Game Loop (game.py)

**run_game()** — Main game loop:
1. Print welcome banner
2. Load or create character/world
3. Initialize RAG knowledge graph
4. Game loop:
   - Print game state
   - Prompt player
   - Handle command (if `/...`)
   - Otherwise: narrator.process_action()
   - Update game state
   - Auto-save every N turns
   - Repeat

**Commands Implemented**:
- `/i`, `/inventory` — Show inventory
- `/s`, `/stats` — Show character stats
- `/q`, `/quests` — Show quests
- `/p`, `/party` — Show party
- `/rel`, `/relationships` — Show NPC relationships
- `/h`, `/help` — Show full help
- `/config` — Change settings
- `/new` — New game
- `/save` — Manual save
- `/exit` — Quit

**All commands have short aliases** for quick access.

### Achievements System (achievements.py)

**AchievementEngine** — Tracks 11 achievements:
1. Explorer — Visit 10 locations
2. Warrior — Win 5 combats
3. Diplomat — Increase NPC disposition by 50 points
4. Scholar — Complete 5 quests
5. Treasure Hunter — Find 10 items
6. Dragon Slayer — Defeat a boss
7. Indestructible — Reach level 5 without dying
8. Hoarder — Have 50 items
9. Wealthy — Collect 1000 gold
10. Legendary — Reach level 10
11. Well-Connected — Meet 10 NPCs

### Campaign Memory (v0.6)

Three additive subsystems that layer over `GameState`, `WorldRAG`, and `state_parser`. No
existing code is restructured; memory features are strictly new-save-only (save_version 2; bumped to 3 for v0.7 bases + modules).

**Timeline (`engine/timeline.py`)** — `Timeline` container holds `TimelineEvent` and
`Bookmark` lists. After each turn, the game loop calls
`Timeline.record_from_state_change(turn, change, player_input, location)` which reads the
`StateChange` produced by `StateParser.parse_narrator_response()` (now preserved on
`Narrator.last_change`) and emits one or more structured events. Events rotate oldest-first
at `max_events` (default 2000); bookmarks never rotate. `/bookmark [note]` grabs
`Narrator.last_response` as full prose; `/bookmarks` lists saved highlights.

**Notetaker (`engine/notetaker.py`, `prompts/notetaker.py`)** — Incremental summarizer.
`Notetaker.refresh(current_turn, history, timeline_events)` sends dialogue + structured
events since `last_summarized_turn` to the configured LLM with `NOTETAKER_SYSTEM` and
parses JSON output into a `NoteEntry`. Storage is a JSON sidecar at
`~/.local/share/rag-quest/notes/{world}.json`. `_save_game()` auto-refreshes on every save
unless `notetaker.auto_summary` is set false in config. `/canonize N` promotes an entry
into LightRAG via `WorldRAG.ingest_text(body, source="canonized")` — hard boundary means
raw notes never silently touch retrieval.

**Hub Bases (v0.7, `engine/bases.py`)** — `Base` dataclass (name, location_ref,
`storage: Inventory`, `stationed_npcs: list[str]`, `npc_service: dict[str, str]`,
`services`, `upgrades`) lives on `World.bases: list[Base]` and serializes
alongside the rest of world state.
Claim flow: `StateChange.claim_base` fires when the narrator emits phrases like
*"claim X as your stronghold"* or *"this shall be your hideout"*; the narrator's
state-change handler calls `World.claim_base_at(location, name)`, which dedupes
on `location_ref` and returns the new `Base` (or `None`). The `/base` command
lists claimed bases; `/base claim [name]` is the deterministic escape hatch and
calls the same `World` method directly. Full menu (v0.7 /base hybrid menu):
`/base here` renders a Rich panel grouping stationed NPCs by service role
(from `Base.npc_service`). `/base station <npc> [as <service>]` binds an
NPC to a role and auto-registers the service. `/base talk <npc> <message>`
sets `Narrator.service_context` to a `build_service_prompt_addendum()`
string for a single turn — the addendum names the base, NPC, and canonical
`SERVICE_DESCRIPTIONS` entry, routes the response back through
`state_parser` as usual, and clears on exit. `/base deposit` / `/base
withdraw` move items between player `Inventory` and `Base.storage`.

**Modular Adventures (v0.7, `worlds/modules.py`)** — Worlds can declare
hub-and-spoke adventures in a top-level `modules.yaml` manifest. Schema: `id`,
`title`, `description`, `entry_location` (required); `unlock_when_quests_completed`,
`completion_quest`, `lore_files`, `rewards` (optional). `load_modules(world_dir,
world_rag)` parses + validates the manifest, ingests referenced lore via
`WorldRAG.ingest_file()`, and returns a `ModuleRegistry`. `World.module_registry`
holds the registry and round-trips via `to_dict`/`from_dict` (persisted
statuses win over initial-state computation on reload — pass
`compute_initial_states=False` to skip the recompute). `ModuleStatus` is an
`Enum` (LOCKED / AVAILABLE / ACTIVE / COMPLETED). Malformed manifests raise
`ModuleManifestError` (zero-traceback principle); `__main__.py` wraps the load
in a Rich status spinner so first-boot ingestion doesn't look like a hang.
`/modules` command lists declared modules by lifecycle status.
`ModuleRegistry.reevaluate(quest_log)` runs after every turn in `run_game`:
locked modules unlock when their `unlock_when_quests_completed` prereqs
are all completed, and modules with a matching `completion_quest` flip to
`COMPLETED`. Transitions are monotonic. Quest matching is case-insensitive
on `Quest.title`.

**`.rqworld` packaging (v0.7 / v0.8)** — `WorldExporter.export_world(game_state,
output_path, source_dir=..., save_file=...)` bundles `world.json` (which
already carries bases + serialized module registry via `World.to_dict`),
the source `modules.yaml` with every referenced lore file when
`source_dir` is set, and the player's save JSON as `save.json` when
`save_file` is set (v0.8 cross-device save sync). Both sides apply a Zip-Slip guard (reject lore paths that
escape `source_dir` on export; reject archive members that escape
`target_dir` on extract). `WorldImporter.extract_to(file, target_dir)`
unpacks the archive back to a world directory so the caller can run
`load_modules(target_dir, world_rag)` to re-ingest lore.
`WorldImporter.extract_campaign(file, install_dir=None)` is the v0.8
save-sync restore path: it unpacks the world into
`install_dir/worlds/<name>/` AND moves `save.json` to
`install_dir/saves/<name>.json` (default `install_dir` is
`~/.local/share/rag-quest/`). The world name from `metadata.json` is
sanitized (non-alnum → `_`) so a malicious archive can't write outside
the install dir. CLI subcommands `rag-quest export-campaign <name>
[out.rqworld]` and `rag-quest import-campaign <file>` wrap the
round-trip. Metadata `version` field is `rag_quest.__version__`
(not a hardcode).
Authors can validate a manifest before shipping with
`rag-quest validate-module <world-dir>` — the subcommand calls
`rag_quest.worlds.validate.validate_manifest()` which checks lore-file
existence, warns on orphan unlock references, and detects prerequisite
cycles in the completion-quest → unlock dependency graph. Exits 1 on any
fatal error so CI can gate on it. `rag-quest new-module <world-dir>` is
the matching creation tool: `rag_quest.worlds.new_module.run_interactive`
walks the author through the schema with Rich prompts, appends a
validated stanza via `write_module`, and rolls back on validator failure.
All prompt/confirm callables are injectable so the CLI flow is unit
testable without Rich.

**Debugging silent fallbacks** — The game loop and narrator contain
several additive `except Exception: pass` blocks (timeline recorder,
module gating re-eval, narrator RAG query) so a flaky subsystem never
kills the game. Set `RAG_QUEST_DEBUG=1` to make every swallowed
exception print a tagged traceback via
`rag_quest._debug.log_swallowed_exc(context)`. Use this first when a
v0.6+ feature silently stops working — it's the one-command check for
"is a catch eating something?"

**Import-graph trap** — `rag_quest.worlds.modules` lazy-imports
`engine.quests.QuestStatus` inside `ModuleRegistry.reevaluate` rather than
at module top. Hoisting creates a cycle: `engine/__init__.py → game.py
→ worlds.modules → engine.quests → engine/__init__.py`. Leave the lazy
import in place.

**Encyclopedia (`engine/encyclopedia.py`)** — Pure wrapper. `LoreEncyclopedia.list_entries()`
reads from `World.visited_locations`, `World.npcs_met`,
`RelationshipManager.{relationships,factions}`, and `Inventory.items`.
`LoreEncyclopedia.detail(entry)` runs an on-demand `WorldRAG.query_world()` with an
entity-shaped prompt, falling back to the GameState-side summary when RAG is unavailable.

**Gotchas**:
- `Narrator.last_change`, `last_response`, `last_player_input` are the contract Timeline /
  Bookmark consumers rely on. Don't reset them on error paths — leave stale values rather
  than wipe them.
- Notetaker failures (LLM timeout, corrupt sidecar) are silenced in `_save_game()`. Never
  let the notetaker block a save — campaign memory is additive, not load-bearing.
- Canonization is one-way per entry (`entry.canonized = True`). `pending_for_canonization`
  is the player-facing list.

### Dungeon Generation (dungeon.py)

**DungeonGenerator** — `generate_level(level) -> DungeonLevel`. 5–15 rooms/level; types: corridors, chambers, traps, treasure, boss. Returns ASCII map.

### Multiplayer (multiplayer/)

**MultiplayerSession** — Hot-seat multiplayer:
- Shared world state
- Per-player character
- Turn management
- Item trading system
- Cooperative and PvP combat options

### World Sharing (worlds/)

**WorldExporter** — Package world as `.rqworld`:
- Exports RAG knowledge graph
- Includes metadata and configuration
- Compressed format for distribution

**WorldImporter** — Load `.rqworld` packages:
- Validation and integrity checking
- Prevents corrupted worlds
- Merges knowledge into existing world

## Important Implementation Details

### Synchronous Architecture

All I/O is now synchronous (v0.5.0+). No async/await in game loop. **Note**: LightRAG is still async internally. `WorldRAG._run_async()` uses `ThreadPoolExecutor` to bridge.

### State Serialization

All game objects implement round-trip serialization: `game_state.to_dict()` → `json.dumps()` to save; `GameState.from_dict(json.loads(...))` to restore.

### Prompt Building

Prompts are composed at call-time, not templated: `[{"role": "system", "content": NARRATOR_SYSTEM + world_context}, {"role": "user", "content": player_action}]`.

### Terminal Output

Always use Rich (`Console`, `Panel`). **Color convention**:
- Green: Success, gains
- Red: Danger, loss
- Blue: Narrative
- Yellow: Warnings
- Magenta: System messages

## Error Handling Philosophy

**Zero tracebacks shown to users.** Every error path returns a friendly, actionable message
classified by root cause: Ollama not running, model not found, API key invalid, timeout, file
not found. When adding new error surfaces, follow the same pattern — name the cause, give the
user one concrete next step, and never leak a stack trace.

## How to Run & Develop

### Initial Setup

```bash
git clone https://github.com/mattwag05/rag-quest.git
cd rag-quest
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Homebrew Python 3.12+ is externally managed — always use a project venv. Subsequent commands
below assume the venv is activated (`source .venv/bin/activate`) or invoked via `.venv/bin/...`.

### Running

```bash
# Interactive setup (first time)
python -m rag_quest

# With environment config (scripting)
export LLM_PROVIDER=ollama OLLAMA_MODEL=gemma4:e4b
python -m rag_quest

# With specific world/character
export WORLD_NAME="My World" CHARACTER_NAME="Hero"
python -m rag_quest

# Web UI (requires [web] extras)
.venv/bin/pip install -e '.[web]'
rag-quest serve --host 127.0.0.1 --port 8000
```

### Testing

```bash
# Run all tests (use python -m pytest, not the shim — see Session Gotchas)
.venv/bin/python -m pytest

# Run a specific test file
.venv/bin/python -m pytest path/to/test_file.py -v

# With coverage
pytest --cov=rag_quest --cov-report=html
```

Historical per-version test scripts (`test_v05*.py`, `test_v04*.py`) were removed — don't
reintroduce them. Write new tests under `tests/` (or alongside the module under test).

### Development Workflow

```bash
# Format
black rag_quest/
isort rag_quest/

# Type check
mypy rag_quest/

# Check syntax
python -m py_compile rag_quest/**/*.py
```

## Session Gotchas (rediscover-tax savers)

- **Run tests as `.venv/bin/python -m pytest`**, not `.venv/bin/pytest` — the venv's pytest shim has a sys-path bug that fails with `ModuleNotFoundError: rag_quest` on a fresh editable install.
- **Bumping `__version__`?** Update BOTH `rag_quest/__init__.py` AND `pyproject.toml`. They've drifted before (pyproject stayed at 0.5.6 while `__init__.py` reached 0.6.0) — check both with `grep -n version pyproject.toml rag_quest/__init__.py` when cutting a release.
- **Character HP roundtrip**: `Character.__init__` recomputes `max_hp` / `current_hp` / `damage_dice` from race+class+level. `to_dict` → `from_dict` preserves identity fields (name, race, class, level, xp, location) but NOT combat stats. Roundtrip tests should only assert on identity.
- **PostToolUse hook auto-runs `black` + `isort`** on `.py` files after every Edit/Write. Don't manually format between edits — it's wasted work. The "file state is current in your context" note means the hook ran.
- **Rich `Live` can fail** in non-interactive / subshell contexts. Any new streaming UI helper must wrap the `with Live(...)` block in `try/except` and fall back to a plain `console.print(Panel(...))` (see `ui.stream_narrator_response` for the pattern).
- **Annotated tags required**: `git tag v0.x.y` fails with "no tag message?". Always use `git tag v0.x.y -m "v0.x.y"` when cutting a release.
- **Pre-push gate requires `/simplify` approval**: run the skill, then in a separate Bash call `touch /tmp/.claude-simplify-approved`, then push. The hook fires on `git push` only (not `git commit`). For doc-only commits, the flag may be set manually per the global CLAUDE.md exception.
- **Keep pyflakes clean** (rag-quest-dt4 + rag-quest-720): `pyflakes rag_quest/` currently exits 0 — zero warnings. Before committing anything in `rag_quest/`, run `.venv/bin/python -m pyflakes rag_quest/` (install with `.venv/bin/pip install pyflakes` if needed). Targets: no unused imports, no unused locals, no empty-prefix f-strings. If you add an `except ... as e:` block, actually log or re-raise `e` — otherwise drop the `as e`. The clean baseline is the easiest time to enforce this; pyflakes once it grows warnings again is painful to clean up.
- **`log_swallowed_exc("<dotted.context>")`** is the canonical swallow-silence idiom for any non-critical `except Exception: pass` site (timeline, module gating, narrator RAG, `game.cleanup.*`). Context strings are dotted namespaces like `game.cleanup.world_rag` or `timeline.record` — match the module + call site, not the error message. Normal runs stay silent; `RAG_QUEST_DEBUG=1` surfaces the tagged traceback. Local-import `from .._debug import log_swallowed_exc` inside the `except` block to keep startup cost zero.
- **Multi-edit-same-file gotcha**: firing multiple `Edit` calls targeting the same file in a single message — the PostToolUse auto-format hook reformats the file after each edit, so the *second* edit's `old_string` may no longer match. Safe pattern: one Edit per file per message, OR serialize (sequential tool calls). Parallel Edits are fine across *different* files.
- **`Read` before `Edit`, not `bash cat/head`**: the `Edit` tool only tracks files viewed via the `Read` tool. Using `bash head -20 file.py` to preview a file and then calling `Edit` errors with "File has not been read yet". If you plan to edit, use `Read`.
- **State parser regex compilation is uniform** (rag-quest-40q): every `*_patterns` list on `StateParser` is pre-compiled at `__init__` via `re.compile(p, re.IGNORECASE)` and call sites use `pattern.search(response)` / `pattern.finditer(response)` — no raw strings + `re.search(..., re.IGNORECASE)` on the hot path. `_strip_markdown` and the shared trailing-punct / leading-article cleanup regexes live as module-level compiled constants (`_MD_*`, `_TRAILING_PUNCT`, `_LEADING_ARTICLE`). When adding a new pattern or cleanup regex, follow the same idiom — don't drop a raw `re.sub(...)` or `re.search(...)` into an extractor.
- **`innerHTML` is blocked by a PreToolUse security hook**: writing `innerHTML = ...` anywhere (HTML, JS, `.py` string templates) fails with an XSS warning from `security_reminder_hook.py`. Use `textContent` + `createElement` for all DOM construction. `rag_quest/web/static/index.html` uses a tiny `makeEl(tag, {cls, text})` + `removeAllChildren(node)` pair — copy that pattern rather than fighting the hook.

## Known Design Limitations

1. **State parser is heuristic** — `engine/state_parser.py` now extracts location changes,
   damage/healing, item gains/losses, quest offers/completions, NPC encounters, and world
   events from narrator text. It uses regex + keyword rules, so phrasings it doesn't
   recognize silently produce no state change. When a gameplay bug traces back to "the
   narrative said X but state didn't update," the parser patterns are the place to look.

   **Two-stage damage flow**: `parse_narrator_response` runs explicit damage extraction
   (`_extract_damage` via compiled `damage_patterns`) first, then falls back to
   `_calculate_combat_damage` (dice roll) when `_has_combat_keyword` matches. A damage bug
   can live in *either* stage — checking only the regex won't catch dice-roll false
   positives. The combat gate must use word-boundary matching via `_combat_regex`; raw
   `any(word in text for word in keyword_set)` substring checks false-positive on
   "stable"→"stab" and similar (rag-quest-0gp).

2. **RAG Query Latency** — First query takes 30-60 seconds (LightRAG initialization).
   Typical query 1-3 seconds.

3. **PDF Ingestion Slow** — Large PDFs take minutes to ingest due to entity extraction.
   Recommend 5-10 page files for testing.

### `from_dict` hardening helpers

`rag_quest/engine/_serialization.py` provides two helpers used by every
hardened deserializer:

- `safe_enum(cls, value, default)` — enum lookup that tries member name
  first, then member value, and collapses to `default` on any failure
  (None, unknown name, wrong type). Use this for any `X[data["k"]]` or
  `X(data["k"])` pattern in a `from_dict`.
- `filter_init_kwargs(cls, data)` — strips dict keys that aren't valid
  `cls.__init__` parameters. Use before `cls(**data)` so newer save
  formats (with extra fields) don't crash older builds with "unexpected
  keyword argument".

When adding a new `from_dict` to the engine, reach for these instead of
`data["key"]` + bracket-enum lookups. Backed by `tests/test_from_dict_hardening.py`.

### Save Format Versioning Convention

New state fields bump `save_version` and add safe defaults in `GameState.from_dict()`. Policy
is clean-break: old saves load with empty new fields, no retroactive migration — new features
populate only on new saves. Document the bump in `docs/CHANGELOG.md` under that version.

Current: `SAVE_FORMAT_VERSION = 3` in `rag_quest/engine/game.py`.
- **v3** (v0.7): `world.bases`, `world.module_registry`
- **v2** (v0.6): timeline, notetaker sidecar pointer
- **v1**: baseline

## File Locations

- **Config**: `~/.config/rag-quest/config.json`
- **Saves**: `~/.local/share/rag-quest/saves/`
- **RAG Data**: `~/.local/share/rag-quest/worlds/{world_name}/`
- **Lore**: `./lore/`

## Performance Characteristics

**Ollama Response Times** (M1 Mac):
- Gemma 4 E4B (GPU): 2-10 sec per response
- Gemma 4 E2B (CPU): 10-60 sec per response

**RAG Query Times**:
- First query: 30-60 sec (initialization)
- Typical query: 1-3 sec
- Large world: 3-5 sec

**Memory Usage**:
- Base game: <50 MB
- Per 100 conversation exchanges: ~100 KB
- RAG storage: 50-200 MB per world

## Contributing

1. Check beads: `bd list`
2. Claim work: `bd update <id> --claim`
3. Create branch
4. Make changes
5. Test: `pytest`
6. Format: `black`, `isort`, `mypy`
7. Commit: atomic messages
8. PR & review

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for full guidelines.

## Resources

- **Feature ideation source**: [`docs/Extending RAG-Quest Using Features from Existing AI Dungeon Master Projects.md`](docs/Extending%20RAG-Quest%20Using%20Features%20from%20Existing%20AI%20Dungeon%20Master%20Projects.md) — competitive survey of AI DM projects with extractable feature ideas. Consult when scoping new roadmap entries.
- **LightRAG**: https://github.com/hkuds/LightRAG
- **Ollama**: https://ollama.ai
- **Gemma**: https://blog.google/technology/developers/gemma-open-models/
- **Rich**: https://rich.readthedocs.io/
- **httpx**: https://www.python-httpx.org/

---

**For**: Claude and other AI assistants contributing to RAG-Quest

**Key Principle**: LightRAG does the heavy lifting. Keep the LLM lightweight and focused on narrative.
