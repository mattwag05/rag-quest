# RAG-Quest

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Version 0.2.0](https://img.shields.io/badge/version-0.2.0%20MVP-brightgreen.svg)](https://github.com/mattwag05/rag-quest/releases/tag/v0.2.0)

> **An AI-powered D&D-style text RPG where a lightweight LLM narrator brings your world to life, powered by LightRAG's knowledge graph backbone.**

RAG-Quest is the first playable release of an AI-powered text adventure game that eliminates hallucinations through retrieval-augmented generation. Your dungeon master is a small language model (Gemma 4 E2B/E4B, 2-4B parameters) that doesn't need to memorize the world—instead, LightRAG's dual-level retrieval system injects precise context for every narrative decision. This architecture means you get GPT-4-quality narration from a model that runs on a Mac or modest GPU.

## What Makes RAG-Quest Different

**LightRAG Does the Heavy Lifting**: Unlike traditional AI storytellers that hallucinate contradictions and forget plot points, RAG-Quest grounds every response in a persistent knowledge graph. Your world state is facts, not tokens. The LLM is just the narrator.

**Consumer Hardware Friendly**: Runs entirely on Ollama with Gemma 4 E2B (2B, CPU-friendly) or E4B (4B, GPU-optimized). No API calls needed. No waiting for cloud services. Your game world is yours alone.

**Flexible LLM Providers**: Works seamlessly with:
- **Ollama** (recommended for local play) — free, fast, private
- **OpenRouter** — 100+ models, pay-per-use, cloud-hosted
- **OpenAI** — GPT-4, GPT-3.5-turbo, highest quality

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

You'll see an interactive setup menu:
- Choose your LLM provider (OpenAI, OpenRouter, or Ollama)
- Select a RAG profile (fast/balanced/deep)
- Name your world and character
- Optionally upload custom lore (PDF, markdown, text)

### 3. Play

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
- **Location Tracking** — Your character's position matters; locations persist and evolve
- **Combat System** — Turn-based battles with HP, damage calculation, and encounter difficulty
- **Inventory Management** — Find, carry, use, and lose items during gameplay
- **Quest System** — Receive quests from NPCs, track objectives, earn rewards
- **Character Progression** — Experience, leveling, attributes, class abilities
- **Save System** — Auto-save every turn; load and resume any time

### LightRAG Knowledge Graph
- **Dual-Level Retrieval** — Entity matching + vector similarity for precise context injection
- **World Persistence** — Every event, NPC, location, and discovery lives in the knowledge graph
- **PDF Lore Ingestion** — Upload your custom world lore; RAG extracts and grounds all narration in it
- **Intelligent Chunking** — Three RAG profiles optimize chunk size and query depth for your hardware
- **Smart Caching** — File hash caching skips re-ingestion of unchanged documents

### Terminal UI
- **Rich Panels** — Colored output with formatted panels for narrative, status, and commands
- **ASCII Art** — Visual scene descriptions and maps (in development)
- **Status Bar** — HP, location, inventory summary always visible
- **Natural Actions** — Type what you want to do; the AI understands intent and context

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

rag-quest
```

### Config File Location

Configuration is saved to: `~/.config/rag-quest/config.json`

Game saves are stored at: `~/.local/share/rag-quest/saves/{world_name}.json`

RAG databases live at: `~/.local/share/rag-quest/worlds/{world_name}/`

## v0.2.0 Changelog

### New in v0.2.0 MVP

**Game Loop & Mechanics** ✅
- Core game engine with character, world, inventory, quests fully working
- 50-turn playtest completed successfully with all systems functional
- Location tracking and movement
- Combat system with HP and damage calculation
- Inventory system with item discovery and usage
- Quest system with NPC offers and completion tracking

**LightRAG Knowledge Graph** ✅
- Multi-level knowledge retrieval (entity + vector matching)
- World persistence across saves
- Lore ingestion from PDF, markdown, and text files
- Intelligent chunking with section boundary detection
- File hash caching for smart re-ingestion

**LLM Providers** ✅
- OpenAI (GPT-4, GPT-3.5-turbo)
- OpenRouter (100+ models)
- Ollama (local, free, private)
- Synchronous architecture for turn-based gameplay

**RAG Profiles** ✅
- Three configurable profiles: fast, balanced, deep
- Profile-aware chunk sizes and query depths
- Speed vs quality tradeoff configurable per user

**Terminal UI** ✅
- Rich colored output with formatted panels
- Status bar with character HP, location, inventory
- Natural language action processing
- Graceful error recovery and fallbacks

**Documentation** ✅
- Comprehensive README with quick-start guide
- CLAUDE.md — Developer reference for AI assistants
- AGENTS.md — LLM provider integration guide
- ROADMAP.md — Vision for v0.3+ features

### Verified Functionality
- ✅ 50-turn playtest with all game mechanics
- ✅ Three LLM providers working reliably
- ✅ PDF lore ingestion and knowledge graph queries
- ✅ Auto-save and recovery
- ✅ Configuration via env vars or interactive setup
- ✅ Runs on Ollama with Gemma 4 E2B/E4B models

## Roadmap

### v0.3 (Coming Q2 2026)
- Multi-character parties
- NPC relationship system and companion recruitment
- Quest chains and branching narratives
- **Text-to-speech narrator** (voice narration for immersion)
- World events and faction dynamics

### v0.4 (Coming Q3 2026)
- Multiplayer support
- Cloud save synchronization
- Community world sharing
- Persistent cross-session economies

### Future
- Native iOS app with SwiftUI (on-device Apple Intelligence inference)
- Web client
- Procedural dungeon generation
- Advanced spell and crafting systems

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

**v0.2.0 MVP Release — Ready for Game Night!**

Built with ❤️ for solo and group play. Designed to run on your hardware. Powered by LightRAG and lightweight LLMs.
