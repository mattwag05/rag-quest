# Changelog

All notable changes to RAG-Quest. Authoritative version lives in `rag_quest/__init__.py`.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/). For anything not
captured here, `git log --oneline` is the source of truth.

**Maintenance rule**: add user-visible changes under `## [Unreleased]` in the same commit
as the code. When bumping `rag_quest.__version__`, rename `[Unreleased]` to the new
version and open a fresh `[Unreleased]` block above it. See `CLAUDE.md` → "Updating the
changelog" for the full convention.

## [Unreleased]

## [0.9.1] — 2026-04-15

### Changed
- **`memory.assembler_enabled` now defaults to `True`.** The WorldDB-backed
  `MemoryAssembler` is the narrator's primary context source out of the box.
  Existing users who want the legacy path can set the flag to `false` in
  `~/.config/rag-quest/config.json`.
- **`MemoryAssembler` is measurably faster on every turn.** Reference
  extraction now issues a single FTS5 OR-match per turn (was one query
  per token); entity snapshots go through a single `LEFT JOIN` helper
  (was three queries per entity); and repeated identical
  `(turn_number, player_input, location)` tuples return a memoized block
  without touching WorldDB or LightRAG. Internal beads: rag-quest-696,
  rag-quest-pvt, rag-quest-g13.
- **`Narrator._call_llm` now delegates to `_build_llm_messages`** instead
  of maintaining a near-duplicate copy of the prompt-building logic. No
  runtime change; removes a future divergence footgun. Internal bead:
  rag-quest-7uc.

### Removed
- **`WorldRAG.record_event` method.** It was defined but never called in
  v0.9.0 — every per-turn write already routes through `WorldDB.record_event`
  via the Phase 1 shadow-write. v0.9.1 deletes the dead method and marks
  the v0.9 Phase 3 cutover complete.

## [0.9.0] — 2026-04-13

### Added
- **`MemoryAssembler` — v0.9 Phase 2.** New `rag_quest/knowledge/memory_assembler.py`
  composes a structured §4.3 context block for the narrator from WorldDB
  facts (current state, entities present, recent events, relevant
  history) and a single LightRAG lore call. Replaces the raw
  `WorldRAG.query_world()` injection in the narrator system prompt when
  enabled. Opt-in via two new config keys:
  - `memory.assembler_enabled` (bool, default `false`)
  - `memory.profile` (`fast` | `balanced` | `deep`, default `balanced`)

  Profiles tune the §4.2 token budgets (recent turns, entity snapshot
  cap, historical event cap, lore cap). The narrator's
  `_gather_external_context` helper transparently falls back to the
  legacy LightRAG-only path when the assembler isn't wired, so existing
  saves and users see no behavior change until they flip the flag.
  `MemoryAssembler.assemble()` is the only place in the engine that
  *reads* from `WorldDB`; shadow-writes still happen in
  `engine/turn.py::collect_post_turn_effects`. See
  `docs/MEMORY_ARCHITECTURE.md` §4 for the full pipeline. Step 5
  (narrative echoes via FTS5) is intentionally deferred to a v0.9.x
  follow-up. 18 new tests in `tests/test_memory_assembler.py` and
  `tests/test_memory_assembler_narrator_integration.py`.

### Added (carried over from 0.9.0.dev1)
- **WebUI command menu — "Illuminated Terminal" redesign.** The browser
  client's footer gains a clickable sigil bar exposing inventory,
  stats, quests, party, relationships, timeline, bookmarks, lore,
  achievements, notes, base, story arcs, save, mark, and help. Each
  navigation panel opens in a manuscript-style modal with a gold
  drop-cap title and hand-drawn SVG divider. All navigation panels
  render client-side from the cached turn state — no server round-trip
  — so the browser UI matches the CLI slash commands without a new
  dispatcher. Contextual visibility: the BASE and ARCS sigils stay
  hidden until a base is claimed or modules are loaded.
- **Mobile-friendly command bar** — the sigil row wraps onto multiple
  rows below 768px with 44px minimum touch targets; the modal uses a
  near-full-screen overlay on narrow viewports. `prefers-reduced-motion`
  collapses every animation.
- **`POST /session/{id}/save`** endpoint — manual save from the browser.
  Resolves the on-disk path to work against both layouts that coexist
  today: flat `saves/{session}.json` (CLI + onboarding) and slot-dir
  `saves/{session}/state.json` (`/session/load`). The `rag-quest-dbs`
  bug tracks the real unification.
- **`POST /session/{id}/bookmark`** endpoint — capture the narrator's
  last scene as a `Bookmark` with an optional note, reusing the
  existing dataclass and timeline container.
- **`GET /session/{id}/notes`** endpoint — lightweight read of the
  in-session notetaker entries for the Notes panel.
- **Illuminated Terminal design system** — the whole web client is
  re-tokenized onto a new palette (warm ink-black, parchment vellum,
  sealing-wax red, gold leaf) with IBM Plex Mono for body and
  Cormorant Garamond italic for panel titles. Divider ornaments are
  hand-drawn SVG. No rounded corners on new components. Regression
  assertions in `tests/test_v083_web_command_menu.py` pin the aesthetic
  (tokens, fonts, uppercase sigil labels, `prefers-reduced-motion`,
  banned generic fonts) so future edits can't drift into generic SaaS
  slop.
- **`WorldDB` SQLite store** — Phase 1 of the v0.9 memory architecture
  redesign. Adds a typed entity registry (NPCs, locations, factions,
  items, quests, bases) and an append-only event log alongside the
  existing JSON save. Populated via shadow-writes from the per-turn
  state parser; the narrator does not yet read from it. Phase 2 will
  add the `MemoryAssembler` that consumes this store. See
  `docs/MEMORY_ARCHITECTURE.md` for the full architecture.
