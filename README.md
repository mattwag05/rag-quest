# RAG-Quest

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Version 0.5.1](https://img.shields.io/badge/version-0.5.1-green.svg)](https://github.com/mattwag05/rag-quest/releases/tag/v0.5.1)
[![Status: Stable](https://img.shields.io/badge/status-stable-green.svg)](docs/TEST_REPORT_v04.md)

> **An AI-powered D&D-style text RPG where a lightweight LLM narrator brings your world to life, powered by LightRAG's knowledge graph backbone. Now with persistent saves, world sharing, local multiplayer, achievements, and procedural dungeons.**

RAG-Quest is the first playable release of an AI-powered text adventure game that eliminates hallucinations through retrieval-augmented generation. Your dungeon master is a small language model (Gemma 4 E2B/E4B, 2-4B parameters) that doesn't need to memorize the world—instead, LightRAG's dual-level retrieval system injects precise context for every narrative decision. This architecture means you get GPT-4-quality narration from a model that runs on a Mac or modest GPU.

## What Makes RAG-Quest Different

**LightRAG Does the Heavy Lifting**: Unlike traditional AI storytellers that hallucinate contradictions and forget plot points, RAG-Quest grounds every response in a persistent knowledge graph. Your world state is facts, not tokens. The LLM is just the narrator.

**Consumer Hardware Friendly**: Runs entirely on Ollama with Gemma 4 E2B (2B, CPU-friendly) or E4B (4B, GPU-optimized). No API calls needed. No waiting for cloud services. Your game world is yours alone.

**Flexible LLM Providers**: Works seamlessly with:
- **Ollama** (recommended for local play) — free, fast, private
- **OpenRouter** — 100+ models, pay-per-use, cloud-hosted
- **OpenAI** — GPT-4, GPT-3.5-turbo, highest quality

## v0.5.0 Highlights — Multiplayer, Persistent Saves & World Sharing

**✨ Multi-Slot Save System**
- Save to 5+ independent slots with metadata tracking
- Auto-save rotation (keeps 3 most recent auto-saves)
- Export saves as `.rqsave` files for backup or sharing
- Import saves from other games
- Format migration between versions

**✨ World Sharing & Templates**
- Export worlds as `.rqworld` packages
- Import community worlds and templates
- 4 built-in starter worlds (Classic Dungeon, Enchanted Forest, Port City, War-Torn Kingdom)
- Validation and integrity checking

**✨ Local Multiplayer (Hot-Seat)**
- Turn-based multiplayer on the same machine
- Shared world state across all players
- Item trading between players
- Cooperative and PvP combat options
- Commands: `/multiplayer`, `/trade`, `/party`

**✨ Achievement System**
- 11 built-in achievements tracking exploration, combat, social, and progression milestones
- Automatic detection and notification
- Achievement progress tracking
- Command: `/achievements`

**✨ Procedural Dungeon Generation**
- Random dungeon generation with 5-15 rooms per level
- ASCII maps that reveal as you explore
- Room types: corridors, chambers, trap rooms, treasure rooms, boss rooms
- Difficulty-scaled enemies and loot based on level
- Command: `/dungeon`

## v0.5.1 — Polished for Everyone

**🎯 Friendly Setup** — No command-line knowledge required
- Automatic Ollama detection (just install it and go)
- Clear, jargon-free setup wizard
- Sensible defaults that work out of the box

**📖 Comprehensive Help System** — Learn as you play
- `/help` shows all commands with examples
- `/help <command>` for command-specific tips
- Pro tips built into the setup wizard

**😊 Graceful Error Handling** — User-friendly error messages
- Clear explanations instead of confusing tracebacks
- Helpful suggestions for fixing problems
- Automatic recovery from common issues

**💾 Smart Save Management** — Never lose progress
- Auto-save on every turn (configurable interval)
- Ctrl+C always prompts to save before exiting
- Save backups for disaster recovery

**🎉 Rewarding Milestones** — Celebrate your progress
- Clearer achievement notifications
- Level-up celebrations with stat bonuses
- Boss victory fanfare and treasure reveals

## Quick Install

```bash
# Option 1: Homebrew (recommended)
brew install mattwag05/tap/rag-quest

# Option 2: From source
git clone https://github.com/mattwag05/rag-quest.git
cd rag-quest
pip install -e .

# Option 3: From PyPI
pip install rag-quest
```

## Quick Start (5 Minutes)

> **No command-line experience needed!** The setup wizard is completely interactive and guides you through every step.

### 1. Install Ollama (if playing locally)

```bash
# Download from ollama.ai
# Then pull a recommended model:
ollama pull gemma4:e4b  # 4B, best quality (GPU)
ollama pull gemma4:e2b  # 2B, CPU-friendly
```

### 2. Start a Game

```bash
rag-quest
```

On first run, you'll see an interactive **Setup Wizard**. Choose one of three start modes:

**🌟 Mode 1: Fresh Adventure** — Start with a blank world
- Name your world and character
- Choose your race and class
- Let the narrator create dynamic encounters
- Default model: Gemma 4 (`gemma4:e4b` on Ollama)

**⚡ Mode 2: Quick Start Template** — Begin with a pre-built world
- Choose from 4 starter worlds (Classic Dungeon, Enchanted Forest, Port City, War-Torn Kingdom)
- Customize character name/race/class
- Jump straight into play with pre-configured lore

**📚 Mode 3: Upload Lore** — Build a custom world from PDFs/markdown
- Upload custom world documents (PDF, .md, .txt)
- System ingests lore into the knowledge graph
- Narrator draws from your custom world
- Best for existing worldbuilders

After setup, your configuration is saved to: **~/.config/rag-quest/config.json**

### 3. Configure Settings (Mid-Game)

Once playing, use the `/config` command to change settings without restarting:

```
> /config

Current Configuration:
  Provider: ollama
  Model: gemma4:e4b
  RAG Profile: balanced
  
Settings:
  1. Change LLM Provider
  2. Change Model
  3. Change RAG Profile (fast/balanced/deep)
  4. Auto-Save Interval
  5. Back to Game

Choose: > 
```

Your changes persist immediately to the config file.

### 4. Play

```
Welcome to Ebonvale Forest...

> I carefully approach the tavern and push open the wooden door

The tavern is dimly lit by candlelight. A hearth crackles in the corner.
Behind the bar stands a grizzled dwarf with a wry smile...

> I sit down and order a drink

The dwarf pours you a frothy ale. "Visitor, are ye? Dangerous times
in these woods. There's been talk of a dragon in the mountains..."

> /inventory
> /quests
> /map
> I ask the bartender about the dragon

...
```

## Features

### Game Mechanics
- **D&D Combat System** — Initiative, dice rolls (d4-d20), attack vs AC, damage calculation, critical hits
- **Character Progression** — Six attributes (STR/DEX/CON/INT/WIS/CHA), XP, leveling to 10, class abilities, equipment slots
- **Location Tracking** — Your character's position matters; locations persist and evolve
- **Dynamic Encounters** — Location-based enemy tables, difficulty scaling, boss encounters with 5x XP rewards
- **Inventory Management** — Find, carry, use, and lose items during gameplay
- **Quest System** — Multi-step quest chains with branching paths and NPC-specific storylines
- **Save System** — Auto-save every turn; load and resume any time
- **Multi-Character Parties** — Recruit NPCs as companions (up to 4 party members), companion AI with personality-driven behaviors
- **NPC Relationship System** — Trust and disposition tracking, faction reputation, relationship-gated dialogue and quests
- **World Events** — Dynamic world events (festivals, raids, storms, plagues, etc.) that affect game mechanics
- **Companion Mechanics** — Loyalty system affecting behavior, shared party objectives, inter-party dynamics

### v0.5.0 New Systems
- **Persistent Saves** — Multiple save slots, auto-save rotation, export/import
- **World Sharing** — Package and share worlds, 4 built-in starter templates
- **Local Multiplayer** — Hot-seat turn-based play with shared state
- **Achievements** — 11 built-in achievements, progression tracking
- **Procedural Dungeons** — Randomly generated dungeons with ASCII maps and scaling difficulty

### LightRAG Knowledge Graph
- **Persistent Knowledge Base** — Everything about your world is stored in a knowledge graph
- **Intelligent Retrieval** — Dual-level system: entity matching + vector similarity
- **Lore Ingestion** — Upload PDFs, markdown, or plain text; RAG automatically chunks and indexes
- **World Consistency** — No hallucinations; narrator always grounded in actual world knowledge
- **Extensible Format** — Add more lore mid-game; graph updates automatically

### LLM Providers (All First-Class Citizens)
| Provider | Best For | Cost | Speed | Setup |
|----------|----------|------|-------|-------|
| **Ollama** (Gemma 4 E2B/E4B) | Local play, privacy, cost | Free | 2-20s | Medium |
| **OpenRouter** | Flexibility, 100+ models | $0.005-0.15/turn | 1-5s | Easy |
| **OpenAI** | Highest quality | $0.05-0.30/turn | 3-10s | Easy |

### RAG Profiles (Speed vs Quality Tradeoff)
| Profile | Chunk Size | Query Type | Speed | Quality | Best For |
|---------|------------|-----------|-------|---------|----------|
| **fast** | 4000 chars | Naive vector | ⚡ Fastest | Lower | CPU-only, testing |
| **balanced** | 2000 chars | Entity-focused | Good | Good | Most users (recommended) |
| **deep** | 1000 chars | Hybrid (entity + graph) | Slower | ⭐ Excellent | Maximum immersion |

Configure via environment variable:
```bash
RAG_PROFILE=deep rag-quest
```

## New Commands in v0.5.0

| Command | Purpose |
|---------|---------|
| `/saves` | List all save slots and metadata |
| `/export` | Export current game to `.rqsave` file |
| `/import` | Import save file or world template |
| `/multiplayer` | Start local multiplayer session |
| `/trade` | Trade items between players |
| `/achievements` | View progress on all 11 achievements |
| `/dungeon` | Enter a procedurally generated dungeon |

## Character Creation

During setup, you'll create your character with guided prompts:

**Character Races** (with lore descriptions):
- **Human** — Adaptable and ambitious, jack of all trades
- **Elf** — Graceful and long-lived, masters of magic and archery
- **Dwarf** — Hardy and honorable, builders and miners
- **Tiefling** — Mystical and mysterious, outsiders with dark fates
- **Orc** — Strong and fierce, misunderstood barbarians
- **Halfling** — Small but brave, lucky adventurers

**Character Classes** (with unique ability trees):
- **Fighter** — Melee combat specialist, heavy armor mastery
- **Ranger** — Bow mastery, tracking, wilderness survival
- **Rogue** — Stealth, critical strikes, lockpicking
- **Cleric** — Healing magic, buffs, support spellcasting
- **Wizard** — Ranged magic, area effects, knowledge
- **Barbarian** — Rage mechanics, two-handed weapons, tank

Each class gets unique abilities that unlock as you level up (max level 10).

## Example Gameplay

### Creating a World

```
RAG-Quest: New Game Setup

LLM Provider? [openai/openrouter/ollama] > ollama
Ollama Model? [gemma4:e4b] > gemma4:e4b
RAG Profile (speed vs fidelity)? [fast/balanced/deep] > balanced

World Name? > The Shattered Citadel
World Setting? > Post-apocalyptic ruins
World Tone? > Dark and mysterious

Character Name? > Kael
Character Race? > Human
Character Class? > Ranger

Upload lore? (txt/md/pdf paths, space-separated) > lore/shattered_citadel.pdf
Ingesting lore... ████████████████████ 100%

Creating game... Done!
```

### Playing the Game

```
═══════════════════════════════════════════════════════════════════════════════
  THE SHATTERED CITADEL — Post-Apocalyptic Ruins  |  Time: Dawn  |  Weather: Overcast
═══════════════════════════════════════════════════════════════════════════════

📍 LOCATION: Rusted Plaza
Broken towers loom overhead, their facades crumbling. Vines creep across ancient
stone. The smell of rust and decay fills the air. You notice a path leading east
to the collapsed library, and north toward a makeshift shelter...

💚 KAEL | HP: 30/30 | Level 1 | Ranger
📦 Inventory: Worn Backpack (5/20), Water Canteen, Rope, Knife
⚔️  Active Quests: Find the Safehouse (Main)

> I carefully move north toward the shelter, staying alert

You cautiously approach the makeshift shelter, hand on your knife. As you draw
near, you see it's built from salvaged metal and wood. Smoke curls from a small
opening. A figure emerges—a grizzled woman with a rifle. She eyes you warily...

> I raise my hands peacefully and approach

"Easy, friend," she says, lowering her weapon slightly. "Name's Vera. Been
guarding this place for months. Most folks 'round here ain't friendly. You look
like you got a story..." She gestures to the shelter. "Care for some tea?"

> /quests
Active Quests:
  - Find the Safehouse [IN PROGRESS] — Vera has clues about it

> I ask Vera about the safehouse

"The safehouse? That's a legend..." she says, settling into a rusted chair.
"But three weeks back, I found a map. A real one, not some tale. It's marked
on old paper, showing a route to the old military bunker below the citadel..."

✨ NEW QUEST: Vera's Map — Find the Military Bunker

> I take the map and thank her

You carefully take the worn map from Vera's hands. It's old—maybe from before
the collapse. An X marks a location at what looks like the eastern ruins. Vera
hands you supplies: food rations and a rusted key.

You gain: Food Rations (x3), Old Bunker Key

═══════════════════════════════════════════════════════════════════════════════
```

## Installation & Configuration

### Requirements
- **Python 3.11+**
- **Ollama** (for local play) — or API credentials for OpenAI/OpenRouter

### Environment Variables (Optional, for Non-Interactive Setup)

```bash
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=gemma4:e4b
export OLLAMA_BASE_URL=http://localhost:11434
export RAG_PROFILE=balanced

export WORLD_NAME="The Shattered Citadel"
export WORLD_SETTING="Post-apocalyptic"
export WORLD_TONE="Dark"

export CHARACTER_NAME="Kael"
export CHARACTER_RACE=HUMAN
export CHARACTER_CLASS=RANGER

export SAVE_DIR=~/.local/share/rag-quest/saves
export AUTO_SAVE_INTERVAL=5

rag-quest
```

### Config File Location

Configuration is saved to: `~/.config/rag-quest/config.json`

Game saves are stored at: `~/.local/share/rag-quest/saves/`

RAG databases live at: `~/.local/share/rag-quest/worlds/`

## v0.5.0 Release Notes

### New in v0.5.0 - Multiplayer, Persistent Saves & World Sharing

**Persistent Save System** ✅
- Multiple save slots with metadata tracking
- Auto-save rotation (keeps 3 most recent)
- Export/import saves as `.rqsave` files
- Save format migration between versions

**World Sharing** ✅
- Export worlds as `.rqworld` packages
- Import community-created worlds
- 4 built-in starter worlds (Classic Dungeon, Enchanted Forest, Port City, War-Torn Kingdom)
- World validation and integrity checking

**Local Multiplayer** ✅
- Hot-seat turn-based multiplayer on the same machine
- Shared world state across all players
- Item trading between players
- Cooperative and PvP combat options

**Achievement System** ✅
- 11 built-in achievements tracking exploration, combat, social, and progression milestones
- Automatic detection and notification

**Procedural Dungeons** ✅
- Random dungeon generation with 5-15 rooms
- ASCII map that reveals as you explore
- Room types: corridors, chambers, trap rooms, treasure rooms, boss rooms
- Difficulty-scaled enemies and loot

### Inherited from v0.4.1
- Multi-character parties with companion AI
- NPC relationship system with faction reputation
- Multi-step quest chains with branching paths
- Dynamic world events affecting gameplay
- D&D combat with dice rolls and critical hits
- Character progression to level 10 with class abilities
- Text-to-speech narration
- All 6 critical API integration bugs fixed

### v0.3.0 Features (Inherited)
- D&D-style combat with dice rolls and class abilities
- Character progression with leveling and equipment
- Dynamic encounter generation with loot
- Text-to-speech narrator (TTS)
- Real LLM narrator with context injection and error recovery

### v0.2.0 Features (Inherited)
- Full game engine with character, world, inventory, quests
- Location tracking and movement with narrator integration
- Combat system mechanics with HP and damage
- LightRAG knowledge graph with dual-level retrieval
- Multi-provider LLM support (OpenAI, OpenRouter, Ollama)
- Save/load system with auto-save
- Three RAG profiles (fast, balanced, deep)

## Roadmap

### v0.5 — Now Live ✅
- ✅ Multi-slot save system with auto-save rotation
- ✅ World sharing via .rqworld packages
- ✅ 4 built-in starter worlds
- ✅ Local multiplayer (hot-seat)
- ✅ Achievement system (11 achievements)
- ✅ Procedural dungeon generation

### v0.6+ (Coming 2026-2027)
- Cloud save synchronization
- Asynchronous multiplayer (turns-based online)
- Advanced spell and crafting systems
- PvP leaderboards and seasons
- Mod support and script engine
- Mobile companion app
- Native iOS/Android clients
- Advanced procedural generation (biomes, region themes)

## Contributing

RAG-Quest is open source and welcomes contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

All issues tracked via beads (`bd`):
```bash
bd list        # See open issues
bd create ...  # File a new issue
bd show <id>   # View issue details
```

## Architecture Philosophy

**LightRAG Does the Heavy Lifting**: Every design decision prioritizes keeping the LLM lightweight while making the knowledge graph do the actual work.

- **Small Models Work**: 2-4B parameter models (Gemma 4 E2B/E4B) with RAG often outperform much larger models without RAG
- **Consumer Hardware**: Entire game runs on a Mac or modest GPU; no expensive cloud inference required
- **Privacy First**: With Ollama, everything stays local—no data leaves your machine
- **Extensible Providers**: Add new LLM providers easily via the `BaseLLMProvider` interface

See [CLAUDE.md](CLAUDE.md) for technical architecture and [AGENTS.md](AGENTS.md) for LLM provider details.

## Getting Help

- **Start Playing**: `rag-quest` and follow the interactive setup
- **Read Docs**: Check [CLAUDE.md](CLAUDE.md), [AGENTS.md](AGENTS.md), [ROADMAP.md](ROADMAP.md)
- **Report Issues**: Use `bd create` or open a GitHub issue
- **Share Worlds**: Upload custom lore documents during game setup

## License

MIT License. See [LICENSE](LICENSE) for details.

---

**v0.5.0 Release — Multiplayer, Persistent Saves, World Sharing, Achievements & Procedural Dungeons!**

Built with ❤️ for solo and group play. Designed to run on your hardware. Powered by LightRAG, lightweight LLMs, and immersive AI narration.
