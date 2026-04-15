# RAG-Quest Development Roadmap

A phased roadmap for RAG-Quest, an AI-powered D&D-style text RPG with LightRAG knowledge graph backend.

## Design Philosophy

**Core Principle**: LightRAG does the heavy lifting. The LLM narrator is kept lightweight (Gemma 4 E2B/E4B—2-4B parameters, ≤8K context) because it doesn't memorize the world. LightRAG's dual-level retrieval (entity + vector matching) injects precisely the relevant knowledge per query. This enables RAG-Quest to run entirely on consumer hardware with local models via Ollama.

This philosophy shapes every version.

---

## v0.8.3 — Web UI Command Menus & "Illuminated Terminal" Redesign

**Status**: ✅ Complete — shipping as part of the v0.9.0 pre-release cycle.

### What's New in v0.8.3

**Sigil Command Bar**
- ✅ Clickable sigil row in the WebUI footer exposing every major panel: INV, STATS, QUESTS, PARTY, NPCS, TIME, MARKS, LORE, HONORS, NOTES, BASE, ARCS, SAVE, MARK, HELP
- ✅ Infocom-style uppercase verbs — touch-friendly, no chatty labels
- ✅ Contextual visibility: BASE and ARCS sigils stay hidden until a base is claimed or modules are loaded
- ✅ Mobile reflow at <768px with 44px minimum touch targets

**Panel Modal System**
- ✅ Every navigation panel (inventory, stats, quests, party, relationships, timeline, bookmarks, lore, achievements, modules, base, notes, help) renders client-side from the cached turn state — zero server round-trip
- ✅ Manuscript-style modal with gold drop-cap title and hand-drawn SVG divider
- ✅ Esc/backdrop dismiss, focus management, `aria-modal` dialog semantics

**Mutating Endpoints**
- ✅ `POST /session/{id}/save` — manual save from browser, handles both coexisting save layouts
- ✅ `POST /session/{id}/bookmark` — capture narrator's last scene with optional note
- ✅ `GET /session/{id}/notes` — read notetaker entries for the Notes panel

**Illuminated Terminal Design System**
- ✅ Full palette re-tokenization: warm ink-black, parchment vellum, sealing-wax red, gold leaf
- ✅ IBM Plex Mono for body, Cormorant Garamond italic for panel titles
- ✅ Inline SVG divider ornament, gold drop-caps via `::first-letter`, sharp corners
- ✅ `prefers-reduced-motion` collapses every animation
- ✅ Design regression assertions in `tests/test_v083_web_command_menu.py` pin tokens, fonts, and banned generic fonts (Inter, Roboto, Arial, Space Grotesk)

---

## v0.8.2 (Current) — Web Onboarding Flow

**Status**: ✅ Complete — new players can create a character and start a game from the browser without CLI.

### What's New in v0.8.2

**Game Onboarding Wizard**
- ✅ 3-step overlay wizard: world template selection → character creation → confirmation
- ✅ "New Game" button in header opens the onboarding dialog
- ✅ Race and class pickers with stat previews and descriptions
- ✅ 4 built-in world templates (Classic Dungeon, Enchanted Forest, Port City, War-Torn Kingdom)
- ✅ `role="dialog"` accessibility, XSS-safe DOM construction

**Onboarding API**
- ✅ `GET /onboarding/races`, `/classes`, `/templates` data endpoints
- ✅ `POST /session/new` creates a full game session with validation
- ✅ Input validation: empty names, long names, unknown race/class/template → 400

**Data Integrity**
- ✅ Onboarding RACES/CLASSES match engine enums
- ✅ Onboarding TEMPLATES match `worlds/templates.py` STARTER_WORLDS

---

## v0.8.1 — WebUI Design Polish

**Status**: ✅ Complete — responsive layout, HP bar, quest sidebar, loading indicator, welcome panel, accessibility improvements.

### What's New in v0.8.1

**Responsive Layout**
- ✅ Mobile breakpoint at 768px stacks sidebar below narrator
- ✅ Enlarged touch targets and spacing for phone/tablet use

**HP Bar Visualization**
- ✅ Color-coded health bar (green > 60%, yellow > 30%, red below)
- ✅ Smooth animated transitions on HP changes

**Quest Sidebar**
- ✅ Active quests displayed with title and truncated description
- ✅ Sourced from `quest_log` in the done payload state