- **One-time migration from v3 saves** — loading a save that predates
  v0.9 walks the in-memory `GameState` and seeds the new database with
  visited locations, NPCs met, factions, inventory, quests, bases, and
  Timeline events. Idempotent via a metadata flag.
- **`engine/state_event_mapping.py`** — shared `StateChange → writes`
  translator used by the new `WorldDB` shadow write. Phase 3 will retire
  the duplicate translator in `Timeline.record_from_state_change` and
  point both consumers at this module.
- 30+ new tests across `tests/test_world_db.py` and
  `tests/test_world_db_integration.py` covering schema, dedup,
  relationships, FTS5 search, migration, and the turn-helper integration.

### Fixed
- **CLI-created worlds now show up in the web UI's save list**
  ([rag-quest-dbs]). The CLI and web onboarding used to write flat
  `saves/{world_name}.json` files that `SaveManager` never indexed, so
  a world started in the terminal was invisible to `GET /saves` in the
  browser. All three new-game paths (CLI, web, autosave) now route
  through `SaveManager.save_game(slot_id=...)` with a single canonical
  `saves/{slot_id}/{state.json,metadata.json,world.db}` layout.
- **Per-NPC disposition rows no longer split into two dimensions**
  ([rag-quest-678]). The WorldDB shadow-write previously emitted
  `disposition_delta` rows alongside the absolute `disposition` rows
  from the v3 migration, producing two conflicting entries per NPC
  that the Phase 2 MemoryAssembler would have to reconcile. Deltas
  now fold into the absolute `disposition` value via
  read-modify-write at the DB boundary, clamped to [-1.0, 1.0].

### Changed
- **Save format bumped to v4.** Adds a `world.db` SQLite file inside
  each save slot's directory alongside the existing `state.json`. Old
  saves auto-migrate on first load; nothing else changes.
- **Version bumped to 0.9.0.dev1.**
- **WorldDB `EntityType` / `EventType` are now `StrEnum`s**
  ([rag-quest-csi]). The CHECK clauses in the schema DDL are derived
  from the enum members so the validation sets, the SQL constraint,
  and every call site in `state_event_mapping.py` stay in lockstep
  automatically.

### Added
- **Opt-in state projection on the web turn endpoints**
  ([rag-quest-rkg]). Both `POST /session/{id}/turn` and
  `GET /session/{id}/turn/stream` accept a `?fields=a,b,c` query param
  that slices the `state` field of the done payload down to just those
  top-level keys. Default behavior is unchanged — omit the param to
  keep receiving the full state dict. Cuts per-turn bandwidth on long
  campaigns where the sidebar only reads a handful of keys.

### Fixed
- **Ollama thinking content leaking into narrator** — models like Gemma 4
  E2B that ignore `think=False` and inline chain-of-thought directly in
  the content field (using `<think>`, `<reasoning>`, or `<channel|>`
  delimiters) now have their reasoning stripped before the narrative
  reaches the player. Both `complete()` and `stream_complete()` are
  covered. The streaming path uses a three-phase state machine
  (detection → full-buffer → passthrough) with heuristic meta-commentary
  detection to buffer thinking tokens indefinitely until a delimiter
  arrives, while still flushing clean narrative promptly. 24 new tests
  in `tests/test_ollama_thinking_strip.py`.

## [0.8.2] — 2026-04-13

### Added
- **WebUI game onboarding flow** — new players can now create a character
  and start a game entirely from the browser, without touching the CLI.
  A 3-step wizard (world template selection → character creation with
  race/class picker → confirmation) is accessed via the "New Game" button
  in the header. The overlay uses `role="dialog"` for accessibility and
  all DOM construction is XSS-safe (`createElement`/`textContent` only).
- **Onboarding API endpoints** — `GET /onboarding/races`,
  `GET /onboarding/classes`, `GET /onboarding/templates` serve static
  character-creation data; `POST /session/new` validates inputs, builds
  engine objects, persists the initial save, and returns a ready-to-play
  session. Input validation rejects empty names, names > 50 chars,
  unknown races/classes/templates with descriptive 400 errors.
- **`rag_quest/web/onboarding.py`** — new module containing `RACES`,
  `CLASSES`, `TEMPLATES` data (synced with engine enums and
  `worlds/templates.py`) and the `create_new_session()` factory that
  mirrors the CLI new-game path without Rich prompts.
- 21 new tests in `tests/test_v082_onboarding.py` covering data
  endpoints, input validation, static HTML elements, JS function
  presence, XSS safety, and data integrity against engine enums.

## [0.8.1] — 2026-04-13

### Added
- **WebUI responsive layout** — the browser client now adapts to narrow
  screens (phones, tablets). Below 768px the sidebar stacks below the
  narrator pane instead of beside it, and touch targets are enlarged.
- **WebUI HP bar** — a color-coded health bar (green / yellow / red) now
  renders below the character stats in the sidebar, updating live after
  each turn.
- **WebUI quest sidebar** — active quests now appear in the sidebar panel
  with title and truncated description, sourced from the `quest_log`
  in the done payload.
- **WebUI loading indicator** — a pulsing "Thinking..." animation appears
  in the narrator pane while waiting for the LLM response, replacing the
  previous blank gap between player input and narrator output.
- **WebUI welcome panel** — a centered welcome message with game
  description now greets players before they load a save, replacing the
  previous bare system line.
