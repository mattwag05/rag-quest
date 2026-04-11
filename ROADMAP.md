# RAG-Quest Development Roadmap

A phased roadmap for RAG-Quest, an AI-powered D&D-style text RPG with LightRAG knowledge graph backend.

## Design Philosophy

**Core Principle**: LightRAG does the heavy lifting. The LLM acting as dungeon master is kept lightweight (Gemma 4 E2B/E4B—2-4B parameters, ≤8K context window) because it doesn't need to memorize the world. LightRAG's dual-level retrieval (entity + vector matching) injects precisely the relevant knowledge per query. This enables RAG-Quest to run entirely on consumer hardware with local models via Ollama.

This philosophy shapes every version and feature below.

---

## v0.1 (Current) - Core Foundation

**Status**: Early Alpha - Game loop functional, gameplay mechanics incomplete

### Completed Features
- Core game engine with character, world, inventory, and quest systems
- Multi-provider LLM support (OpenAI, OpenRouter, Ollama) as first-class citizens
- LightRAG integration for knowledge graph-backed world context
- Lightweight narrator agent powered by RAG context injection
- Configuration via .env or interactive setup with environment variable fallback
- Rich terminal UI with colored output and formatted panels
- Game state serialization and persistence
- Lore ingestion from multiple file formats (txt, md, pdf)
- Natural language action processing
- Conversation history and context management
- All 6 critical bugs fixed (async/await, config, PDF ingestion, constructors, packages)

### Current Capabilities
- **Scope**: Narrative exploration, dialogue, inventory management
- **Supported Actions**: Movement, interaction, dialogue, investigation
- **Built-in Commands**: `/inventory`, `/quests`, `/look`, `/map`, `/status`, `/save`, `/help`
- **World Persistence**: Full game state + RAG database saved per world
- **Lore Support**: Custom lore documents ingested at world creation
- **Hardware Support**: Runs on consumer hardware with Ollama + Gemma 4 E2B/E4B models
- **Test Coverage**: 35-turn playthrough with 100% completion rate

### Known Limitations & v0.1.1 Targets (From Playtest)

The following P2 issues must be fixed before gameplay feels complete:

1. **Character Location Not Updating** (rag-quest-jjc)
   - Character stays at starting location despite actions
   - Narrator must parse location keywords from responses and update state
   
2. **No Combat System Integration** (rag-quest-y1u)
   - Combat described narratively but no mechanical integration
   - Narrator must connect to combat system, track HP, parse outcomes
   
3. **Inventory Not Used During Gameplay** (rag-quest-m2u)
   - Items exist but never affect narrative or game mechanics
   - Narrator must parse item discovery/loss and update inventory
   
4. **Quest Log Not Integrated** (rag-quest-0ia)
   - Quests offered but never tracked or completed
   - Narrator must generate offers and mark completion

### v0.1.1 Targets (Planned)

**Timeline**: April 2026 (immediate follow-up)

Fix the 4 P2 issues above. Target deliverable:
- Character location updates during gameplay
- Combat mechanics actually affect character state
- Inventory used in action resolution
- Quest system offers and tracks quests
- 35-turn playthrough with gameplay mechanics working

**Implementation approach**: Enhance `Narrator._parse_and_apply_changes()` to detect and apply state changes from LLM responses using regex patterns and rule-based parsing.

### P3 Issues (Completed in v0.1.1 - April 11, 2026)

All three P3 issues have been addressed with comprehensive solutions:

1. **PDF Ingestion Extremely Slow** ✓
   - Implemented intelligent chunking with RAGProfileConfig
   - Added file hash caching to skip re-ingestion of unchanged files
   - Added PDF progress reporting with progress bars
   - Profile-aware chunk sizes (4000 for fast, 1000 for deep)
   - Chunking respects section boundaries for better coherence

2. **Insufficient Narrator Context Injection** ✓
   - Created multi-source context injection: location, character, action, recent events
   - Added specialized RAG queries for different context types
   - Enhanced system prompts with comprehensive game state
   - Better formatting of retrieved context for LLM consumption

3. **No Error Recovery** ✓
   - Implemented retry logic with exponential backoff (up to 3 retries)
   - Added graceful fallback responses when LLM fails
   - Wrapped all RAG queries in try/except with safe defaults
   - Added frequent auto-save (every 3 actions) to protect progress
   - Error counter to warn when too many failures in a row

**New Feature: RAG Profiles** ✓
- Three user-configurable profiles: fast, balanced, deep
- Profiles optimize chunk size, query mode, and token limits
- Configuration via environment variable or interactive setup
- Intelligent PDF chunking with section detection
- File hash caching for smart change detection
- Profile-aware ingestion reporting