**Loading Indicator**
- ✅ Pulsing "Thinking..." animation during LLM response wait

**Welcome Panel**
- ✅ Centered welcome message before a save is loaded

**Accessibility**
- ✅ Skip-to-content link for keyboard navigation
- ✅ `role="log"` on narrator, `role="status"` on header status
- ✅ `aria-label` on all interactive elements and landmark regions
- ✅ Visible `:focus-visible` outlines for keyboard users

**Visual Polish**
- ✅ CSS custom properties for consistent border-radius and transitions
- ✅ Hover states on header controls
- ✅ Player input prefix via CSS `::before` pseudo-element
- ✅ 22 new tests in `tests/test_v081_web_ui.py`

---

## v0.8.0 — Web UI & Streaming

**Status**: ✅ Complete — FastAPI web server, streaming SSE turns, static browser client, cross-device save sync, turn-loop parity, from_dict hardening.

### What's New in v0.8.0

**Web UI**
- ✅ `FastAPI` app with `/healthz`, `/saves`, `/session/load`, `/session/{id}/state` endpoints
- ✅ `/session/{id}/turn` (non-streaming) and `/session/{id}/turn/stream` (SSE streaming)
- ✅ Static vanilla-JS browser client with dark-mode terminal aesthetic
- ✅ Left-side auto-scrolling narrator pane, right-side state panel, bottom input
- ✅ `rag-quest serve --host 127.0.0.1 --port 8000` CLI launcher

**Streaming Narrator**
- ✅ `Narrator.stream_action()` yields tokens for live prose rendering
- ✅ `BaseLLMProvider.stream_complete()` with safe single-chunk fallback
- ✅ OllamaProvider streams line-delimited JSON; OpenAI/OpenRouter use shared SSE parser
- ✅ Rich `Live` panel for CLI, `EventSource` for browser

**Cross-Device Save Sync (v0.8)**
- ✅ `WorldExporter.export_world(..., save_file=...)` bundles player save into `.rqworld`
- ✅ `WorldImporter.extract_campaign()` unpacks world + save to `~/.local/share/rag-quest/`
- ✅ `rag-quest export-campaign <name> [out.rqworld]` and `rag-quest import-campaign <file>` CLI subcommands

**Turn-Loop Parity**
- ✅ Shared `rag_quest/engine/turn.py` helpers: `collect_pre_turn_effects()`, `collect_post_turn_effects()`, `advance_one_turn()`
- ✅ Web endpoints and CLI loop call the same mechanics (world events, party loyalty, timeline, module gating, achievements)
- ✅ Pre-turn and post-turn payloads in all turn endpoints

**Hardening**
- ✅ `from_dict` deserializers guard against corrupted saves via `safe_enum()` and `filter_init_kwargs()`
- ✅ WebUI bug fixes: turn counter display, markdown rendering in narrator panel, inventory sidebar state
- ✅ State parser healing patterns guard against false-positives (enemy self-healing no longer credits player)
- ✅ State parser damage extraction uses word-boundary matching

---

## v0.7.0 — Modular Adventures & Hub Bases

**Status**: ✅ Complete — the full v0.7 epic shipped as save format v3 with 55+ new tests.

### What's New in v0.7.0

**Hub Bases**
- ✅ `Base` entity in `engine/bases.py` with storage Inventory, stationed NPCs, service roles, upgrades
- ✅ `/base claim [name]` escape hatch + narrator-driven claim detection (`StateChange.claim_base` rule)
- ✅ `/base here` Rich panel grouping stationed NPCs by service (`Base.npcs_by_service()`)
- ✅ `/base station <npc> [as <service>]` binds NPCs to canonical service roles (smith, healer, innkeeper, storage, stable, library)
- ✅ `/base talk <npc> <message>` — scoped conversation with a deterministic narrator system addendum via `build_service_prompt_addendum()`
- ✅ `/base deposit` / `/base withdraw` move items between player Inventory and the base's own storage

**Modular Adventures**
- ✅ `modules.yaml` manifest format + `ModuleRegistry` + `Module` dataclass with `ModuleStatus` enum
- ✅ `load_modules()` validates schema and ingests referenced lore files via `WorldRAG.ingest_file()`
- ✅ `ModuleRegistry.reevaluate(quest_log)` runs post-turn, transitions module statuses monotonically, surfaces unlock/completion notifications
- ✅ `/modules` command lists declared modules by lifecycle status