- **WebUI accessibility improvements** — skip-to-content link for keyboard
  navigation, `role="log"` on the narrator pane, `role="status"` with
  `aria-live="polite"` on the status bar, `aria-label` attributes on all
  interactive elements and landmark regions, and visible `:focus-visible`
  outlines.
- **WebUI visual polish** — consistent border-radius and transition CSS
  custom properties, hover states on header controls, player input prefix
  moved to a CSS `::before` pseudo-element, and smooth HP bar transitions.
- 22 new tests in `tests/test_v081_web_ui.py` covering accessibility
  attributes, HP bar, quest sidebar, loading indicator, welcome panel,
  responsive breakpoint, visual polish, and XSS safety invariants.

### Fixed
- **WebUI turn counter display** — the turn number now displays correctly
  in the browser client after each turn. Previously the counter was
  derived from `state.turn_number` but the web layer's turn endpoints
  were incrementing the game state turn AFTER the state was serialized
  for the done payload, so the counter always lagged by 1. Fixed by
  moving the `turn_number` increment to occur BEFORE the final state
  serialization in `collect_post_turn_effects` (rag-quest-dqr).
- **WebUI markdown rendering** — narrator responses now render correctly
  when they contain markdown formatting. Previous releases had a bug where
  markdown emphasis markers (`**`, `*`, `__`, `_`) were being stripped
  from the state but not from the UI text, leaving broken markup visible
  to the player. Markdown is now preserved in the narrator panel and
  rendered via the browser's built-in text handling (rag-quest-dqr).
- **WebUI inventory sidebar state** — the right-side state panel now
  properly refreshes inventory display after items are picked up, dropped,
  or used. Previously the sidebar cached the initial state and never
  re-rendered even when `state_change` indicated inventory mutations.
  Fixed by always re-rendering the sidebar from the current `GameState`
  on every turn (rag-quest-dqr).
- **`GameState.from_dict()` hardening** — deserializers for `Character`,
  `World`, `NPC`, `NPCRelationship`, `Faction`, `Quest`, `QuestObjective`,
  and `QuestReward` now handle corrupted or partial saves gracefully.
  New `safe_enum()` helper collapses unknown/malformed enum values to
  canonical defaults instead of raising `KeyError`; new `filter_init_kwargs()`
  strips unrecognized dict keys so newer saves don't break older builds.
  Saves that were previously fatal with tracebacks now load with sensible
  defaults. Covered by comprehensive new tests in
  `tests/test_from_dict_hardening.py`.

### Changed
- **Per-turn state serialization halved** — `collect_post_turn_effects`
  now serializes `GameState.to_dict()` once per turn and reuses the
  cached dict for both the achievements check and the web layer's
  non-streaming / streaming done payload. Previously each turn paid for
  two full serializations of the state (character + world + inventory
  + quests + party + relationships + events + timeline + achievements
  + bases + modules). On long-running saves this was the dominant
  per-turn CPU cost after the narrator call itself (rag-quest-dqr).

### Fixed
- **Healing false-positive bug** — narrator descriptions of enemy self-healing
  ("The troll regenerates and heals 15 hp") no longer credit the player with
  HP recovery. All five healing patterns in `StateParser` now require either
  the player ("you") as an explicit subject/object, an artefact subject
  ("potion"), or passive voice with no enemy agent — mirroring the subject-guard
  discipline applied to damage extraction in rag-quest-0gp. Covered by 13 new
  tests in `tests/test_state_parser_healing.py`.

## [0.8.0] — 2026-04-12

### Added
- **v0.8 web: CLI turn-loop parity** — `POST /session/{id}/turn` and
  `GET /session/{id}/turn/stream` now fire every side effect the CLI
  loop runs per turn: world-event check/expire, party loyalty
  departures, timeline recording, module-gating reevaluation, and
  achievement unlocks. A shared pure helper in
  `rag_quest/engine/turn.py` (`collect_pre_turn_effects`,
  `collect_post_turn_effects`, `advance_one_turn`) owns the mechanics,
  with zero Rich/console coupling, so CLI and web callers share one
  implementation. Both endpoints now return `pre_turn` and `post_turn`
  payloads alongside `response`/`state_change`/`state`; the streaming
  endpoint emits a new `event: pre_turn` SSE frame before any narrator
  chunks so clients can render world-event banners up top. 11 new
  engine-turn unit tests + 9 new web parity tests. (rag-quest-1o2)
- **v0.8 web: static browser client** — new
  `rag_quest/web/static/index.html` + `README.md`. Single-page vanilla
  JS (no build step, no framework, no CDN) with a dark-mode terminal
  aesthetic — left-side auto-scrolling narrator pane, right-side state
  panel (character / location / inventory), bottom input form. Talks
  to the server over `fetch()` for `/saves` + `/session/load` +
  `/session/{id}/state`, and `EventSource` for the streaming turn
  endpoint. Mounted at `/` via `StaticFiles(html=True)` after all API
  routes so it can't shadow them. All server-supplied text renders
  through `textContent`/`createElement` — `innerHTML` is not used
  anywhere, since LLM output and save-file data flow through the
  page. 2 new tests pin the mount invariants. (rag-quest-dby)
- **v0.8: Streaming narrator responses** — the game loop now renders
  narration token-by-token via Rich `Live` instead of waiting 2-10
  seconds for the complete response, so players see prose unfold
  live. `BaseLLMProvider` gains a `stream_complete(messages)` method
  with a safe single-chunk fallback; `OllamaProvider` streams Ollama's
  line-delimited JSON protocol, `OpenAIProvider` and `OpenRouterProvider`
  share a new `rag_quest/llm/_sse.py` helper that parses OpenAI-compatible
  SSE events. `Narrator.stream_action(player_input)` is the public
  streaming entry point: it yields chunks and, after the generator is
  exhausted, runs the state parser on the full joined response so
  mechanics stay deterministic. `ui.stream_narrator_response(iterator)`
  wraps a Rich `Live` panel update loop; `run_game` consumes it.
