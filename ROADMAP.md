# RAG-Quest Development Roadmap

A phased roadmap for RAG-Quest, an AI-powered D&D-style text RPG with LightRAG knowledge graph backend.

## Design Philosophy

**Core Principle**: LightRAG does the heavy lifting. The LLM narrator is kept lightweight (Gemma 4 E2B/E4B—2-4B parameters, ≤8K context) because it doesn't memorize the world. LightRAG's dual-level retrieval (entity + vector matching) injects precisely the relevant knowledge per query. This enables RAG-Quest to run entirely on consumer hardware with local models via Ollama.

This philosophy shapes every version.

---

## v0.5.3 (Current) — Tutorial & User Guide

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

## Future Roadmap

### v0.6 — Web UI & Streaming

**Planned**:
- Web interface for browser-based play
- Streaming responses (see narration as it's generated)
- Cloud deployment option
- Save sync across devices
- Status: Pre-development

### v0.7 — iOS App & Offline Distribution

**Planned**:
- SwiftUI iOS app
- Offline model distribution
- Apple ecosystem integration
- Touch UI for mobile
- Status: Pre-development

### v0.8 — Voice & Apple Intelligence

**Planned**:
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
- Status: Post-v0.8

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

**Last Updated**: April 2026