**Author Tooling**
- ✅ `rag-quest validate-module <dir>` — non-interactive sanity checker with DFS cycle detection on the completion-quest → unlock dependency graph
- ✅ `rag-quest new-module <dir>` — interactive Rich-prompt manifest author with auto-slug, prereq auto-wiring, lore-stub generation, and rollback-on-validation-failure

**`.rqworld` Packaging**
- ✅ Exporter `source_dir` parameter bundles `modules.yaml` + referenced lore with Zip-Slip guard
- ✅ `WorldImporter.extract_to()` unpacks to disk with matching Zip-Slip guard
- ✅ Metadata `version` now tracks `rag_quest.__version__` (was hardcoded `0.5.0` since v0.5)

**Save format v3**
- ✅ `save_version` → 3; `world.bases` and `world.module_registry` round-trip through `World.to_dict` / `from_dict`
- ✅ v2 saves load with empty collections (clean-break policy)

**Dependency**: pyyaml>=6.0

---

## v0.6.0 — Campaign Memory

**Status**: ✅ Complete — AI Notetaker, Lore Encyclopedia, Player Journal & Timeline shipped as pure additive layers over existing GameState, LightRAG, and state_parser.

### What's New in v0.6.0

**AI Notetaker** (hybrid-trigger)
- ✅ Auto-refresh on save events (both auto-save and `/save`)
- ✅ `/notes` command to view; `/notes refresh` to force update
- ✅ Incremental via `last_summarized_turn` cursor — no re-summarizing 500-turn campaigns
- ✅ JSON sidecar at `~/.local/share/rag-quest/notes/{world}.json`
- ✅ Config toggle `notetaker.auto_summary` for cost-sensitive providers

**Canonize**
- ✅ `/canonize N` or `/canonize all` promotes notes into LightRAG with `source="canonized"`
- ✅ Hard boundary — local JSON never silently pollutes retrieval

**Lore Encyclopedia**
- ✅ `/lore` category overview, `/lore <cat>` listing, `/lore <cat> <name>` RAG detail
- ✅ Browse NPCs, locations, factions, items from GameState indexes
- ✅ On-demand `WorldRAG.query_world()` for rich descriptions

**Player Journal & Timeline**
- ✅ Every turn emits structured `TimelineEvent` from `StateChange`
- ✅ `/timeline` with type filters (combat, quest, npc, item, location, all)
- ✅ `/bookmark [note]` captures full narrator prose; `/bookmarks` lists saved highlights
- ✅ 2000-event cap with oldest-first rotation; bookmarks never rotate

**Save format v2**
- ✅ `save_version` → 2; v1 saves load with empty memory fields (clean-break policy)

---

## v0.5.3 — Tutorial & User Guide

**Status**: ✅ Complete — Interactive tutorial, downloadable user guide, automated testing

### What's New in v0.5.3

**Interactive TUI Tutorial**
- ✅ 9-step guided tutorial accessible via `/tutorial` command
- ✅ Covers exploration, NPCs, inventory, combat, commands, quests, saving, and tips
- ✅ Works in-game — no external tools needed
- ✅ Beginner-friendly with clear explanations at each step

**Downloadable User Guide**
- ✅ Professional Word document (docs/RAG-Quest_User_Guide.docx)
- ✅ 8 chapters + appendix covering all game features
- ✅ Written for non-technical users
- ✅ Covers setup, character creation, gameplay, commands, advanced features

**Quality Assurance**
- ✅ 25-turn automated test suite (test_v053.py)
- ✅ 100% pass rate across all game systems
- ✅ Tutorial system fully tested
- ✅ All previous tests continue passing

---

## v0.5.2 — Polished UX for Non-Developers

**Status**: ✅ Complete — Production-ready, comprehensive UX polish, zero tracebacks

### What's New in v0.5.2

**Comprehensive UX Polish**
- ✅ Friendly setup wizard with three start modes
- ✅ Automatic Ollama detection with setup guidance
- ✅ Character creation confirmation screen
- ✅ Input validation with helpful retry messages
- ✅ Smart save management with game recaps on load

