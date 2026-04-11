# RAG-Quest

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

An AI-powered D&D-style text RPG that uses LightRAG knowledge graph backend to eliminate hallucinations. Play in immersive fantasy worlds crafted by AI, where consistency and lore accuracy are guaranteed.

## Overview

RAG-Quest combines the power of knowledge graph retrieval with language models to create engaging, coherent text-based RPG experiences. Unlike traditional AI storytellers that struggle with consistency, RAG-Quest grounds its narrative in a persistent knowledge graph, ensuring your world remains consistent throughout your adventure.

**Key Design Philosophy**: LightRAG does the heavy lifting. The AI dungeon master (LLM) is kept lightweight (~3B parameters, ≤8K context window) because it doesn't need to memorize the world. Instead, LightRAG's dual-level retrieval system (knowledge graph + vector embedding matching) injects precisely the relevant context for each narrative decision. This means RAG-Quest can run entirely on consumer hardware with local models via Ollama.

**Key Innovation**: Every game state change and narrative detail is recorded in LightRAG's knowledge graph. When the player acts, LightRAG returns the exact facts the narrator needs—no hallucinations, no contradictions, no redundant world state in the LLM's context window.

## Features

- **LightRAG-Powered World Context**: Dual-level knowledge graph retrieval (entity + theme matching) delivers only the relevant facts per query—enables tiny LLM models to narrate coherently
- **Lightweight LLM Design**: Run with ~3B parameter models (Ollama locally, or OpenRouter's Llama/Mistral) thanks to RAG context injection; no need for GPT-4 or Claude
- **Multiple LLM Providers**: Works with OpenAI, OpenRouter, or local Ollama models as first-class citizens
- **Dynamic Narration**: Every action generates vivid, contextual responses from an AI Dungeon Master powered by relevant retrieved knowledge
- **World Persistence**: Your game saves include the full knowledge graph, ensuring consistency when you pick up where you left off
- **Lore Ingestion**: Load your own lore documents (txt, md, pdf) into the knowledge graph to build custom worlds with guaranteed lore adherence
- **Rich Terminal UI**: Beautiful colored text, formatted panels, and intuitive commands
- **Natural Language Actions**: Type what you want to do; the AI understands context and intent
- **Consumer-Hardware Friendly**: The architecture favors local inference; even modest machines can run engaging narratives

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/rag-quest.git
cd rag-quest

# Install with pip
pip install -e .

# Or install dependencies directly
pip install lightrag-hku httpx rich pymupdf
```

### Configuration

Run the game once to start the interactive setup:

```bash
python -m rag_quest
```

This will prompt you to:
1. **Choose an LLM provider**:
   - OpenAI (GPT-4, GPT-3.5-turbo) - Best quality, cloud-hosted
   - OpenRouter (100+ models) - Best flexibility, cloud-hosted
   - Ollama (local, free) - Best for consumer hardware, local inference
2. **Configure the world**: Name, setting, tone
3. **Create your character**: Name, race, class

Configuration is saved to `~/.config/rag-quest/config.json`.

### First Game

```bash
python -m rag_quest
```

Then simply type actions in natural language:

```
> I carefully approach the tavern and push open the wooden door
> I sit at the bar and order a drink
> I ask the bartender about the rumors of a dragon
> /inventory
> /quests
> /map
> /help
```

## Game Guide

### Commands

| Command | Purpose |
|---------|---------|
| `/inventory` | View your items and equipment |
| `/quests` | Check active quests and objectives |
| `/look` | Examine current location in detail |
| `/map` | See visited locations |
| `/status` | Check character HP and stats |
| `/save` | Manually save game |
| `/help` | Show command help |
| `/quit` | Exit game (prompts to save) |

### Gameplay Tips

- **Use natural language**: The AI understands context and nuance - be descriptive
- **Be creative**: The world responds to unexpected actions and creative solutions
- **Explore thoroughly**: Find hidden details with `/look` and by asking about things
- **Track quests**: Check `/quests` to see active objectives and rewards
- **Manage inventory**: Items have weight limits; drop what you don't need
- **Learn world knowledge**: The more you explore, the better RAG context becomes

### Creating Custom Worlds

To create a world with custom lore:

1. Write or gather lore documents (txt, md, or pdf)
2. During setup, choose "Upload lore" and point to the directory
3. RAG will ingest all files and make the lore queryable
4. The narrator will consistently reference your world

**Example lore format**:

```markdown
# The Kingdom of Aethoria

## Geography
- Aethoria is a crescent-shaped kingdom nestled between mountains and sea
- The capital, Silvermere, lies on the coast
- Three main regions: The Highlands, The Forest of Whispers, The Dead Marshes

## History
- Founded 500 years ago by the First King
- Recently invaded by the Shadow Court
- The old magic still lingers in forgotten places

## NPCs
- Queen Lydia: Wise ruler, skilled diplomat
- The Raven: Mysterious spymaster with unknown loyalties
- Brother Aldric: Monks' leader, keeper of ancient knowledge

## Factions
- The Royal Guard: Crown loyalists
- The Shadow Court: Invaders from beyond
- The Grey Circle: Neutral mages

## Locations
- The Tavern at World's End: Neutral ground
- Silvermere Palace: Seat of power
- The Sunken Temple: Ancient ruin
```

## Architecture

### High-Level Overview

```
┌─────────────────────────────────────────┐
│      Terminal UI (Rich Library)         │
│   - Game loop & input handling          │
│   - Response display & formatting       │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│    Game Engine (rag_quest/engine/)      │
│  - Character, World, Inventory, Quests  │
│  - Lightweight Narrator (LLM agent)     │
│  - State management & serialization     │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
┌───────▼─────────┐  ┌─────▼────────────────┐
│  LLM Providers  │  │  LightRAG (Heavy     │
│  (rag_quest/    │  │   Lifting)           │
│   llm/)         │  │  (rag_quest/         │
│                 │  │   knowledge/)        │
│  - OpenAI       │  │                      │
│  - OpenRouter   │  │  - Dual-level query  │
│  - Ollama       │  │  - Lore ingestion    │
│    (~3B models) │  │  - Knowledge graph   │
└─────────────────┘  └──────────────────────┘
```

**The Design Principle**: LightRAG's knowledge graph stores all world facts. The Narrator LLM retrieves only what's needed per query—no bloated context window, no hallucinations. A ~3B parameter model (or even smaller) paired with strong RAG performs as well as massive models running blind.

### Core Components

#### LLM Providers (`rag_quest/llm/`)
- **BaseLLMProvider**: Abstract interface for all providers
- **OpenAIProvider**: Direct OpenAI API integration
- **OpenRouterProvider**: OpenRouter.ai multi-model support (recommended for testing with lighter models)
- **OllamaProvider**: Local Ollama support (recommended for consumer hardware)

See [AGENTS.md](AGENTS.md) for detailed provider documentation and model recommendations.

#### Knowledge Management (`rag_quest/knowledge/`)
- **WorldRAG**: Wraps LightRAG for game-specific queries and updates
- **Ingest**: File handling for lore documents (txt, md, pdf)

The RAG system is the "brain" of the world. Narrator queries it before every response.

#### Game Engine (`rag_quest/engine/`)
- **Character**: Player character with stats, inventory, location
- **World**: World state (time, weather, visited locations, NPCs met)
- **Inventory**: Item management with weight and rarity
- **QuestLog**: Quest tracking and objectives
- **Narrator**: Lightweight AI narrator that queries RAG and generates responses based on injected context
- **GameState**: Complete serializable game state
- **Game**: Main game loop

#### Configuration
- **config.py**: Interactive setup wizard and configuration management

### Data Flow Example

```
Player Input: "I search the desk for clues"
        ↓
Narrator queries RAG:
"What relevant facts about desks, searching, clues exist in this location?"
        ↓
RAG returns context (entity + theme matching):
"Desk in study contains: old books, jewels, secret compartment..."
        ↓
Narrator builds message:
[system prompt] + [RAG context] + [character status] + [recent history] + [action]
        ↓
LLM (small model, ~3B params) generates response based on injected context
        ↓
Response: "You find an old key and a mysterious letter..."
        ↓
Narrator parses for state changes:
- New items? Add to inventory
- Location changes? Update character position
- NPCs met? Add to world state
        ↓
Record event to RAG knowledge graph for future queries
        ↓
Save game state & auto-save
        ↓
Display response to player
```

**Why this matters**: The LLM never sees the full world. It gets exactly what it needs. This is why a lightweight model works—RAG does the world knowledge retrieval, the LLM does narrative synthesis.

## Configuration

### Config File Location

`~/.config/rag-quest/config.json`

### Config Structure

```json
{
  "llm": {
    "provider": "openrouter|openai|ollama",
    "model": "meta-llama/llama-2-7b|anthropic/claude-sonnet-4",
    "api_key": "sk-or-...",
    "temperature": 0.85,
    "max_tokens": 1024
  },
  "world": {
    "name": "Aethoria",
    "setting": "Medieval Fantasy",
    "tone": "Dark",
    "starting_location": "The Tavern"
  },
  "character": {
    "name": "Aragorn",
    "race": "Human",
    "class": "Ranger",
    "background": "Raised by wolves"
  }
}
```

**Model Selection Tips**:
- For local play: Use Ollama with 7B-13B models (neural-chat, mistral, llama2)
- For testing: Use OpenRouter with Llama-2-70b or Mistral
- For best quality: Use OpenAI GPT-4 or OpenRouter Claude Sonnet
- **Key insight**: A 7B local model with good RAG context beats a 70B model without RAG

### Changing Providers Mid-Game

You can switch LLM providers without losing your game save:

1. Edit `~/.config/rag-quest/config.json`
2. Change the `llm.provider` and `llm.model` values
3. Start the game and continue playing
4. The RAG database stays the same; only the narrator provider changes

## Game State & Saves

- **Game saves**: `~/.local/share/rag-quest/saves/{world_name}.json`
- **RAG database**: `~/.local/share/rag-quest/worlds/{world_name}/`
- **Config**: `~/.config/rag-quest/config.json`

Both game state and RAG database are preserved when you load a save, ensuring world consistency.

## Troubleshooting

### "Connection refused" errors
- **For OpenAI**: Check your API key in `~/.config/rag-quest/config.json`
- **For OpenRouter**: Verify API key and internet connection
- **For Ollama**: Make sure Ollama is running (`ollama serve` in another terminal)

### RAG queries returning irrelevant results
- The hybrid mode balances entity and theme matching
- More detailed lore ingestion helps significantly
- Try restarting the game to reset RAG context
- Consider adding more specific details to your lore

### Game not responding / hanging
- Check your LLM provider's API status
- For Ollama, ensure it's not overloaded (try a smaller model)
- Try a simpler action to test (e.g., `/status`)

### Memory or performance issues
- Check available disk space for RAG storage
- Consider archiving old save games
- For Ollama, larger models need more VRAM
- Remember: RAG does the heavy lifting, so the LLM can be smaller

## Development

### Project Structure

```
rag-quest/
├── rag_quest/
│   ├── __init__.py
│   ├── __main__.py              # Entry point
│   ├── config.py                # Configuration
│   ├── llm/                     # LLM providers
│   │   ├── base.py
│   │   ├── openai_provider.py
│   │   ├── openrouter_provider.py
│   │   └── ollama_provider.py
│   ├── knowledge/               # RAG integration
│   │   ├── world_rag.py
│   │   └── ingest.py
│   ├── engine/                  # Game logic
│   │   ├── character.py
│   │   ├── world.py
│   │   ├── inventory.py
│   │   ├── quests.py
│   │   ├── narrator.py
│   │   └── game.py
│   └── prompts/                 # System prompts
│       └── templates.py
├── lore/                        # Example lore
├── saves/                       # Game saves
├── tests/                       # Test suite
├── pyproject.toml               # Project config
├── README.md                    # This file
├── ARCHITECTURE.md              # Architecture details
├── AGENTS.md                    # LLM provider guide
├── CLAUDE.md                    # AI assistant guide
├── CONTRIBUTING.md              # Contribution guidelines
├── ROADMAP.md                   # Development roadmap
└── LICENSE                      # MIT License
```

### Running in Development Mode

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run with debug output
python -m rag_quest --debug

# Run tests
pytest -v

# Run with coverage
pytest --cov=rag_quest
```

### Code Quality

```bash
# Format code
black rag_quest/

# Sort imports
isort rag_quest/

# Type checking
mypy rag_quest/

# All checks
black rag_quest/ && isort rag_quest/ && mypy rag_quest/ && pytest
```

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture and design patterns
- **[AGENTS.md](AGENTS.md)** - LLM provider integration and narrator agent details
- **[CLAUDE.md](CLAUDE.md)** - Guide for AI assistants contributing to the project
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines
- **[ROADMAP.md](ROADMAP.md)** - Development roadmap and planned features

## Performance Notes

### RAG Performance
- **First startup**: 30-60 seconds (LightRAG initialization)
- **Typical query**: 1-3 seconds (cached)
- **Larger lore files**: Slower initialization
- **RAG storage**: 50-200 MB per world (grows with lore)

### LLM Response Times
- **OpenAI GPT-4**: 3-10 seconds
- **OpenRouter Claude**: 2-5 seconds
- **OpenRouter Llama**: 1-3 seconds
- **Ollama with GPU**: 2-10 seconds
- **Ollama with CPU**: 10-60 seconds

### Memory Usage
- **Character & world state**: <1 MB
- **Conversation history**: ~100 KB per 100 exchanges
- **RAG database**: 50-200 MB per world

### Optimization Tips
1. Break large lore files into smaller pieces
2. Use smaller LLM models (7B is often sufficient with RAG)
3. For local Ollama, use GPU and smaller models (7B)
4. Limit conversation history to last 6 messages
5. The bottleneck is usually RAG initialization, not the LLM

## Future Roadmap

### v0.2 (Combat & Character Depth)
- Combat system with dice rolls
- Character progression and leveling
- Dynamic encounter generation

### v0.3 (Social & Narrative)
- Multi-character parties
- NPC relationship system
- Quest chains with branching narratives
- **AI dungeon master text-to-speech narration**

### v0.4 (Multiplayer & Persistence)
- Shared multiplayer worlds
- Cloud save synchronization
- World export/import for community sharing

### Long-Term Vision
- Voice input/output
- AI-generated scene images
- Web UI and mobile client
- Crafting, spell research, and deep magic systems

See [ROADMAP.md](ROADMAP.md) for the full development roadmap.

## License

MIT License - See [LICENSE](LICENSE) file for details

## Credits

- **LightRAG**: HKU's knowledge graph system for contextual retrieval—the architectural cornerstone of RAG-Quest
- **Rich**: Gorgeous terminal UI library
- **httpx**: Modern, async-first HTTP client
- **PyMuPDF**: PDF text extraction
- **OpenAI, OpenRouter, Ollama**: LLM providers

## Support & Community

- **Issues**: Use GitHub Issues for bugs and feature requests
- **Discussions**: Share ideas and get help in Discussions
- **Documentation**: Check [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md), and [AGENTS.md](AGENTS.md)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)

## Getting Started

Ready to adventure?

```bash
python -m rag_quest
```

Then type your first action and watch the AI weave your story—powered by a knowledge graph that never forgets!

---

**May your tales be legendary and your worlds eternally consistent.**

