# RAG-Quest

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Version 0.6.0](https://img.shields.io/badge/version-0.6.0-green.svg)](https://github.com/mattwag05/rag-quest/releases/tag/v0.6.0)
[![Status: Stable](https://img.shields.io/badge/status-stable-green.svg)](docs/TEST_REPORT.md)

> **An AI-powered D&D-style text RPG where a lightweight LLM narrator brings your world to life, powered by LightRAG's knowledge graph backbone.**

**Your dungeon master runs on your laptop. No hallucinations. No contradictions. Just rich, consistent storytelling powered by a small language model (2-4B parameters) and a persistent knowledge graph.**

## What Makes RAG-Quest Different

**LightRAG Does the Heavy Lifting**: Unlike traditional AI storytellers that hallucinate and forget plot points, RAG-Quest grounds every narrative decision in a persistent knowledge graph. Your world state is facts, not tokens. The LLM narrator is just the storyteller.

**Consumer Hardware Friendly**: Runs entirely on Ollama with Gemma 4 E2B (2B, CPU-friendly) or E4B (4B, GPU-optimized). No API calls needed unless you want them. No waiting for cloud services. Your game world stays private and local.

**Three LLM Providers Available**:
- **Ollama** (recommended) — free, fast, private, runs on your computer
- **OpenRouter** — 100+ cloud models, pay-per-use, runs anywhere
- **OpenAI** — GPT-4, GPT-3.5-turbo, highest quality

## Features

### Core Game Systems
- **D&D Combat** — Dice rolls (d4-d20), initiative, attack rolls vs AC, critical hits, damage calculation
- **Character Progression** — 6 attributes (STR/DEX/CON/INT/WIS/CHA), 5 races, 5 classes, XP, leveling to 10
- **Dynamic Encounters** — Location-based enemies, difficulty scaling, boss encounters, loot tables
- **Rich Inventory** — Weapons, armor, accessories with stat bonuses, weight management
- **Quest System** — NPC quest offers, branching objectives, completion tracking, experience rewards

### World & Story
- **NPC Relationships** — Track trust and disposition with NPCs, faction reputation
- **Dynamic Events** — World events with consequences, time advancement, location discovery
- **Procedural Dungeons** — Randomly generated dungeon levels, ASCII maps that reveal as you explore, scaling difficulty
- **Three Start Modes** — Fresh Adventure (blank world), Quick Start (4 templates), Upload Lore (bring your own)

### Multiplayer & Persistence
- **Multi-Slot Saves** — 5+ save slots with auto-save rotation and metadata tracking
- **World Sharing** — Export worlds as `.rqworld` packages, import community worlds
- **Local Multiplayer** — Hot-seat mode for turn-based gameplay on one machine
- **Achievement System** — 11 achievements tracking exploration, combat, diplomacy, and progression

### Campaign Memory (v0.6)
- **AI Notetaker** — Incremental session summarizer runs on every save. `/notes` shows the latest chronicle; `/notes refresh` forces an update. Stored as a local JSON sidecar — never touches world lore unless you approve it.
- **Canonize** — `/canonize` promotes player-approved notes into LightRAG with a `canonized` tag. Hard boundary between local notes and the canonical knowledge graph keeps AI hallucinations out of retrieval.
- **Lore Encyclopedia** — `/lore` browses NPCs, locations, factions, and items you've encountered. Drill down with `/lore <category> <name>` to run an on-demand RAG query for rich detail.
- **Timeline & Bookmarks** — `/timeline` shows a filtered chronological event log built from every turn's state changes. `/bookmark [note]` saves a highlight's full prose; `/bookmarks` lists them later.

### Accessibility & Polish
- **Interactive Tutorial** — `/tutorial` launches a 10-step guided TUI walkthrough for new players
- **Downloadable User Guide** — 8-chapter Word document covering all game systems
- **Friendly Setup Wizard** — Automatically detects Ollama, guides you through configuration
- **No Command-Line Experience Needed** — Welcoming interface, helpful prompts, no jargon
- **Command Shortcuts** — `/i` for inventory, `/s` for stats, `/q` for quests, `/p` for party, `/h` for help
- **Smart Error Handling** — Actionable error messages, zero tracebacks, graceful recovery
- **Text-to-Speech Narration** — Optional TTS with multiple voices (pyttsx3 offline, gTTS online)
- **RAG Profiles** — Choose speed vs quality (fast/balanced/deep) based on your hardware

## Quick Start (5 Minutes)

### 1. Install Ollama
Download from **https://ollama.ai** and install for your system (Mac/Linux/Windows).

### 2. Pull the Gemma 4 Model
```bash
ollama pull gemma4:e4b
```
(Takes 5-10 minutes; use `gemma4:e2b` for CPU-only systems)

### 3. Install RAG-Quest

**Homebrew (Mac):**
```bash
brew install mattwag05/tap/rag-quest
rag-quest
```

**pip (all platforms):**
```bash
pip install git+https://github.com/mattwag05/rag-quest.git
python -m rag_quest
```

### Web UI (v0.8, optional)

Prefer playing in a browser? Install the optional `[web]` extras and
launch the FastAPI server:

```bash
pip install 'rag-quest[web] @ git+https://github.com/mattwag05/rag-quest.git'
rag-quest serve --host 127.0.0.1 --port 8000
# → open http://127.0.0.1:8000/ in your browser
```

The web client is a single static page (no build step, no framework)
that streams narrator responses live via Server-Sent Events. World
events, achievement unlocks, and module gating all surface through the
same shared turn loop the CLI uses, so you don't lose any gameplay
features by playing in the browser.

### 4. Follow the Prompts
The setup wizard will:
- Detect Ollama automatically
- Ask if you want a fresh world or to pick a template
- Create your character (choose race, class, name)
- Start your adventure

**That's it!** You're playing.

## How to Play

Type what you want to do in plain English. The AI understands natural language:

```
You see a tavern ahead. What do you do?
> Go inside and order a drink

You walk into the dimly lit tavern. The smell of ale and roasted meat fills your nostrils...
```

### Commands

| Command | Shortcut | What it does |
|---------|----------|-------------|
| `/inventory` | `/i` | Check what you're carrying |
| `/stats` | `/s` | Show character attributes, level, HP |
| `/quests` | `/q` | View active quests and objectives |
| `/party` | `/p` | See your companions |
| `/relationships` | `/rel` | Check NPC trust and faction rep |
| `/timeline` | `/t` | Chronological event log (filter by type) |
| `/bookmark` | `/bm` | Save the current turn's prose as a highlight |
| `/notes` | `/n` | View or refresh AI campaign summary |
| `/canonize` | | Promote notes into permanent world lore |
| `/lore` | `/l` | Browse lore encyclopedia with RAG detail |
| `/achievements` | | View all achievements and progress |
| `/factions` | | See faction standings |
| `/dungeon` | | Generate and explore procedural dungeons |
| `/map` | | Show your world map |
| `/help` | `/h` | Full command reference |
| `/tutorial` | | Interactive 9-step guided tutorial |
| `/config` | | Change LLM provider or RAG profile |
| `/new` | | Start a new game |
| `/save` | | Manually save your progress |
| `/exit` | | Quit (with save option) |

### Game Features in Action

**Combat**: Encounter an enemy? Combat is automatic with dice rolls, initiative, and damage. You don't need to manage the math.

**Quests**: NPCs offer quests with branching objectives. Complete them for XP and loot.

**Exploration**: Discover locations, meet NPCs, uncover secrets. Your world grows as you explore.

**Character Growth**: Gain XP, level up, unlock new abilities, improve attributes.

**Multiplayer**: In hot-seat mode, pass the controller between players. Same world, different characters.

## Configuration

### LLM Provider Setup

On first run, the setup wizard guides you. To reconfigure later:

```bash
python -m rag_quest --config
# or in-game: /config
```

**Environment variables** (for scripting):
```bash
export LLM_PROVIDER=ollama              # or: openai, openrouter
export OLLAMA_MODEL=gemma4:e4b         # ignored if provider != ollama
export OLLAMA_BASE_URL=http://localhost:11434
export OPENAI_API_KEY=sk-...           # if using OpenAI
export OPENROUTER_API_KEY=sk-or-...    # if using OpenRouter
export RAG_PROFILE=balanced             # or: fast, deep
export WORLD_NAME="My World"
python -m rag_quest
```

### RAG Profiles

Choose the right profile for your hardware:

- **fast** — Speed optimized (weak hardware, quick testing). Larger chunks, vector-only search.
- **balanced** — Default (consumer hardware). Moderate chunks, entity-focused search. Recommended.
- **deep** — Quality optimized (high-end systems). Smaller chunks, hybrid entity+relationship search.

### Configuration File

Settings are saved to `~/.config/rag-quest/config.json`:

```json
{
  "llm": {
    "provider": "ollama",
    "model": "gemma4:e4b",
    "api_key": null,
    "base_url": "http://localhost:11434"
  },
  "rag": {
    "profile": "balanced"
  },
  "game": {
    "auto_save_interval": 5
  }
}
```

## Architecture

RAG-Quest uses a novel architecture: **LightRAG does the heavy lifting, the LLM is just the narrator**.

- **LightRAG Knowledge Graph**: Stores all world facts, entities, relationships, and events. Dual-level retrieval (entity matching + vector similarity) ensures the narrator has precise context.
- **Lightweight LLM Narrator**: A small model (Gemma 4 E2B/E4B, 2-4B parameters) that reads the knowledge graph and crafts the narrative response. No memorization needed.
- **Synchronous Game Loop**: Turn-based gameplay with no async complexity. Clean, simple, responsive.

**Why it works**: The knowledge graph is the "long-term memory." The LLM is the "storyteller." Separation of concerns = zero hallucinations.

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed technical documentation.

## Developers

### Setup

```bash
git clone https://github.com/mattwag05/rag-quest.git
cd rag-quest
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest -v
# or specific test file
pytest test_v051_core.py -v
```

### Format & Check

```bash
black rag_quest/
isort rag_quest/
mypy rag_quest/
```

### Development Workflow

1. Check beads: `bd list`
2. Start work: `bd update <id> --claim`
3. Create feature branch
4. Write code and tests
5. Format: `black`, `isort`, `mypy`
6. Commit with atomic, clear messages
7. Create PR

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

## Troubleshooting

### "Ollama isn't running"
Make sure Ollama is installed and launched from Applications. It runs quietly in the background.

### "Model not found"
Run `ollama pull gemma4:e4b` to download the model.

### "API key error"
Check that your API key is correct in `/config` or environment variables.

### "Slow responses"
RAG-Quest is CPU/GPU bound. Large models and weak hardware = slow. Try `gemma4:e2b` or the `fast` RAG profile.

### "Narrative quality is poor"
Make sure you've ingested lore (upload during setup). RAG needs knowledge to work with. Also check the RAG profile matches your hardware.

## Roadmap

- **v0.5.3** ✓ Complete — Interactive TUI tutorial, downloadable user guide, 25-turn automated test suite
- **v0.5.2** ✓ Complete — Polished UX for non-developers, zero tracebacks, command shortcuts, friendly setup
- **v0.6** — Web UI, cloud deployment, streaming responses
- **v0.7** — iOS/SwiftUI app, offline package distribution
- **v0.8** — Apple Intelligence integration, voice I/O
- **v1.0** — Stable API, community mod support, advanced RAG features

## License

MIT License. See [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Resources

- **GitHub**: https://github.com/mattwag05/rag-quest
- **LightRAG**: https://github.com/hkuds/LightRAG
- **Ollama**: https://ollama.ai
- **Gemma**: https://blog.google/technology/developers/gemma-open-models/

---

**Made with knowledge graphs and storytelling by RAG-Quest contributors.**