- **v0.8: Cross-device save sync** — `WorldExporter.export_world` gains
  an optional `save_file` parameter that bundles the player's save JSON
  (`~/.local/share/rag-quest/saves/<name>.json`) into the archive as
  `save.json`. `WorldImporter.extract_campaign(file, install_dir)` is
  the matching restore path: it unpacks world files into
  `install_dir/worlds/<name>/` AND restores `save.json` to
  `install_dir/saves/<name>.json`, sanitizing path-separator chars in
  the world name so a malicious `metadata.name` can't escape the
  install directory. New CLI subcommands `rag-quest export-campaign
  <world-name> [out.rqworld]` and `rag-quest import-campaign
  <file.rqworld>` wrap the round-trip so players can move a campaign
  between machines without a cloud account.

### Added
- **v0.8 web streaming turn endpoint** —
  `GET /session/{session_id}/turn/stream?input=...` wraps
  `Narrator.stream_action` in a FastAPI `StreamingResponse` with
  `text/event-stream` media type. Uses GET + query string so browser
  `EventSource` (which only speaks GET) can consume the stream
  directly. Each streamed token becomes a
  `data: {"type":"chunk","text":"..."}\n\n` SSE event; after the
  generator exhausts, a terminal
  `data: {"type":"done","state_change":{...},"state":{...}}\n\n`
  event fires. Validation (404 unknown session, 400 empty input)
  runs BEFORE the generator starts so error responses stay
  synchronous HTTP status codes instead of partial streams.
  Mid-stream failures in the underlying narrator are swallowed
  via `log_swallowed_exc("web.turn.stream")` — clients can always
  rely on the `done` event arriving with whatever state the
  narrator ended up in, and `turn_number` increments regardless.
  5 new tests in `tests/test_v08_web_stream.py` covering happy
  path, 404, 400, mid-stream-failure resilience, and
  empty-chunk filtering. (rag-quest-tqh)

- **v0.8 web turn endpoint** — `POST /session/{session_id}/turn`
  with body `{"input": "..."}` drives a single player turn through
  the existing `Narrator.process_action` path. Returns
  `{"response": str, "state_change": dict, "state": dict}` where
  `state_change` is `dataclasses.asdict(narrator.last_change)` (or
  `{}` if no state change was parsed) and `state` is the updated
  `GameState.to_dict()`. Increments `game_state.turn_number` after
  each successful call. Returns 404 for unknown session ids and 400
  for empty/whitespace input. Narrator's own fallback-response path
  is transparent — clients always get a 200 with a non-empty
  response body even if the underlying LLM raises. 5 new tests in
  `tests/test_v08_web_turn.py`. Full CLI turn-loop parity (world
  events, party loyalty departures, timeline recording, module
  gating, achievements) is tracked as a follow-up in rag-quest-1o2
  — the MVP endpoint intentionally stays narrow so sub-bead
  dependencies stay unblocked. (rag-quest-g86)

- **v0.8 web read endpoints** — new `rag_quest/web/sessions.py`
  module encapsulates the "read save dict from disk → build provider
  → build WorldRAG → build Narrator → hydrate GameState" chain behind
  a single `load_session_from_slot(slot_id)` entry point, raising
  `SessionLoadError` on any failure (missing slot, malformed config,
  unknown provider, hydration error). Three new HTTP endpoints:
  `GET /saves` lists every save slot via the existing
  `SaveManager.list_saves()`; `POST /session/load` with body
  `{"slot_id":"..."}` hydrates the slot and parks the `GameState` in
  the module-level `SessionStore`, returning session metadata
  (session_id, world, character, turn_number); `GET
  /session/{session_id}/state` serializes the stored `GameState` via
  `to_dict()`. Endpoint handlers lazy-import `rag_quest.web.sessions`
  inside their function bodies so tests can monkeypatch the
  hydration layer without touching real save files or LLM
  providers. Re-loading the same slot closes the previous session's
  `WorldRAG` and LLM first so shared resources are released cleanly
  (matches the `run_game` finally-block pattern). 6 new tests in
  `tests/test_v08_web_read.py`. (rag-quest-8y7)

- **v0.8 web scaffold** — new `rag_quest/web/` subpackage holds a
  FastAPI app (`rag_quest.web.app.app`), an in-memory `SessionStore`
  that registers loaded-campaign triples (`GameState` / `Narrator`
  / `WorldRAG`) by save name, and a `rag_quest.web.app.run(host,
  port)` uvicorn launcher. `fastapi` + `uvicorn` are pulled in via a
  new optional `[web]` extras group — the base install stays slim.
  CLI gains `rag-quest serve [--host 127.0.0.1] [--port 8000]` which
  hands off to uvicorn; missing-extras failures raise ImportError
  with a clear install hint instead of a confusing
  `ModuleNotFoundError`. One endpoint ships in this sub-bead:
  `GET /healthz` → `{"status": "ok", "version": __version__}`.
  Subsequent sub-beads (tracked under rag-quest-a7h) add `/saves`,
  `/session/load`, `/session/{id}/state`, `POST /session/{id}/turn`,
  the SSE streaming variant, and a static HTML frontend. 5 new
  scaffold tests in `tests/test_v08_web_scaffold.py`. (rag-quest-9gx)

