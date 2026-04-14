# CLAUDE.md — RAG-Quest AI Developer Guide

Guide for AI assistants working on RAG-Quest. Authoritative version lives in `rag_quest/__init__.py` — do not hardcode version strings elsewhere; import `rag_quest.__version__`.

> **Read [Session Gotchas](#session-gotchas-rediscover-tax-savers) first** — it's the rediscover-tax savers list (pytest shim bug, `Read`-before-`Edit`, worktree path traps, PreToolUse security hooks, Bookmark six-field constructor, slot_id wiring, …). Skim before touching code.

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

`rag_quest/` top-level: `__init__.py` (version), `__main__.py` (entry),
`startup.py`, `config.py`, `ui.py`, `tutorial.py`. Subpackages:

- **`llm/`** — `base.py` (sync `BaseLLMProvider`), `{ollama,openai,openrouter}_provider.py`, `_sse.py` (shared OpenAI-compatible SSE parser).
- **`knowledge/`** — `world_rag.py` (LightRAG wrapper), `chunking.py` (RAG profiles), `ingest.py` (PDF/txt/md), `world_db.py` (v0.9 SQLite entity registry + event log).
- **`engine/`** — `character.py`, `world.py`, `inventory.py`, `quests.py`, `party.py`, `relationships.py`, `events.py`, `combat.py`, `encounters.py`, `narrator.py`, `state_parser.py`, `state_event_mapping.py` (v0.9 shared `StateChange→writes` translator), `tts.py`, `game.py` (CLI loop), `achievements.py`, `dungeon.py`, `timeline.py` (v0.6), `notetaker.py` (v0.6), `encyclopedia.py` (v0.6), `bases.py` (v0.7), `turn.py` (v0.8 shared CLI/web turn helpers), `_debug.py` (`log_swallowed_exc`), `_serialization.py` (`safe_enum` / `filter_init_kwargs`), `saves.py`.
- **`multiplayer/`** — `session.py`, `trading.py`, `sync.py`.
- **`worlds/`** — `exporter.py` / `importer.py` (`.rqworld`), `templates.py`, `modules.py` (v0.7 manifest loader), `validate.py` / `new_module.py` (author CLIs).
- **`web/`** (v0.8, optional `[web]` extras) — `app.py` (FastAPI + SessionStore), `sessions.py`, `static/index.html` (vanilla-JS SPA), `onboarding.py`.
- **`prompts/`** — `templates.py` + subsystem prompts (`notetaker.py`, etc.).
- **`saves/`** — slot storage + `manager.py` (`SaveManager.save_game(slot_id=...)`).

Top-level repo: `lore/`, `docs/` (ARCHITECTURE, CHANGELOG, QUICKSTART, CONTRIBUTING, ROADMAP, MEMORY_ARCHITECTURE), `tests/`, `pyproject.toml`, `README.md`, `AGENTS.md`, `LICENSE`, `CLAUDE.md`.

## Core Classes & Patterns

### Startup & Config (`startup.py`, `config.py`)

`startup.py` handles the welcome banner and Ollama health/model detection.
`config.py` persists settings to `~/.config/rag-quest/config.json` via
`ConfigManager` (env-var fallback), with a first-run wizard offering
Fresh Adventure / Quick Start template / Upload Lore.

### Game State

**GameState** — Central state container: `character`, `world`, `inventory`, `quest_log`, `party`, `relationships`, `conversation_history`. Fully serializable via `to_dict()` / `from_dict()`. Saves are JSON at: `~/.local/share/rag-quest/saves/{world_name}.json`

**WorldDB (v0.9 Phase 1, save v4)** — `rag_quest/knowledge/world_db.py`. SQLite store
that lives at `{save_path}.db` next to the JSON save. Holds a typed entity registry
(NPCs, locations, factions, items, quests, bases) and an append-only event log,
populated via shadow-writes from `engine/turn.py::collect_post_turn_effects`. The
shared `StateChange→writes` translator lives in `engine/state_event_mapping.py`.
Authoritative spec: `docs/MEMORY_ARCHITECTURE.md`. v3 saves auto-migrate on
first load via `WorldDB.migrate_from_game_state` (idempotent via metadata flag).
Multi-write hot paths should wrap loops in `with world_db.transaction():` — inline
commits inside individual write methods become no-ops and the whole block commits
once on exit (rolls back on exception). Collapses ~7 commits/turn to 1 fsync.

**MemoryAssembler (v0.9 Phase 2)** — `rag_quest/knowledge/memory_assembler.py`. The
narrator's *read* path into WorldDB. Composes the §4.3 structured context block
(`## CURRENT STATE / ENTITIES PRESENT / RECENT EVENTS / RELEVANT HISTORY / WORLD LORE
/ PLAYER ACTION`) by calling WorldDB's `get_entity` / `get_entities_at` /
`get_recent_events` / `get_events_for_entity` / `get_relationship` and then a single
`WorldRAG.query_world` for lore. Three profiles tune §4.2 token budgets: `fast`
(5 recent turns), `balanced` (10), `deep` (15). Opt-in via `memory.assembler_enabled`
+ `memory.profile` in `~/.config/rag-quest/config.json`; default off.
`maybe_attach_to_narrator(narrator, game_state, config)` is the wiring helper called
from `__main__.py`, `web/onboarding.py`, and `web/sessions.py` after WorldDB opens —
keeps the three construction sites in sync. Narrator routes through new
`Narrator._gather_external_context`, which prefers the assembler when wired and
falls back to raw `WorldRAG.query_world` otherwise. Step 5 (FTS5 narrative echoes)
is intentionally deferred — see beads `rag-quest-50j`.

### Engine subsystems (`engine/`)

One-line pointers — full API in the source. Touch these files directly,
not this summary, when you need the contract.

- **`character.py`** — `Character` with 5 races × 5 classes, six D&D attributes, HP/XP/level. Stat bonuses apply at init.
- **`world.py`** — `World` tracks setting, tone, time/weather, visited locations, NPCs met, recent events; `Event` records consequences in the RAG graph.
- **`combat.py` / `encounters.py`** — D&D-flavored combat (d4-d20, initiative, crits), location-based enemy tables, difficulty scaling, loot.
- **`quests.py`** — `Quest` + `QuestLog` (pending/active/completed lifecycle, XP + item rewards).
- **`relationships.py`** — `RelationshipManager` on −1.0 → +1.0 scale, plus faction reputation. No non-obvious invariants — just a keyed dict per subsystem.

### Narrator (`narrator.py`)

Per-turn flow: player action → RAG query for context → compose prompt (system + world context + history) → call LLM (sync) → record the event back to RAG → return prose. `last_response`, `last_change`, and `last_player_input` are the published contract that Timeline/Bookmark consumers read.

**State Parser (`engine/state_parser.py`)** — Post-processes narrator output into a `StateChange`:
location moves, damage taken / healed, items gained/lost, quests offered/completed, NPCs
met/recruited, relationship deltas, world events. The game loop applies the `StateChange` to
`GameState` after each turn so inventory/quest/location stay in sync with the narrative.

### LLM Providers (`llm/`)

`BaseLLMProvider.complete(messages, **kw) -> str` is the **synchronous** contract (was async pre-v0.5.0). Implementations: `OllamaProvider` (local, recommended), `OpenAIProvider`, `OpenRouterProvider`.

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
  `world.module_registry.reevaluate(quest_log)`, serializes
  `game_state.to_dict()` **once** into `PostTurnEffects.state_dict`,
  then passes that cached dict to
  `achievements.check_achievements()`. If achievements unlock, only
  the achievements subtree is refreshed in place — the rest of the
  state is not re-serialized. The web layer reuses `.state_dict` for
  the done payload (rag-quest-dqr).
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

**Recent Fixes (April 13, 2026)**:
- **Turn counter lag** — the web client's turn number display was always
  off-by-one because `collect_post_turn_effects` was incrementing
  `game_state.turn_number` AFTER calling `GameState.to_dict()` for the
  done payload. Reordered to increment FIRST so the done payload includes
  the updated counter.
- **Markdown escaping in narrator panel** — state parser was stripping
  markdown emphasis from narrator text (to clean up `**NPC names**` in
  inventory), but the UI was rendering stripped text. Now markdown is
  preserved in the narrator pane and rendered through `textContent`
  (safe, no-HTML rendering).
- **Inventory sidebar refresh** — the right-side state panel was caching
  the initial `GameState` and never re-rendering inventory after items
  changed. Now the sidebar re-renders from current state on every turn.

### Knowledge Layer (knowledge/)

**WorldRAG** — LightRAG wrapper. Key methods: `initialize(world_name)`, `ingest_text(text, source)`, `ingest_file(path)` (.txt/.md/.pdf), `query_world(question, context) -> str`, `record_event(event)`.

**RAG Profiles** — Configurable chunking and query strategies:
- **fast**: 4000-char chunks, vector-only search
- **balanced**: 2000-char chunks, entity-focused search (recommended)
- **deep**: 1000-char chunks, hybrid entity+relationship search

**Implementation Detail**: LightRAG is async internally. `WorldRAG` uses `ThreadPoolExecutor` to run async operations from synchronous code via `_run_async()` helper.

### Game Loop (`game.py`)

`run_game()` owns the CLI side: welcome banner → load/create state → RAG init → loop (state panel → prompt → command dispatch or `narrator.process_action()` via the shared `turn.py` helpers → auto-save every N turns). Slash commands (`/i`, `/s`, `/q`, `/p`, `/rel`, `/h`, `/config`, `/new`, `/save`, `/exit`, `/base*`, `/bookmark*`, `/modules`) and their short aliases are defined on `run_game`; grep there when adding a new one.

### Achievements (`achievements.py`)

`AchievementEngine.check_achievements(state_dict)` runs inside `collect_post_turn_effects`. Full list of 11 achievements lives in `ACHIEVEMENTS`; add a new one by appending a dataclass entry and a matching check method.

### Campaign Memory (v0.6+)

Additive subsystems layered over `GameState` / `WorldRAG` / `state_parser`.
New-save-only (save_version bumped to 2 for memory, 3 for v0.7 bases + modules).
Source is the contract — the pointers below are just where to look.

- **Timeline (`engine/timeline.py`)** — `Timeline` holds `TimelineEvent` + `Bookmark` lists. `record_from_state_change(turn, change, player_input, location)` is called from `collect_post_turn_effects` and reads `Narrator.last_change`. Events rotate at `max_events=2000`; bookmarks never rotate. `/bookmark [note]` grabs `Narrator.last_response`.
- **Notetaker (`engine/notetaker.py`, `prompts/notetaker.py`)** — Incremental LLM summarizer. JSON sidecar at `~/.local/share/rag-quest/notes/{world}.json`. Auto-refreshes on `_save_game()` unless `notetaker.auto_summary=false`. `/canonize N` promotes a `NoteEntry` into LightRAG via `WorldRAG.ingest_text(..., source="canonized")` — hard boundary so raw notes never silently touch retrieval.
- **Encyclopedia (`engine/encyclopedia.py`)** — Pure wrapper over visited locations / npcs met / relationships / inventory. `detail()` runs an on-demand `WorldRAG.query_world()` with a GameState-side fallback.
- **Hub Bases (v0.7, `engine/bases.py`)** — `Base` dataclass on `World.bases`; claim via `StateChange.claim_base` (narrator phrasing) or `/base claim` (deterministic escape hatch). `/base here|station|talk|deposit|withdraw` is the hybrid menu. `/base talk <npc>` sets `Narrator.service_context` for a single turn via `build_service_prompt_addendum()`.
- **Modular Adventures (v0.7, `worlds/modules.py`)** — `modules.yaml` manifest → `load_modules(world_dir, world_rag)` → `ModuleRegistry` serialized on `World.module_registry`. Status enum `LOCKED / AVAILABLE / ACTIVE / COMPLETED`, monotonic transitions. `ModuleRegistry.reevaluate(quest_log)` runs each turn; unlock prereqs are `unlock_when_quests_completed` (case-insensitive on `Quest.title`), and `completion_quest` flips to COMPLETED. `ModuleManifestError` surfaces malformed manifests (zero-traceback). `rag-quest validate-module` / `rag-quest new-module` are the author CLIs.
- **`.rqworld` packaging (v0.7/v0.8, `worlds/{exporter,importer}.py`)** — `WorldExporter.export_world(game_state, output_path, source_dir=, save_file=)` bundles `world.json` + `modules.yaml` + referenced lore + `save.json` (v0.8 cross-device save sync). Zip-Slip guard on both ends. `WorldImporter.extract_campaign(file, install_dir=)` restores to `install_dir/worlds/<name>/` + `install_dir/saves/<name>.json`; world name sanitized (non-alnum → `_`). CLI: `rag-quest export-campaign` / `import-campaign`. Metadata `version` always `rag_quest.__version__`.
- **Dungeon (`engine/dungeon.py`)** — `DungeonGenerator.generate_level(level)` returns 5–15 rooms + ASCII map (corridors / chambers / traps / treasure / boss).
- **Multiplayer (`multiplayer/`)** — Hot-seat shared world, per-player character, trading, coop/PvP combat.

**Debugging silent fallbacks** — `RAG_QUEST_DEBUG=1` surfaces every `log_swallowed_exc` site as a tagged traceback. First check when a v0.6+ feature silently stops working.

**Import-graph trap** — `rag_quest.worlds.modules` lazy-imports `engine.quests.QuestStatus` inside `ModuleRegistry.reevaluate`. Hoisting creates a cycle (`engine/__init__ → game → worlds.modules → engine.quests`). Leave the lazy import in place.

**Memory gotchas**:
- `Narrator.last_change` / `last_response` / `last_player_input` are the published contract Timeline + Bookmark read from. Don't wipe them on error paths — leave stale values.
- Notetaker failures (LLM timeout, corrupt sidecar) are silenced in `_save_game()`. Never let the notetaker block a save — memory is additive, not load-bearing.
- Canonization is one-way per entry (`entry.canonized = True`); `pending_for_canonization` is the player-facing list.

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
- **Homebrew tap bump after release**: formula at `/opt/homebrew/Library/Taps/mattwag05/homebrew-tap/Formula/rag-quest.rb` (also `github.com/mattwag05/homebrew-tap`, GitHub-only — no Forgejo mirror). Bump = `url` + `sha256` + `version` (3 lines). SHA via `curl -sL https://github.com/mattwag05/rag-quest/archive/refs/tags/vX.Y.Z.tar.gz | shasum -a 256`. Commit + push from the tap dir, then `brew update && brew upgrade rag-quest`. Without this step, `brew info rag-quest` lags the actual release.
- **No `--version` flag**: `rag-quest --version` falls into the interactive launcher and EOFs in non-TTY contexts. To verify an install programmatically, grep the banner output (it prints `Version X.Y.Z`) or call `<cellar>/libexec/bin/python -c "import rag_quest; print(rag_quest.__version__)"`.
- **`cryptography` dylib relinking warning during `brew upgrade` is benign**: Homebrew's `fix_install_linkage` step fails on the `cryptography` wheel because its Mach-O header lacks pad room for `install_name` rewrites. The venv uses `@rpath` internally and rag-quest doesn't need to be linkable from other formulae — install completes, binary runs. Don't chase it.
- **Pre-push gate requires `/simplify` approval**: run the skill, then in a separate Bash call `touch /tmp/.claude-simplify-approved`, then push. The hook fires on `git push` only (not `git commit`). For doc-only commits, the flag may be set manually per the global CLAUDE.md exception.
- **Keep pyflakes clean** (rag-quest-dt4 + rag-quest-720): `pyflakes rag_quest/` currently exits 0 — zero warnings. Before committing anything in `rag_quest/`, run `.venv/bin/python -m pyflakes rag_quest/` (install with `.venv/bin/pip install pyflakes` if needed). Targets: no unused imports, no unused locals, no empty-prefix f-strings. If you add an `except ... as e:` block, actually log or re-raise `e` — otherwise drop the `as e`. The clean baseline is the easiest time to enforce this; pyflakes once it grows warnings again is painful to clean up.
- **`log_swallowed_exc("<dotted.context>")`** is the canonical swallow-silence idiom for any non-critical `except Exception: pass` site (timeline, module gating, narrator RAG, `game.cleanup.*`). Context strings are dotted namespaces like `game.cleanup.world_rag` or `timeline.record` — match the module + call site, not the error message. Normal runs stay silent; `RAG_QUEST_DEBUG=1` surfaces the tagged traceback. Local-import `from .._debug import log_swallowed_exc` inside the `except` block to keep startup cost zero.
- **Multi-edit-same-file gotcha**: firing multiple `Edit` calls targeting the same file in a single message — the PostToolUse auto-format hook reformats the file after each edit, so the *second* edit's `old_string` may no longer match. Safe pattern: one Edit per file per message, OR serialize (sequential tool calls). Parallel Edits are fine across *different* files.
- **`Read` before `Edit`, not `bash cat/head`**: the `Edit` tool only tracks files viewed via the `Read` tool. Using `bash head -20 file.py` to preview a file and then calling `Edit` errors with "File has not been read yet". If you plan to edit, use `Read`.
- **Worktree paths are not relative to `pwd`**: when working inside `.worktrees/<name>/`, `Edit` tool absolute paths must include `.worktrees/<name>/` — paths starting at the repo root silently hit the **master** worktree instead. Bash `pwd` shows the shell cwd but doesn't change what the `Edit` tool resolves. Recovery if you notice mid-session: `cp` the edited file from master into the worktree, then `cd /path/to/master && git checkout -- <file>` to reset master.
- **State parser regex compilation is uniform** (rag-quest-40q): every `*_patterns` list on `StateParser` is pre-compiled at `__init__` via `re.compile(p, re.IGNORECASE)` and call sites use `pattern.search(response)` / `pattern.finditer(response)` — no raw strings + `re.search(..., re.IGNORECASE)` on the hot path. `_strip_markdown` and the shared trailing-punct / leading-article cleanup regexes live as module-level compiled constants (`_MD_*`, `_TRAILING_PUNCT`, `_LEADING_ARTICLE`). When adding a new pattern or cleanup regex, follow the same idiom — don't drop a raw `re.sub(...)` or `re.search(...)` into an extractor.
- **`innerHTML` is blocked by a PreToolUse security hook**: writing `innerHTML = ...` anywhere (HTML, JS, `.py` string templates) fails with an XSS warning from `security_reminder_hook.py`. Use `textContent` + `createElement` for all DOM construction. `rag_quest/web/static/index.html` uses a tiny `makeEl(tag, {cls, text})` + `removeAllChildren(node)` pair — copy that pattern rather than fighting the hook.
- **PreToolUse security hook false-positives on regex `.exec`**: any JS call of the form `pattern.exec` with arguments trips a `child_process` command-injection warning, even in pure regex context — the hook sees `.exec(` as a literal substring regardless of receiver type. In browser JS, prefer `text.matchAll(pattern)` — stateless iteration, no exec call, no hook trip. `rag_quest/web/static/index.html::appendMarkdownText` is the reference site. Same category as the `innerHTML` gotcha above.
- **`rag_quest/web/__init__.py` shadows the `rag_quest.web.app` submodule** by re-exporting the FastAPI `app` instance as an attribute. Tests that need to monkeypatch module-level symbols in `web/app.py` must use `importlib.import_module("rag_quest.web.app")`. `from rag_quest.web import app as web_app` silently gives you the FastAPI instance instead of the module, and `monkeypatch.setattr` fails with `AttributeError: FastAPI object has no attribute '<symbol>'`.
- **`SaveManager.save_game` supports update-in-place via `slot_id=` kwarg** (`rag_quest/saves/manager.py`, post-dbs). Called without it, it mints a fresh UUID; called with an existing slot_id, it preserves `created_at` and bumps `updated_at`. Every write path (CLI autosave, web `POST /save`, web onboarding re-save) passes the session's `game_state.slot_id`. `SaveManager.save_paths_for(slot_id)` returns the canonical `{state, metadata, world_db}` paths inside the slot dir — use it instead of re-deriving the layout.
- **`Bookmark` dataclass requires six fields**, not four: `turn, timestamp, note, player_input, narrator_prose, location` (`engine/timeline.py:50-58`). Don't omit `timestamp` and `player_input` — constructor raises `TypeError`. Generate timestamp with `datetime.now().isoformat(timespec="seconds")` and pull `player_input` from `getattr(narrator, "last_player_input", "") or ""`. Canonical call site: `_cmd_bookmark` in `engine/game.py:612`.
- **Cross-cutting per-turn hooks belong in `engine/turn.py::collect_post_turn_effects`**, not `Narrator._parse_and_apply_changes`. As of v0.9 Phase 2 the narrator *does* hold an optional `_game_state` backref (set by `maybe_attach_to_narrator` when the MemoryAssembler is wired), but that backref is for **read paths only** — letting the assembler look up `character.location` and friends at prompt-build time. *Write* paths (timeline, module re-eval, achievements, WorldDB shadow write) still belong in `collect_post_turn_effects(game_state, player_input)` because that helper already has the canonical `game_state` + `narrator.last_change` and runs after every turn regardless of streaming/non-streaming, CLI/web.
- **`tests/conftest.py::wire_turn_subsystems(gs)`** is the shared fixture for MagicMock-driven turn-helper tests — wires `character`, `events`, `party`, `timeline`, `world.module_registry`, `achievements` to safe defaults. Don't re-wire from scratch; override individual subsystems after calling the helper.
- **`monkeypatch.setattr(Cls, "method", fn)` requires `self` in the replacement**: the descriptor protocol still passes `self` when the mocked method is called via `instance.method(...)`, so replacement callables must take it as their first positional arg or you'll see `TypeError: got multiple values for argument`. Pattern: `def _fake(self, state_dict, slot_id=None, **kw): ...`.
- **CLI has no save-load flow** — `rag_quest/__main__.py` only *creates* fresh GameStates via the setup wizard. The only `GameState.from_dict` caller is `rag_quest/web/sessions.py::load_session_from_slot`. New-game features need wiring at three sites: `__main__.py`, `web/onboarding.py`, and the load path `web/sessions.py`. Each site must mint a slot via `SaveManager().save_game(state_dict, slot_name=...)` and assign the returned `slot_id` to `game_state.slot_id` before entering the game loop — `_save_game` uses that slot_id to route autosaves through `SaveManager.save_game(slot_id=...)` for update-in-place semantics.
- **PEP 440 dev suffix uses `.devN`, not `-devN`** — `pyproject.toml` rejects `0.9.0-dev1` as an invalid version. Use `0.9.0.dev1` in both `pyproject.toml` and `rag_quest/__init__.py`.
- **MemoryAssembler is opt-in** — the v0.9 Phase 2 read path (`memory.assembler_enabled`) defaults to `false` so existing users see no behavior change. Flip the flag in `~/.config/rag-quest/config.json` to enable. The narrator's `_gather_external_context` helper handles both code paths in one place; don't add a third gating site.

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

   **Healing subject-guard**: the same discipline applies to `healing_patterns`.
   Every pattern requires the player ("you") as explicit subject/object, an
   artefact subject ("potion"), or passive voice with no enemy agent.  Without
   this, enemy self-healing ("the troll regenerates and heals 15 hp") silently
   adds HP to the player. Covered by `tests/test_state_parser_healing.py`.

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

See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md). Tracked in `bd` (`bd ready` → `bd update <id> --claim` → work → `bd close <id>`).

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
