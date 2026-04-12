# Changelog

All notable changes to RAG-Quest. Authoritative version lives in `rag_quest/__init__.py`.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/). For anything not
captured here, `git log --oneline` is the source of truth.

**Maintenance rule**: add user-visible changes under `## [Unreleased]` in the same commit
as the code. When bumping `rag_quest.__version__`, rename `[Unreleased]` to the new
version and open a fresh `[Unreleased]` block above it. See `CLAUDE.md` → "Updating the
changelog" for the full convention.

## [Unreleased]

### Added
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