---

## v0.2 - Combat & Character Depth

**Timeline**: Q2-Q3 2026  
**Focus**: Add strategic gameplay mechanics and character progression

### Features to Implement

#### Combat System
- [ ] Initiative and turn order (dice rolls)
- [ ] Attack/defense mechanics with hit/miss resolution
- [ ] Damage calculation and HP management
- [ ] Special abilities and spells per class
- [ ] Encounter difficulty scaling
- [ ] Combat log and action replay
- [ ] Multiple enemy encounters

#### Character Progression
- [ ] Experience and leveling system
- [ ] Skill trees and ability unlocking
- [ ] Equipment and weapon systems
- [ ] Stat growth and advancement
- [ ] Character specialization branches (subclasses)

#### Encounter Generation
- [ ] Dynamic enemy generation based on location and difficulty
- [ ] Loot tables and treasure distribution
- [ ] Boss encounters and unique enemies
- [ ] Difficulty balancing relative to party level

#### Enhanced Combat Narration
- [ ] Combat-specific narration prompts
- [ ] Action descriptions with damage feedback
- [ ] Victory/defeat scenarios
- [ ] Post-combat loot descriptions and experience gain

### Technical Changes
- Add `Combat` class to engine with turn management
- Extend `Character` with experience, level, abilities
- Add `Enemy`, `Loot`, and `Encounter` classes
- Update narrator with combat flow logic
- Extend RAG query context for encounter-relevant information
- Add dice rolling system with configurable mechanics

### Narrator Philosophy for v0.2
- Combat description generation uses same RAG-powered lightweight narrator
- RAG provides encounter context (difficulty, loot, environment)
- Small LLM model sufficient—RAG handles world knowledge
- Combat results parsed and applied to game state

---

## v0.3 - Social & Narrative Depth

**Timeline**: Q3-Q4 2026  
**Focus**: Deepen NPC interactions and quest systems, add immersive narration

### Features to Implement

#### Multi-Character Parties
- [ ] Party formation and management
- [ ] Multi-character turn order in combat
- [ ] Individual skill and ability specialization
- [ ] Shared inventory with party pooling
- [ ] Party-level quests vs. individual missions
- [ ] Companion AI and companion interactions

#### NPC Relationship System
- [ ] NPC reputation tracking
- [ ] Relationship depth and faction loyalty
- [ ] NPC dialogue variations based on relationship
- [ ] Companion recruitment and romance arcs
- [ ] NPC proactive actions (encounters initiated by NPCs)
- [ ] Dialogue trees with consequence branching

#### Quest Chains
- [ ] Multi-part quest chains
- [ ] Dynamic quest generation from world events
- [ ] Quest failure states and consequences
- [ ] Branching narratives based on choices
- [ ] Repeatable vs. one-time quests
- [ ] Quest reward customization

#### World Events
- [ ] Timed world events (seasonal, periodic)
- [ ] Faction conflicts and political intrigue
- [ ] NPC death and story impact
- [ ] Dynamic location changes
- [ ] World-state persistence across saves

#### **AI Dungeon Master Text-to-Speech Narration** ⭐
- [ ] **Text-to-speech engine integration (gTTS, pyttsx3, or similar)**
- [ ] **Narrator voice selection and customization**
- [ ] **Spatial audio hints for immersion (optional)**
- [ ] **TTS for quest descriptions and dialogue**
- [ ] **Optional: user audio playback control (play/pause/skip)**
- [ ] **Audio caching for repeated narration**
- [ ] **Config option to enable/disable TTS**

**Rationale**: Hearing the dungeon master narrate the world deepens immersion. Text-to-speech is lightweight and complements the lightweight LLM approach. Voice narration elevates the player experience without requiring pre-recorded audio. This is a major quality-of-life improvement that makes the game feel more like a real tabletop experience.

### Technical Changes
- Add `Party` class for multi-character management
- Extend `NPC` with relationship and personality data
- Create `QuestChain` for quest dependencies
- Add event scheduling system
- Extend RAG to track relationship context
- **Add TTS module with voice selection and streaming audio**
- **Integrate TTS output alongside text responses**
- Add dialogue tree system for branching narratives

### Narrator Philosophy for v0.3
- NPC dialogue and narration still powered by lightweight LLM + RAG
- RAG provides NPC context, relationship history, lore references
- TTS reads narrator output aloud—no additional LLM calls needed
- Small model still sufficient; RAG handles all knowledge

---

## v0.4 - Multiplayer & Persistence

**Timeline**: Q4 2026 - Q1 2027  
**Focus**: Enable shared worlds and long-term persistence