**Error Handling**
- ✅ Zero tracebacks shown to users
- ✅ Every error has an actionable, friendly message
- ✅ Smart error classification (Ollama, timeout, API, file errors)
- ✅ Graceful recovery and helpful suggestions

**Command System**
- ✅ Command shortcuts: `/i`, `/s`, `/q`, `/p`, `/h`
- ✅ New `/new` command to start game without quitting
- ✅ New `/config` command for mid-game settings changes
- ✅ Better unknown command feedback with suggestions

**Terminal UX**
- ✅ Better status bar formatting and clarity
- ✅ Improved narrator response panels with Rich formatting
- ✅ Subtle "✓ Progress saved" notification on auto-save
- ✅ Game recap when loading save (character, level, world, days)
- ✅ Safe line widths (80-char compatible)
- ✅ Color contrast for accessibility

**Help System**
- ✅ Comprehensive `/help` with command reference table
- ✅ Command shortcuts displayed prominently
- ✅ Pro tips and game features highlighted
- ✅ Troubleshooting guidance for stuck players
- ✅ Examples of natural language actions

**Quality Assurance**
- ✅ All syntax validated (py_compile)
- ✅ No tracebacks in error paths
- ✅ Backwards compatible with all previous saves
- ✅ All 12 core game systems verified working

---

## v0.5.1 — Polish for Everyone

**Status**: ✅ Complete — UX enhancements, smart saves, friendly errors

### Highlights

**Setup & Configuration**
- ✅ Automatic Ollama detection
- ✅ Clear setup wizard without jargon
- ✅ No command-line knowledge required
- ✅ Provider descriptions explaining each option
- ✅ Links to external services (Ollama, OpenAI, OpenRouter)

**Error Recovery**
- ✅ User-friendly error messages instead of tracebacks
- ✅ Helpful suggestions for fixing common issues
- ✅ Automatic recovery from transient failures
- ✅ Smart error classification

**Save Management**
- ✅ Auto-save every 5 actions
- ✅ Ctrl+C offers save before exit
- ✅ Save metadata tracking
- ✅ Clear save confirmation messages

**Visual Improvements**
- ✅ Better status bar formatting
- ✅ Improved narrator response panels
- ✅ Achievement notifications with clear formatting
- ✅ Level-up celebrations

---

## v0.5.0 — Multiplayer, Saves & World Sharing

**Status**: ✅ Complete — All major features implemented

### Highlights

**Persistent Save System**
- ✅ Multi-slot saves (5+ independent slots)
- ✅ Auto-save rotation (keeps 3 most recent)
- ✅ Export/import as `.rqsave` files
- ✅ Format migration between versions
- ✅ Centralized SaveManager

**World Sharing**
- ✅ Export worlds as `.rqworld` packages
- ✅ Import community worlds
- ✅ 4 built-in starter templates
- ✅ World validation and integrity checking

**Local Multiplayer**
- ✅ Hot-seat mode for turn-based play
- ✅ Shared world state
- ✅ Item trading between players
- ✅ Cooperative and PvP combat

**Achievement System**
- ✅ 11 achievements (Explorer, Warrior, Diplomat, Scholar, Treasure Hunter, Dragon Slayer, Indestructible, Hoarder, Wealthy, Legendary, Well-Connected)
- ✅ Automatic detection and notifications
- ✅ Progress tracking
- ✅ Real-time notifications

**Procedural Dungeons**
- ✅ Random level generation (5-15 rooms per level)
- ✅ ASCII maps that reveal as you explore
- ✅ Room types: corridors, chambers, traps, treasure, boss
- ✅ Difficulty-scaled enemies and loot

---

## v0.4.1 — API Integration Fixes

**Status**: ✅ Complete — All 6 critical API bugs fixed

### Bugs Fixed
- ✅ Inventory.list_items() returns formatted string correctly
- ✅ Party constructor accepts optional leader argument
- ✅ RelationshipManager.add_npc() method implemented
- ✅ QuestLog.add_quest() accepts Quest objects
- ✅ EventType enum has CONFLICT and all standard types
- ✅ Character.get_available_abilities() method implemented

---

## v0.4.0 — Character Progression, Combat & Narration

**Status**: ✅ Complete — Full D&D mechanics and real LLM narration

### Highlights

