# RAG-Quest Development Roadmap

A phased roadmap for RAG-Quest, an AI-powered D&D-style text RPG with LightRAG knowledge graph backend.

## v0.1 (Current) - Core Foundation

**Status**: Released

### Completed Features
- Core game engine with character, world, inventory, and quest systems
- Multi-provider LLM support (OpenAI, OpenRouter, Ollama) as first-class citizens
- LightRAG integration for knowledge graph-backed world context
- Narrative-driven gameplay with AI narrator
- Three start modes:
  - Fresh prompt setup
  - Interactive configuration menu
  - Lore document upload for custom worlds
- Rich terminal UI with colored output and formatted panels
- Game state serialization and persistence
- Lore ingestion from multiple file formats (txt, md, pdf)
- Natural language action processing
- Conversation history and context management

### Current Capabilities
- **Scope**: Narrative exploration, dialogue, inventory management
- **Supported Actions**: Movement, interaction, dialogue, investigation
- **Built-in Commands**: `/inventory`, `/quests`, `/look`, `/map`, `/status`, `/save`, `/help`
- **World Persistence**: Full game state + RAG database saved per world
- **Lore Support**: Custom lore documents ingested at world creation

### Known Limitations
- Single-player only
- No combat system (purely narrative)
- NPC interactions are reactive only
- Manual world generation (no procedural generation yet)
- Limited procedural content

---

## v0.2 - Combat & Character Depth

**Timeline**: Q2 2026  
**Focus**: Add strategic gameplay mechanics and character progression

### Features to Implement

#### Combat System
- [ ] Initiative and turn order
- [ ] Attack/defense mechanics with dice rolls
- [ ] Damage calculation (hit points, armor)
- [ ] Special abilities and spells per class
- [ ] Encounter difficulty scaling
- [ ] Combat log and action replay

#### Character Progression
- [ ] Experience and leveling system
- [ ] Skill trees and ability unlocking
- [ ] Equipment and weapon systems
- [ ] Stat growth and advancement
- [ ] Character specialization branches

#### Encounter Generation
- [ ] Dynamic enemy generation based on world context
- [ ] Loot tables and treasure distribution
- [ ] Boss encounters and unique enemies
- [ ] Difficulty balancing

#### Enhanced Narration
- [ ] Combat-specific narration prompts
- [ ] Action descriptions with damage feedback
- [ ] Victory/defeat scenarios
- [ ] Post-combat scene setting

### Technical Changes
- Add `Combat` class to engine
- Extend `Character` with experience and leveling
- Add `Enemy` and `Encounter` classes
- Update narrator with combat flow logic
- Extend RAG query context for encounter-relevant information

---

## v0.3 - Social & Narrative Depth

**Timeline**: Q3 2026  
**Focus**: Deepen NPC interactions and quest systems

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

### Technical Changes
- Add `Party` class for multi-character management
- Extend `NPC` with relationship and personality data
- Create `QuestChain` for quest dependencies
- Add event scheduling system
- Extend RAG to track relationship context

---

## v0.4 - Multiplayer & Persistence

**Timeline**: Q4 2026  
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
- [ ] Voice input for actions
- [ ] Text-to-speech narration
- [ ] Ambient music and sound effects
- [ ] Spatial audio for combat

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

### v0.2 Success Criteria
- [ ] Combat is engaging and balanced
- [ ] Character progression feels meaningful
- [ ] Average encounter duration: 5-15 minutes
- [ ] Combat win/loss rates balanced
- [ ] No major performance regressions

### v0.3 Success Criteria
- [ ] NPC relationships deepen engagement
- [ ] Quest chains are compelling and coherent
- [ ] Party mechanics feel natural
- [ ] Average session length: 30-60 minutes
- [ ] Narrative choices matter to players

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

---

## Technical Debt & Maintenance

Ongoing throughout all versions:
- Keep dependencies updated (quarterly)
- Monitor and optimize RAG query performance
- Expand test coverage (target: >85%)
- Improve error messages and debugging
- Performance profiling and optimization
- Security audits and updates

---

**Last Updated**: April 2026  
**Next Review**: June 2026