### Features to Implement

#### Multiplayer Support
- [ ] Shared world state via Tailscale or similar
- [ ] Player character presence and synchronization
- [ ] Cooperative gameplay modes
- [ ] Shared inventory and trading
- [ ] PvP encounter options
- [ ] World ownership and access control

#### Persistent Saves
- [ ] Cloud save synchronization
- [ ] Multiple save slots
- [ ] Character import/export
- [ ] Branching saves and alternate timelines
- [ ] Autosave with recovery options

#### World Persistence & Sharing
- [ ] Export world to shareable format
- [ ] Import community-created worlds
- [ ] World versioning and updates
- [ ] Template worlds for quick starts
- [ ] Community world repository

#### Long-Term Content
- [ ] Seasonal events and updates
- [ ] Procedural dungeon generation
- [ ] Dynamic world evolution over game time
- [ ] Legacy mechanics (consequences carry forward)
- [ ] Achievement system

### Technical Changes
- Implement multiplayer state sync (likely Tailscale integration)
- Create world export/import serialization
- Add authentication and access control
- Extend save system for branching
- Create community content distribution system

---

## Future Vision (Post v0.4)

### Voice & Audio
- [ ] Voice input for actions (speech-to-text)
- [ ] **AI narrator TTS output (added in v0.3)**
- [ ] Ambient music and sound effects
- [ ] Spatial audio for combat encounters

### Visual Enhancements
- [ ] ASCII art maps and scene rendering
- [ ] AI-generated scene images (via DALL-E or similar)
- [ ] Dynamic terminal theming per world
- [ ] Animated transitions and effects

### Web & Mobile
- [ ] Web UI alongside terminal version
- [ ] REST API for bot integrations
- [ ] Mobile web client
- [ ] Telegram bot integration for remote play
- [ ] Discord bot for world notifications

### Advanced Mechanics
- [ ] Spell research and invention
- [ ] Crafting and alchemy systems
- [ ] Political intrigue and alliances
- [ ] Pet/animal companion systems
- [ ] Magic system with learning

### Apple Intelligence Foundation Models

**Timeline**: Post v0.4 / Future Vision

Native integration with Apple's on-device foundation models as an LLM provider. On Apple Silicon Macs and iPhones/iPads, RAG-Quest can run entirely offline without needing Ollama, using Apple's private on-device inference:

- [ ] Apple Intelligence provider implementation
- [ ] On-device inference for Mac (Apple Silicon)
- [ ] Privacy-first—no data sent to cloud
- [ ] Seamless integration with existing provider architecture
- [ ] Offline-first gameplay on Apple devices

**Why this matters**: Users with Apple Silicon hardware (M-series Macs, iPhone 16 Pro+) can play RAG-Quest with zero external dependencies—just the game, LightRAG, and Apple's foundation models. Gameplay stays private and fast on their device.

### iOS App with SwiftUI Interface

**Timeline**: Post v0.4 / Future Vision  
**Foundation**: Builds on Apple Intelligence Foundation Models integration

Native iOS and iPadOS app bringing RAG-Quest to iPhone and iPad with seamless touch-optimized gameplay:

#### Core Features
- [ ] Native SwiftUI interface designed for mobile gameplay
- [ ] Touch-optimized action UI (gesture-based movement, quick actions)
- [ ] On-device LLM inference via Apple Intelligence foundation models
- [ ] Lightweight on-device LightRAG variant for offline knowledge graph queries
- [ ] Rich text rendering with advanced typography for narrator output
- [ ] Haptic feedback system for gameplay events (combat hits, critical strikes, world events)
- [ ] Full-featured inventory and character sheet interfaces

#### Persistence & Sharing
- [ ] iCloud CloudKit sync for save files and character data
- [ ] Seamless sync between iOS and macOS versions
- [ ] World export/import via AirDrop and iCloud
- [ ] Campaign sharing with other players via AirDrop
- [ ] Automatic cloud backup with conflict resolution

#### User Experience
- [ ] Split-view support for iPad (narrative on left, actions on right)
- [ ] Dark mode optimized for extended play sessions
- [ ] Portrait and landscape orientation support
- [ ] Keyboard and gamepad support for iPad
- [ ] Custom action quick-bar for frequent commands
- [ ] Audio narrator integration (TTS from v0.3) with speaker output and volume control

#### Companion macOS Support
- [ ] SwiftUI multiplatform codebase (iOS/iPadOS/macOS)
- [ ] Mac version with optimized desktop UI
- [ ] Seamless game state sync across all Apple platforms
- [ ] Native menu bar integration on macOS
- [ ] Share worlds between mobile and desktop seamlessly

