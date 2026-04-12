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