### Changed
- **`EventManager.apply_effects` documented as a stub.** The built-in
  event templates declare `effects` dicts (`shop_prices`,
  `enemy_difficulty`, `npc_friendliness`, `item_variety`, etc.)
  describing what an event *would like* to modify. No game subsystem
  reads the returned map yet, and the method is not called from the
  turn loop. The keys are preserved as authoring intent; real wire-up
  into shops/encounters/NPC disposition tracked in rag-quest-nen.
  (rag-quest-702)

### Fixed
- **`run_game` shutdown catches now route through `log_swallowed_exc`.**
  The `finally` block in `rag_quest/engine/game.py::run_game` wraps
  `game_state.world_rag.close()` and `game_state.llm.close()` in a
  last-line-of-defense `except Exception:` handler each. Previously
  those catches were bare `pass`, so any unexpected shutdown-phase
  failure (e.g. a typo introduced at a refactor, an `executor.shutdown`
  hang, a new contract violation) vanished silently at exit. Both are
  now routed through `log_swallowed_exc("game.cleanup.world_rag")` and
  `log_swallowed_exc("game.cleanup.llm")`, matching the per-turn
  additive catch convention. Normal runs stay silent; exporting
  `RAG_QUEST_DEBUG=1` surfaces the tagged traceback. Inner
  `WorldRAG.close()` still logs its own `finalize_storages` failure
  via `print(...)` — the new outer log only fires for secondary
  failures above that. (rag-quest-hmq)

### Fixed
- **`Narrator.__init__` dead parameters.** `party`, `relationships`, and
  `events` were declared `Optional["Party"] / Optional["Relationships"]
  / Optional["EventManager"]` but none of the three forward-ref class
  names were imported (`"Relationships"` was a typo; the actual class
  is `RelationshipManager`). All three attributes were assigned in
  `__init__` and then never read anywhere in the module, and the only
  caller (`rag_quest/__main__.py`) never passed them. Removed the
  params, the assignments, and the broken type hints. Found via
  pyflakes audit. (rag-quest-wav)
- **`ui.py` duplicate function definitions.** `print_character_status`
  was defined twice (lines 156 and 357) and `print_world_context` was
  defined twice (lines 164 and 375). Python late-binding silently made
  the second definitions authoritative, so the first versions were
  unreachable dead code. Removed the dead first versions. Found via
  pyflakes audit. (rag-quest-5ya)

### Removed
- **Dead public exports: `StateSync` + 6 unused prompt templates.**
  Scout audit found two clean dead-export categories with zero
  callers in `rag_quest/` or `tests/`:
  (1) `rag_quest/multiplayer/sync.py` — a `StateSync` class with
  three `@staticmethod`s (`sync_world_state`, `merge_player_actions`,
  `resolve_conflicts`) that was re-exported from
  `multiplayer/__init__.py::__all__` but never instantiated or
  called. Deleted the whole `sync.py` file and trimmed the
  `__init__.py` import + `__all__` entry.
  (2) `rag_quest/prompts/templates.py` — `COMBAT_NARRATOR`,
  `ABILITY_NARRATION`, `PARTY_CONTEXT`, `RELATIONSHIP_CONTEXT`,
  `QUEST_CHAIN_NARRATION`, `WORLD_EVENT_NARRATION` were defined as
  module constants but each had exactly one reference in the entire
  codebase — the definition itself. Deleted all six. `prompts/__init__.py`
  didn't re-export them, so no import hygiene work was needed there.
  192 tests pass, pyflakes stays exit 0. (rag-quest-zo9)