**D&D Combat System**
- ✅ Dice rolling (d4-d20)
- ✅ Initiative and attack rolls vs AC
- ✅ Damage calculation with critical hits
- ✅ Turn-based combat flow

**Character Progression**
- ✅ 6 attributes (STR/DEX/CON/INT/WIS/CHA)
- ✅ 5 races with stat bonuses
- ✅ 5 classes with unique abilities
- ✅ XP and leveling to level 10
- ✅ Class abilities unlocking

**Real LLM Narration**
- ✅ Actual LLM calls for dynamic narration
- ✅ Context injection (game state, RAG knowledge)
- ✅ Conversation history management
- ✅ Synchronous (not async) for clean game loop

**Encounters & Loot**
- ✅ Location-based enemy tables
- ✅ Difficulty scaling
- ✅ Boss encounters with 5x XP
- ✅ Loot tables with equipment

**Audio & Voice**
- ✅ TTS narration (pyttsx3 offline, gTTS online)
- ✅ Voice selection and configuration
- ✅ Toggle TTS with `/voice` command

---

## v0.3.0 — Quest System, Parties & Relationships

**Status**: ✅ Complete — Deep story mechanics

### Highlights

**Quest System**
- ✅ NPC quest offers
- ✅ Branching objectives
- ✅ Quest completion tracking
- ✅ Experience and item rewards

**Multi-Character Parties**
- ✅ Recruit companions
- ✅ Party management
- ✅ Companion AI behavior
- ✅ Cooperative combat