#### Technical Architecture
- [ ] Shared Swift foundation with platform-specific UI layers
- [ ] On-device LightRAG using Core Data or similar local persistence
- [ ] Apple Intelligence framework integration for LLM inference
- [ ] CloudKit schema for multiplayer save sync
- [ ] Haptic Engine integration (iOS) and Haptics framework (macOS)
- [ ] AVFoundation for TTS audio playback

**Why this matters**: RAG-Quest on mobile is pure immersion. Players can explore worlds during commutes, breaks, or relaxation time. With on-device Apple Intelligence and lightweight LightRAG, everything runs privately and instantly on their phone—no cloud dependency, no latency. Haptic feedback transforms the tactile experience, making discoveries and combat visceral. iCloud sync means your campaign seamlessly follows you from phone to iPad to Mac.

**Implementation notes**: 
- The lightweight LLM + LightRAG architecture enables this—too much compute overhead would be impossible on mobile
- Apple Intelligence on-device models are optimized for privacy and latency, making them ideal for mobile RPG narration
- Share via AirDrop leverages iOS native conventions for seamless social play
- Haptic feedback is surprisingly impactful in text-based games, providing crucial sensory feedback for narrative impact

### Ecosystem
- [ ] Official world templates
- [ ] Community modding support
- [ ] Plugin system for custom mechanics
- [ ] LLM provider abstraction improvements
- [ ] Analytics and metrics (opt-in)

### Performance & Scalability
- [ ] Ray or Dask for distributed computation
- [ ] Vector database for RAG scaling
- [ ] Caching strategies for large worlds
- [ ] Batch processing for world initialization
- [ ] Streaming for large narrative outputs

---

## Success Metrics

### v0.1 Success Criteria
- ✅ Core engine is stable and playable
- ✅ Multi-provider support works reliably
- ✅ LightRAG improves narrative consistency
- ✅ Documentation is comprehensive
- ✅ Users can create custom worlds
- ✅ Runs on consumer hardware with Ollama
- ✅ 35-turn playthrough with 100% success rate
- ⏳ Game mechanics respond to player actions (v0.1.1 target)

### v0.1.1 Success Criteria (Upcoming)
- [ ] Character location updates correctly
- [ ] Combat affects character HP
- [ ] Inventory used in action resolution
- [ ] Quests offered and tracked
- [ ] 35+ turn playthrough with full mechanics
- [ ] All 7 beads issues closed

### v0.2 Success Criteria
- [ ] Combat is engaging and balanced
- [ ] Character progression feels meaningful
- [ ] Average encounter duration: 5-15 minutes
- [ ] Combat win/loss rates balanced
- [ ] No major performance regressions
- [ ] Narrator still works with lightweight models

### v0.3 Success Criteria
- [ ] NPC relationships deepen engagement
- [ ] Quest chains are compelling and coherent
- [ ] Party mechanics feel natural
- [ ] Average session length: 30-60 minutes
- [ ] Narrative choices matter to players
- [ ] **TTS narration enhances immersion**
- [ ] **TTS doesn't significantly impact performance**

### v0.4 Success Criteria
- [ ] Multiplayer sessions are stable
- [ ] Community worlds are being shared
- [ ] Persistent saves improve replay value
- [ ] Player retention metrics improve
- [ ] Scalability supports 100+ concurrent players

---

## Contributing to the Roadmap

Have ideas? Want to help? Check [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Submitting feature proposals
- Reporting bugs and issues
- Contributing code and documentation
- Sharing custom worlds and lore

Use beads (`bd`) for all issue tracking:
```bash
bd list          # See all issues
bd create -t "title" -d "description" -p P2  # File new issue
bd show <id>     # View details
bd update <id> --claim  # Start work
bd close <id>    # Complete work
```

---

## Technical Debt & Maintenance

Ongoing throughout all versions:
- Keep dependencies updated (quarterly)
- Monitor and optimize RAG query performance
- Expand test coverage (target: >85%)
- Improve error messages and debugging
- Performance profiling and optimization
- Security audits and updates
- **Maintain LightRAG-first architecture in all changes**

---

## Current Status (2026-04-11)

**v0.1 is functionally complete** but gameplay is incomplete. The game loop works perfectly, narrative generation is solid, and the RAG system is stable. What's missing are game mechanics that respond to player actions.

**Next focus**: v0.1.1 targets (location tracking, combat integration, inventory usage, quest system). These are straightforward enhancements to the Narrator state parsing logic.

---

**Last Updated**: April 11, 2026  
**Next Review**: May 2026

**Core Principle**: Every feature should work well with a lightweight LLM + strong RAG. If it doesn't, reconsider the architecture.