- **Dead-local / cosmetic cleanup (pyflakes round 2).** Follow-up to
  the import sweep: deleted unused locals (`response_lower` and
  `defensive_words` in `engine/state_parser.py`; `char` in
  `saves/migration.py`; `elapsed` plus its `start = time.time()` in
  `engine/narrator.py::_call_llm`, which cascaded into dropping the
  module's `time` import); dropped three unused `except ... as e:`
  captures (`engine/game.py` cleanup path and
  `engine/narrator.py::process_action` + `knowledge/world_rag.py`
  embedder fallback) down to bare `except Exception:`; and removed
  the `f` prefix from 15 format-string literals that had no
  placeholders (fallback-response lists in `engine/narrator.py`,
  blank-line entries in `ui.py::print_character_status`, the ASCII
  banner in `engine/game.py::_print_banner`, and the constant
  party-backstory string). Zero behavior change; `pyflakes
  rag_quest/` now exits 0 — no warnings of any category. (rag-quest-720)

- **Unused-import sweep across `rag_quest/`.** pyflakes audit turned
  up ~30 imports that were pulled in but never referenced — typing
  helpers (`Dict`, `Optional`, `Tuple`), Rich widgets (`Layout`,
  `Rule`, `Text`, `Table`, `Align`, `Markdown`, `Panel`, depending on
  the file), `asyncio` in modules that became synchronous in v0.5,
  stale world-class exports (`TimeOfDay`, `Weather`), leftover
  `dataclass` / `field` imports in modules without dataclasses,
  `textwrap` in `worlds/new_module.py`, and several orphaned
  per-module helpers (`chunk_pdf_text`, `TextChunker`,
  `should_re_ingest`, `SaveManager`, `CombatEncounter`,
  `EncounterGenerator`, `ACTION_PARSER`, `Markdown` in
  `engine/game.py`, local `from rich.table import Table` inside
  `_render_base_menu`, local `from . import startup` inside
  `ConfigManager._setup_llm_provider`). Also lifted
  `MultiplayerSession` in `multiplayer/sync.py` from a never-imported
  forward-ref string to a proper `TYPE_CHECKING` import. No behavior
  change; pyflakes now reports zero "imported but unused" warnings
  for `rag_quest/`. (rag-quest-dt4)

- **Dead-code sweep in `StateParser`.** `parse_action_intent` was a
  player-input intent classifier that used raw substring matching —
  so a player typing "I lay the stable boy down" would have tripped
  `is_combat` on `"stab" in "stable"`. Audit turned up zero callers
  in production code, tests, or docs, so the method was deleted
  rather than patched — a bug in unreachable code is worse than
  missing functionality. A cascade check then found two more
  `StateParser.__init__` attributes that only `parse_action_intent`
  (or nothing at all) referenced: `self.relationship_keywords` (a
  disposition-delta lookup table, never consulted) and
  `self.recruitment_patterns` (three regexes, never searched). Both
  removed. If intent classification is needed later, reuse the
  word-boundary `StateParser._combat_regex` idiom. (rag-quest-1d9)

### Changed
- **State parser: pre-compiled every regex on the per-turn hot path.**
  Nine pattern lists (`healing_patterns`, `pickup_patterns`,
  `drop_patterns`, `use_patterns`, `quest_offer_patterns`,
  `quest_complete_patterns`, `npc_patterns`, `location_patterns`,
  `recruitment_patterns`) on `StateParser` are now compiled once at
  `__init__` (matching the existing `damage_patterns` /
  `_combat_regex` / `claim_base_patterns` idiom) and call sites use
  `pattern.search(response)` / `pattern.finditer(response)`. The four
  `_strip_markdown` emphasis-stripper patterns plus the shared
  trailing-punct and leading-article cleanup regexes are now
  module-level compiled constants (`_MD_BOLD_STAR` / `_MD_BOLD_UNDER`
  / `_MD_ITALIC_STAR` / `_MD_ITALIC_UNDER` / `_TRAILING_PUNCT` /
  `_LEADING_ARTICLE`). No functional change — removes repeated
  `re.compile` cache lookups on every extraction. (rag-quest-40q)
- **Hardened `from_dict` deserializers against corrupted saves.** New
  `rag_quest/engine/_serialization.py` module exposes `safe_enum(cls,
  value, default)` (by-name-or-value enum lookup with safe fallback) and
  `filter_init_kwargs(cls, data)` (strips keys that aren't valid
  `__init__` parameters). Applied to `Character`, `World`, `NPC`,
  `NPCRelationship`, `Faction`, `Quest`, `QuestObjective`, and
  `QuestReward` `from_dict` methods. Corrupted/partial saves now load
  with sensible defaults instead of raising `KeyError` /
  `TypeError` tracebacks — unknown enum values (e.g. a renamed
  `CharacterClass`) degrade to canonical defaults, and extra fields
  from newer builds are stripped before `cls(**data)` so an older
  binary can still load a newer save.

### Added
- **`RAG_QUEST_DEBUG=1` env flag** — new `rag_quest/_debug.py` module exposes
  `log_swallowed_exc(context)`. When the env var is set, every additive
  per-turn catch site (timeline recorder, module gating, narrator RAG query)
  prints a tagged traceback to stderr instead of eating the exception.
  Normal runs stay silent. Directly motivated by the v0.7.1 narrator-RAG
  bug that hid inside a bare `except Exception: pass` block for an unknown
  number of releases.

### Fixed
- **Critical:** new characters no longer die on turn 1 when the narrator's
  status line includes an HP readout. The state parser's damage regex
  (`rag_quest/engine/state_parser.py`) matched `22/22 HP` as 22 points of
  damage, and the combat-keyword gate used substring matching so `stable`
  triggered combat via `stab`. Damage extraction now requires an
  action-verb form (`take/suffer/receive N damage|hp`) or
  `lose N hp/health/hit points`, and the combat gate is word-boundary
  with a `hit points`/`hit dice` exclusion. Regression tests in
  `tests/test_state_parser_damage.py`. (rag-quest-0gp)
- Tightened the last three bare `except:` clauses in the repo
  (`engine/tts.py:186`, `engine/tts.py:195`, `knowledge/world_rag.py:187`)
  so they no longer swallow `KeyboardInterrupt` / `SystemExit` alongside
  the errors they actually meant to catch. The `WorldRAG.close`
  finalization path now logs failures to stderr instead of silently
  eating them on shutdown.

## [0.7.1] — Narrator RAG Fix

### Fixed
- **Critical:** narrator now actually pulls world lore from `WorldRAG` on
  every LLM call. The previous code (`narrator.py:208`) called
  `self.world_rag.query(...)` — a method that does not exist on `WorldRAG`
  — and the resulting `AttributeError` was silently swallowed by a bare
  `except Exception: pass` block. As a result, the narrator's LLM prompt
  never included RAG-fetched lore, defeating the core design principle
  (*"LightRAG does the heavy lifting"*) for an unknown span of releases.
  Fixed to call `query_world()` and treat the returned string correctly.
  Regression tests in `tests/test_narrator_rag_context.py`.
- Tightened two bare `except:` clauses in `engine/combat.py` (dice parse
  fallback) and `engine/tts.py` (voice switch) so they no longer swallow
  `KeyboardInterrupt` / `SystemExit` alongside the actual errors they're
  meant to catch.

## [0.7.0] — Modular Adventures & Hub Bases

### Added
- **v0.7: `/base` hybrid menu + service conversation routing** — stationed
  NPCs can now be bound to a service role (smith, healer, innkeeper,
  storage, stable, library) via `/base station <npc> as <service>`.
  `/base here` renders a Rich panel grouping NPCs by service. `/base talk
  <npc> <message>` runs a scoped conversation: the narrator gets a
  deterministic `build_service_prompt_addendum()` system addendum naming
  the NPC and their canonical role for one turn, then clears it — the
  response still flows through the state-parser. `/base deposit` and
  `/base withdraw` shift items between player `Inventory` and the base's
  `storage` Inventory. New `Base.npc_service` dict maps stationed NPC
  names to service strings; `Base.npcs_by_service()` groups them for UI.
- **v0.7 foundation: `Base` entity** — new `rag_quest/engine/bases.py` with `Base`
  dataclass (name, location_ref, storage `Inventory`, stationed NPCs, services,
  upgrades) plus `World.bases: list[Base]` that round-trips through `to_dict` /
  `from_dict`. Old saves without `bases` load as empty.
- **v0.7: Base claim flow** — narrator phrasings like *"claim the ruined tower as
  your stronghold"*, *"make this your headquarters"*, or *"this shall be your
  hideout"* now create a `Base` at the character's current location via a new
  `StateChange.claim_base` rule. New `/base` command lists claimed bases;
  `/base claim [name]` is a deterministic escape hatch when regex detection
  doesn't catch the narrator's phrasing. Claims dedupe on `location_ref`.
- **v0.7: `rag-quest new-module <world-dir>` CLI** — interactive manifest
  author tool. Rich prompts walk you through module id (with auto-suggested
  slug from the title), title, description, entry location, optional
  completion quest, optional prerequisite modules (auto-wires to the
  selected modules' `completion_quest` values as the new module's
  `unlock_when_quests_completed`), and optional XP reward. Can stub a lore
  template at `lore/modules/<id>.md` if one doesn't already exist (never
  clobbers hand-written lore). Validates the resulting manifest via
  `validate_manifest` and rolls back the append if validation fails so the
  manifest can't be left wedged. Also hardens the loader: `modules:` with
  nothing underneath is now a legal empty manifest.
