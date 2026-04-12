# RAG-Quest Development Roadmap

A phased roadmap for RAG-Quest, an AI-powered D&D-style text RPG with LightRAG knowledge graph backend.

## Design Philosophy

**Core Principle**: LightRAG does the heavy lifting. The LLM acting as dungeon master is kept lightweight (Gemma 4 E2B/E4B—2-4B parameters, ≤8K context window) because it doesn't need to memorize the world. LightRAG's dual-level retrieval (entity + vector matching) injects precisely the relevant knowledge per query. This enables RAG-Quest to run entirely on consumer hardware with local models via Ollama.

This philosophy shapes every version and feature below.

---

## v0.5.1 (Current) - Polished for Everyone

**Status**: ✅ Complete — UX polish for non-developers, full backwards compatibility

### What's New in v0.5.1

**Friendly Setup**
- ✅ Automatic Ollama detection
- ✅ Clear, jargon-free setup wizard
- ✅ No command-line knowledge required

**Comprehensive Help System**
- ✅ `/help` shows all commands with examples
- ✅ Command-specific help with `/help <command>`
- ✅ Pro tips built into setup wizard

**Graceful Error Handling**
- ✅ User-friendly error messages instead of tracebacks
- ✅ Helpful suggestions for fixing common issues
- ✅ Automatic recovery from transient failures

**Smart Save Management**
- ✅ Auto-save on every turn
- ✅ Ctrl+C always offers to save before exit
- ✅ Save backup and disaster recovery

**Visual Rewards**
- ✅ Achievement notifications with fanfare
- ✅ Level-up celebrations with stat bonuses
- ✅ Treasure reveal animations
- ✅ Boss victory celebrations

---

## v0.5.0 - Multiplayer, Saves & World Sharing

**Status**: ✅ Complete — All features implemented, tested, and verified

### What's New in v0.5.0

**Persistent Save System**
- ✅ Multi-slot saves with metadata tracking (5+ independent slots)
- ✅ Auto-save rotation (keeps 3 most recent auto-saves)
- ✅ Export/import saves as `.rqsave` files
- ✅ Save format migration between versions
- ✅ SaveManager with centralized orchestration

**World Sharing & Templates**
- ✅ Export worlds as `.rqworld` packages
- ✅ Import community-created worlds
- ✅ 4 built-in starter worlds (Classic Dungeon, Enchanted Forest, Port City, War-Torn Kingdom)
- ✅ World validation and integrity checking
- ✅ Modular export/import system

**Local Multiplayer (Hot-Seat)**
- ✅ Turn-based multiplayer on same machine
- ✅ Shared world state across all players
- ✅ Item trading between players with negotiation
- ✅ Cooperative and PvP combat options
- ✅ MultiplayerSession with state synchronization

**Achievement System**
- ✅ 11 built-in achievements (Explorer, Warrior, Diplomat, Scholar, etc.)
- ✅ Automatic detection triggered on game events
- ✅ Progress tracking for multi-step achievements
- ✅ Real-time achievement notifications
- ✅ AchievementEngine for centralized management

**Procedural Dungeon Generation**
- ✅ Random dungeon generation with 5-15 rooms per level
- ✅ ASCII maps that reveal as you explore
- ✅ Room types: corridors, chambers, traps, treasures, boss rooms
- ✅ Difficulty-scaled enemies and loot
- ✅ DungeonGenerator with seeding support

**New Commands**
- ✅ `/saves` — List all save slots and metadata
- ✅ `/export` — Export current game to `.rqsave`
- ✅ `/import` — Import save file or world template
- ✅ `/multiplayer` — Start local multiplayer session
- ✅ `/trade` — Trade items between players
- ✅ `/achievements` — View achievement progress
- ✅ `/dungeon` — Enter procedurally generated dungeon

### Verification
- All save/load operations working with format migration
- World export/import with validation functional
- Multiplayer state sync and trading verified
- All 11 achievements triggered and tracked correctly
- Procedural dungeon generation producing valid ASCII maps
- All new commands implemented and functional

### Code Quality
- New packages: `saves/`, `worlds/`, `multiplayer/`
- New engine modules: `achievements.py`, `dungeon.py`
- Full type signatures and comprehensive error handling
- Backwards compatible with v0.4 save formats

---

## v0.4.1 - API Integration Fixes

**Status**: ✅ Complete — All 6 critical API bugs fixed and verified

### Bugs Fixed
- ✅ Inventory.list_items() returning formatted strings
- ✅ Party constructor accepting optional leader keyword
- ✅ RelationshipManager.add_npc() method added
- ✅ QuestLog.add_quest() accepting Quest objects
- ✅ EventType.CONFLICT added to enum
- ✅ Character.get_available_abilities() method added