**NPC Relationships**
- ✅ Trust and disposition tracking
- ✅ Faction reputation system
- ✅ NPC memory (who you've met)
- ✅ Relationship-based quest triggers

**World Events**
- ✅ Dynamic events with consequences
- ✅ Time advancement
- ✅ Location discovery
- ✅ Recent event tracking for narrative context

---

## v0.2.0 — Core Inventory & Equipment

**Status**: ✅ Complete — Item management and gear

### Highlights

- ✅ Item management with weight tracking
- ✅ Equipment slots (weapon, armor, accessory)
- ✅ Stat bonuses from equipment
- ✅ Inventory commands (`/inventory`, `/equipment`)
- ✅ Item discovery and drops

---

## v0.1.0 — Foundation

**Status**: ✅ Complete — Core game loop and world state

### Highlights

- ✅ Game loop with turn-based input
- ✅ Character creation (name, race, class)
- ✅ World state management
- ✅ Basic narration
- ✅ Command system
- ✅ LLM provider framework

---

## v0.9.1 — WorldDB cutover + MemoryAssembler tuning

**Status**: ✅ Shipping — Phase 3 cutover complete. The MemoryAssembler is
now default-on and the four tuning beads (batch snapshot, batch refs,
one-slot cache, narrator dedupe) are closed. No new mechanics; this is a
perf + polish release that finishes the v0.9 story.

### What's New in v0.9.1

- ✅ `memory.assembler_enabled` defaults to `True`. The WorldDB-backed
  MemoryAssembler is the narrator's primary context source out of the box.
  Set the flag to `false` to restore the legacy `WorldRAG.query_world`
  injection.
- ✅ Dead `WorldRAG.record_event` method deleted. It was defined but
  never called after v0.9 Phase 1 wired `_shadow_write_to_world_db` —
  Phase 3 was effectively complete the day Phase 1 landed.
- ✅ `MemoryAssembler._extract_entity_references` now issues a single FTS5
  OR-match per turn instead of one query per token (rag-quest-pvt).
- ✅ `MemoryAssembler._pull_entity_snapshots` now delegates to the new
  `WorldDB.get_entity_snapshot_batch` helper — one LEFT JOIN query in place
  of `get_entity` + `get_relationship` + `get_events_for_entity` per
  reference (rag-quest-696).
- ✅ `MemoryAssembler.assemble` memoizes the last block on
  `(turn_number, hash(input), location)` so repeated `look`/`wait` turns
  skip the whole rebuild (rag-quest-g13).
- ✅ `Narrator._call_llm` now delegates to `_build_llm_messages` instead
  of duplicating the prompt-building logic — removes a future divergence
  footgun (rag-quest-7uc).

---

## v0.9.0 — WorldDB Memory Architecture (Phases 1 + 2)

**Status**: ✅ Shipped — Phase 1 (shadow-write SQLite store) and Phase 2
(MemoryAssembler) both landed opt-in. Phase 3 (cut over `record_event`
away from LightRAG) was a side-effect of Phase 1 and was finished in
v0.9.1.

### What's New in v0.9.0

**WorldDB SQLite store (Phase 1)**
- ✅ Typed entity registry (NPCs, locations, factions, items, quests, bases) +
  append-only event log alongside the JSON save at
  `~/.local/share/rag-quest/saves/{slot}/world_db.sqlite`
- ✅ Shadow-writes from `engine/turn.py::collect_post_turn_effects` populate
  it from every `StateChange`, batched inside a single `with world_db.transaction():`
  block to collapse ~7 fsyncs/turn down to 1
- ✅ Shared `engine/state_event_mapping.py::state_change_to_writes` translator
  is the single source of truth for the `StateChange → WorldDB` mapping
- ✅ One-time migration from v3 saves (idempotent via metadata flag)
- ✅ FTS5 entity + event search (with LIKE fallback when FTS5 isn't compiled in)

**MemoryAssembler (Phase 2)**
- ✅ New `rag_quest/knowledge/memory_assembler.py` composes the §4.3 structured
  context block (CURRENT STATE / ENTITIES PRESENT / RECENT EVENTS / RELEVANT
  HISTORY / WORLD LORE / PLAYER ACTION) for the narrator
- ✅ Reads structured facts from WorldDB; LightRAG queried exactly once per
  turn, scoped to lore (Step 6 of the §4.1 pipeline)
- ✅ Three RAG profiles tune the §4.2 token budgets: `fast` (5 recent turns,
  small budgets), `balanced` (10, defaults), `deep` (15, larger budgets)
- ✅ Opt-in via `memory.assembler_enabled = true` and `memory.profile = ...`
  in `~/.config/rag-quest/config.json`. Default off so existing users see no
  behavior change until they flip the flag
- ✅ Narrator's new `_gather_external_context` helper transparently falls back
  to the legacy `WorldRAG.query_world` injection when the assembler isn't wired
- ✅ Step 5 (narrative echoes via FTS5) intentionally deferred to a v0.9.x
  follow-up — spec lists it as optional and the entity registry + event log
  already provide dramatically better continuity

**Authoritative spec**: [`docs/MEMORY_ARCHITECTURE.md`](MEMORY_ARCHITECTURE.md)

---

## Future Roadmap

### v0.9.2 — Narrative echoes + Timeline cutover

- Step 5 narrative echoes via FTS5 on `events.summary` (rag-quest-50j)
- Point `Timeline.record_from_state_change` at `state_event_mapping` and
  make Timeline a query/view layer over `WorldDB.events`
- Status: Scoped, awaiting v0.9.1 playtesting feedback

### v0.10 — iOS App & Offline Distribution

**Planned** (shifted from v0.9):
- SwiftUI iOS app
- Offline model distribution
- Apple ecosystem integration
- Touch UI for mobile
- Status: Pre-development

### v0.11 — Voice & Apple Intelligence

**Planned** (shifted from v0.8):
- Voice input (speak your actions)
- Voice output (AI reads narration)
- Apple Intelligence integration (on-device processing)
- Natural language improvements
- Status: Pre-development

### v1.0 — Stable Release

**Planned**:
- Stable API for third-party extensions
- Community mod support
- Advanced RAG features (custom entity types, relationships)
- Performance optimizations
- Status: Post-v0.10

---

## Key Principles

1. **LightRAG is the Foundation** — The knowledge graph is the "long-term memory," not the LLM
2. **Lightweight Narrator** — Keep the LLM small; let RAG provide context
3. **Local First** — Ollama + Gemma 4 should be the default experience
4. **No Hallucinations** — RAG grounding ensures narrative consistency
5. **Consumer Hardware** — Everything should run on a Mac or modest GPU
6. **Zero Friction** — Setup should be friendly and automatic
7. **Full Backwards Compatibility** — All saves and worlds should migrate cleanly

---

## Release Cadence

- Major versions (v0.x.0): 1-2 months between releases
- Bug fixes (v0.x.1): As needed
- Documentation: Continuous

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**Last Updated**: April 15, 2026 (v0.9.1 shipped — MemoryAssembler default-on, four tuning beads closed, dead `WorldRAG.record_event` removed)