- **v0.7: `.rqworld` exporter/importer know about bases + modules** —
  `WorldExporter.export_world` gains an optional `source_dir` parameter.
  When supplied, the packager bundles `modules.yaml` plus every
  `lore_files` reference into the archive (with a Zip-Slip guard that
  rejects lore paths escaping `source_dir`). `Base` state already rides
  along inside `world.json` via `World.to_dict` from earlier v0.7
  commits, so existing saves with claimed bases now round-trip through
  `.rqworld` automatically. New `WorldImporter.extract_to(file, target_dir)`
  writes the archive contents to disk with a Zip-Slip guard on the import
  side so shipped worlds can be dropped straight into
  `~/.local/share/rag-quest/worlds/<name>/` and immediately handed to
  `load_modules()`. Metadata `version` field now tracks
  `rag_quest.__version__` instead of a stale hardcode.
- **v0.7: `rag-quest validate-module <path>` CLI** — non-interactive subcommand
  that loads a `modules.yaml` manifest, checks all referenced lore files
  exist, warns on unlock prereqs that no declared module completes (likely
  narrative quests — possibly typos), and detects prerequisite cycles in the
  implicit completion-quest → unlock dependency graph. Exits 0 on clean,
  1 on any fatal error. Warnings never fail the check. Wraps a new
  `rag_quest.worlds.validate.validate_manifest()` helper so author tooling
  can call the checker programmatically without spawning a subprocess.
- **v0.7: Module gating via QuestLog** — `ModuleRegistry.reevaluate(quest_log)`
  runs after every turn in the game loop and transitions module statuses
  based on completed quests. Locked modules become `AVAILABLE` when their
  `unlock_when_quests_completed` prereqs are all marked done; available/active
  modules with a matching `completion_quest` become `COMPLETED` and unlock any
  dependent modules in the same call. Transitions are monotonic (completed
  modules stay completed). Quest references match `Quest.title`
  case-insensitively. Game loop surfaces "Module unlocked" and "Module
  completed" notifications via `ui.print_info` / `ui.print_success`.
- **v0.7: `modules.yaml` loader + `ModuleRegistry`** — worlds can now declare
  hub-and-spoke adventure modules in a top-level `modules.yaml` manifest.
  New `rag_quest/worlds/modules.py` validates the schema (id, title,
  description, entry_location, unlock_when_quests_completed, completion_quest,
  lore_files, rewards), ingests referenced lore files into the knowledge
  graph via `WorldRAG.ingest_file()`, and stores the result in a new
  `World.module_registry` field. Malformed manifests raise
  `ModuleManifestError` and surface via `ui.print_error()` — never crashes the
  game loop. New `/modules` command lists declared modules by lifecycle status
  (active / available / locked / completed). On startup, the loader probes
  `./lore/modules.yaml` then `~/.local/share/rag-quest/worlds/{name}/modules.yaml`.

### Dependencies
- Adds `pyyaml>=6.0` as a runtime dependency for the new modules.yaml loader.

### Changed
- **Save format bumped to v3.** `world.bases` and `world.module_registry`
  are now part of the serialized save state. Clean-break migration policy
  (same as v0.6): v2 saves load with empty `bases` and an empty
  `ModuleRegistry`; new v0.7 features populate only on new saves. No
  retroactive migration. `SAVE_FORMAT_VERSION` lives in
  `rag_quest/engine/game.py`.

### Fixed
- State parser: strip Markdown emphasis markers (`**`, `__`, `*`, `_`) from extracted
  NPC names, item names, locations, and quest titles. Narrators that format proper nouns
  with bold/italic no longer leak `**Captain Mira**` into `World.npcs_met`, Inventory, or
  Timeline events (`rag_quest/engine/state_parser.py`).