### Inherited from v0.4.0
- Multi-character parties with companion AI
- NPC relationship system with faction reputation
- Multi-step quest chains with branching paths
- Dynamic world events affecting gameplay

---

## v0.4.0 - Social Dynamics, Parties & World Events

**Status**: ✅ Complete — All features implemented and tested

### Features
- ✅ Multi-character parties (up to 4 members)
- ✅ Companion AI with personality-driven behaviors
- ✅ NPC relationship system (trust, disposition, reputation)
- ✅ Faction reputation with faction-wide tracking
- ✅ Multi-step quest chains with branching paths
- ✅ Dynamic world events (10+ event types)
- ✅ Event consequences persisting in world state
- ✅ Loyalty system affecting companion behavior

### Commands Added
- `/party` — View party roster and status
- `/relationships` — See trust and disposition metrics
- `/factions` — View faction reputation
- `/recruit` — Invite NPC to party
- `/dismiss` — Remove companion from party
- `/events` — View active world events

---

## v0.3.0 - Combat, Progression & TTS

**Status**: ✅ Complete — All combat and progression systems working

### Features
- ✅ D&D combat with dice rolls (d4-d20), initiative, critical hits
- ✅ Character progression with 6 attributes and leveling to 10
- ✅ Equipment system with weapon, armor, and accessory slots
- ✅ Class abilities and progression-gated skills
- ✅ Encounter generation with scaling difficulty
- ✅ Loot tables and boss encounters (5x XP rewards)
- ✅ Text-to-speech narration (pyttsx3 and gTTS)
- ✅ Real LLM narrator with context injection

### Commands Added
- `/abilities` — List class abilities and unlocks
- `/equipment` — View equipped items
- `/voice` — Change TTS voice and settings

---

## v0.2.0 - MVP Release

**Status**: ✅ Complete — Fully playable core game

### Features
- ✅ Character creation and progression
- ✅ Location tracking and movement
- ✅ Combat system with HP and damage
- ✅ Inventory system with item discovery
- ✅ Quest system with NPC offers and tracking
- ✅ LightRAG knowledge graph integration
- ✅ Multi-provider LLM support (Ollama, OpenRouter, OpenAI)
- ✅ Three RAG profiles (fast, balanced, deep)
- ✅ Auto-save and error recovery
- ✅ Comprehensive documentation

### Commands
- `/inventory` — View and manage items
- `/quests` — View active quests
- `/look` — Examine current location
- `/map` — View world map
- `/status` — View character stats
- `/save` — Manual save
- `/help` — Command reference

---

## v0.6+ Vision — Advanced Features & Expansion

### v0.6 (Planned for 2026-Q3)
- **Cloud Save Sync** — Synchronize saves across devices
- **Asynchronous Multiplayer** — Play with friends online (turns-based)
- **Advanced Crafting** — Craft items from raw materials
- **Spell System** — Learn and cast spells with cooldowns
- **Mod Support** — Community-created content and scripts

### v0.7+ (2026-2027)
- **PvP Leaderboards** — Ranked multiplayer seasons
- **Mobile Companion App** — Manage party and inventory on phone
- **Native iOS/Android Clients** — Full mobile game
- **Biome System** — Regional themes with unique encounters
- **Seasonal Content** — Limited-time events and rewards

### Long-Term Vision (2027+)
- **Cross-Platform Play** — Web, mobile, desktop unified
- **Community Hub** — Share worlds, achievements, playthroughs
- **Advanced Procedural Generation** — Biome themes, region connectivity
- **Story Campaigns** — Campaign-length narrative arcs
- **Game Editor** — Build custom worlds with UI tools
- **API & Integrations** — Streaming, Discord bots, external tools

---

## Architecture Pillars

1. **LightRAG at the Core** — Knowledge graphs, not token memory
2. **Consumer Hardware** — 2-4B models on Ollama/local GPU
3. **Privacy First** — No mandatory cloud connectivity
4. **Extensibility** — Plugin systems, custom content, mod support
5. **Community Driven** — World sharing, achievements, leaderboards
6. **Quality Narrative** — Small models + excellent RAG = great stories

---

## Release Cadence

- **Major Versions** (v0.X.0): 6-8 months between releases
- **Minor Versions** (v0.X.Y): Bug fixes and small features, as needed
- **Playtest Cycle**: Extensive testing before each major release
- **Community Feedback**: Active issue tracking and feature requests via beads

For contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).