- State parser: reject false-positive regex extractions that polluted game state.
  `"you take a deep breath"` no longer adds "deep breath" to inventory; `"the morning
  sun rising"` no longer registers as an NPC; trailing prepositional phrases (`"Whispering
  Woods at dawn"` → `"Whispering Woods"`, `"wild fox in"` → `"wild fox"`) are stripped
  from location and NPC extractions.

## [0.6.0] — Campaign Memory

### Added
- **AI Notetaker** — incremental session summarizer. Auto-runs on every save (and `/save`),
  reads a `last_summarized_turn` cursor so long campaigns only chew on new material. New
  `/notes` (alias `/n`) command shows the latest summary; `/notes refresh` forces an update.
  JSON sidecar stored at `~/.local/share/rag-quest/notes/{world}.json`. Config toggle
  `notetaker.auto_summary` lets cost-sensitive users on paid providers opt out.
- **Canonize** — new `/canonize` command promotes player-approved note entries into LightRAG
  with `source="canonized"` tag. Hard boundary between local JSON notes and the canonical
  world graph; nothing touches retrieval without explicit player approval.
- **Player Journal & Timeline** — `/timeline` (alias `/t`) renders a chronological event log
  sourced from `StateChange` output. Types: location, combat, quest, npc, item, world_event.
  Supports filtering (`/timeline combat`, `/timeline quest`, etc.). Events are capped at 2000
  with oldest-first rotation (bookmarks never rotate).
- **Bookmarks** — `/bookmark [note]` (alias `/bm`) captures the current turn's full narrator
  prose with optional note. `/bookmarks` lists saved highlights.
- **Lore Encyclopedia** — `/lore` (alias `/l`) browses NPCs, locations, factions, and items
  encountered during play. `/lore <category>` lists entries; `/lore <category> <name>` runs
  an on-demand `WorldRAG.query_world()` against the selected entity for rich detail.
- Tutorial step 9 introduces the full memory panel (`/notes`, `/lore`, `/timeline`,
  `/bookmark`, `/canonize`).

### Changed
- `save_version` bumped to **2**. v1 saves load with empty timeline + notetaker cursor —
  clean-break policy, no retroactive migration. New features only populate on new saves.
- `Narrator.process_action` now exposes the last parsed `StateChange`, player input, and
  response prose for downstream consumers (Timeline/Notetaker/Bookmark). Internal-only
  change — existing callers unaffected.

## [0.5.6]

### Fixed
- Use dynamic version from `rag_quest.__version__` instead of hardcoded strings across UI,
  banners, and `--version` output.
- Ollama provider handles thinking models (Qwen 3.5, DeepSeek-R1) by stripping
  `<think>...</think>` blocks before returning.
- Narrator sends proper `messages=[{"role": "user", "content": ...}]` format to Ollama's
  `/api/chat` endpoint, fixing HTTP 400 errors on LLM calls.
- ASCII art shows "RAG-Quest" (not "GAG-Quest"); package build includes all subpackages.
- Stale version comments and duplicate entries removed from README/QUICKSTART.

## [0.5.3]

### Added
- Interactive TUI tutorial — 9-step guided walkthrough via `/tutorial` covering exploration,
  NPCs, inventory, combat, commands, quests, saving, and pro tips.
- Downloadable user guide — `docs/RAG-Quest_User_Guide.docx`, 8 chapters + appendix, written
  for non-technical players.
- 25-turn automated test suite with full regression coverage.

## [0.5.2]

### Added
- Friendly setup wizard with Ollama auto-detection.
- Command shortcuts: `/i`, `/s`, `/q`, `/p`, `/h`.
- `/new` command to start a new game without quitting.
- `/config` command for mid-game setting changes.
- Character creation confirmation screen.
- Save management: game recaps on load, metadata tracking.

### Changed
- Zero tracebacks shown to users — every error path returns a friendly, actionable message
  classified by root cause (Ollama, timeout, API key, file).
- Terminal output now uses safe 80-char line widths and accessible color contrast.

### Fixed
- Inventory serialization preserves all data across save/load.
- `DifficultyLevel` enum complete with all values.
- Comprehensive backwards compatibility for legacy save files.

## [0.5.1]

### Added
- Persistent config system (`~/.config/rag-quest/config.json`).
- Three start modes: Fresh Adventure, Quick Start (templates), Upload Lore.
- Polished startup and in-game settings.

### Fixed
- Resolved all remaining P1 API bugs carried over from 0.5.0.

## [0.5.0]

### Added
- Multiplayer (hot-seat, shared world state, trading, PvP/co-op combat).
- Persistent saves with full round-trip serialization.
- World sharing via `.rqworld` export/import.
- 11 achievements.
- Procedural dungeon generation.

### Changed
- **Synchronous rewrite** — providers and game loop are now pure sync. LightRAG is still
  async internally; `WorldRAG._run_async()` bridges via `ThreadPoolExecutor`.

## [0.4.0]

### Added
- Parties (multi-character).
- NPC relationships and faction reputation.
- Quest chains.
- Dynamic world events recorded back into the RAG knowledge graph.

### Fixed
- 6 API integration bugs found during 22-turn playtest.

## [0.3.0]

### Added
- D&D combat system with dice rolls (d4–d20, attack vs AC, criticals).
- Character progression (levels, XP, six attributes).
- Encounter generation with location-based enemy tables and loot.
- Text-to-speech narration support.

## [0.2.0] — MVP

### Added
- Rich terminal UI and working game loop.
- Core engine: character, world, inventory, quests, narrator.
- LightRAG integration with fast/balanced/deep profiles.
- Ollama, OpenAI, and OpenRouter LLM providers.
- 50-turn playtest verified end to end.
