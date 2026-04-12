# CLAUDE.md — RAG-Quest v0.5.3 AI Developer Guide

This document provides AI assistants (Claude, GPT, etc.) with a comprehensive understanding of RAG-Quest v0.5.3 architecture, conventions, and development practices.

## Project Overview

**RAG-Quest** is an AI-powered D&D-style text RPG that uses LightRAG to eliminate hallucinations in narrative generation. Version 0.5.3 adds an interactive TUI tutorial, a downloadable user guide, and a 25-turn automated test suite, building on v0.5.2's polished UX.

**Core Design Philosophy**: LightRAG does the heavy lifting. The LLM narrator is intentionally kept small (Gemma 4 E2B/E4B, 2-4B parameters) because it doesn't memorize the world. Instead, LightRAG's dual-level retrieval (entity matching + vector similarity) injects precise knowledge per query. This architecture enables RAG-Quest to run on consumer hardware while producing narrative quality comparable to much larger models.

**Version**: v0.5.3 (Tutorial & User Guide)

**Status**: Production-ready. All core systems verified and working. Full backwards compatibility with legacy code.

**Key Achievement**: Interactive tutorial and comprehensive user guide make the game fully accessible to non-technical users.

## What's New in v0.5.3

### Interactive TUI Tutorial
- **9-Step Guided Walkthrough**: Accessible via `/tutorial` command in-game
- **Covers**: Exploration, NPCs, inventory, combat, commands, quests, saving, and pro tips
- **Beginner-Friendly**: No prior knowledge needed, clear explanations at each step

### Downloadable User Guide
- **Professional Word Document**: `docs/RAG-Quest_User_Guide.docx`
- **8 Chapters + Appendix**: Welcome, Getting Started, Setup, Character Creation, Gameplay, Commands, Advanced Features, Multiplayer & Troubleshooting
- **Non-Technical Audience**: Written for players with no command-line experience

### Quality Assurance
- **25-Turn Automated Test Suite**: `test_v053.py` with 100% pass rate
- **Tutorial System Tested**: All 9 steps validated
- **Full Regression Coverage**: All previous tests continue passing

## What's in v0.5.2

### UX Polish & Accessibility
- **Friendly Setup Wizard**: Automatically detects Ollama, guides through configuration
- **Command Shortcuts**: `/i`, `/s`, `/q`, `/p`, `/h` for rapid access
- **Smart Error Handling**: No tracebacks, every error is actionable and clear
- **Character Creation Confirmation**: Review before finalizing
- **Input Validation**: Helpful retry messages, not harsh rejections
- **Save Management**: Game recaps on load, metadata tracking

### Commands Added in v0.5.2
- `/new` — Start a new game without quitting
- Better unknown command feedback with suggestions
- `/config` for mid-game setting changes

### UX Features
- **Startup**: Ollama detection, ASCII welcome banner
- **Character Selection**: Race/class with stat bonuses shown, confirmation screen
- **Game Loop**: Clear status bar, subtle auto-save notifications
- **Error Recovery**: Smart classification (Ollama, timeout, API, file errors)
- **Terminal Compatibility**: Safe line widths (80-char), color contrast

## Technology Stack

- **Python 3.11+** — Core language
- **LightRAG** — Knowledge graph backend (the cornerstone)
- **httpx** — Async HTTP (used synchronously via ThreadPoolExecutor)
- **Rich** — Terminal UI and formatting
- **PyMuPDF** — PDF text extraction
- **pytest** — Testing framework

## Directory Structure

```
rag-quest/
├── rag_quest/                    # Main package
│   ├── __init__.py              # Version: 0.5.3
│   ├── __main__.py              # Entry point (python -m rag_quest)
│   ├── startup.py               # Welcome screen & Ollama detection
│   ├── config.py                # ConfigManager & setup wizard
│   ├── ui.py                    # Terminal UI, help, commands
│   ├── tutorial.py              # Interactive 9-step TUI tutorial
│   ├── llm/                     # LLM provider implementations
│   │   ├── __init__.py
│   │   ├── base.py              # BaseLLMProvider
│   │   ├── ollama_provider.py   # Local Ollama (recommended)
│   │   ├── openai_provider.py   # OpenAI integration
│   │   └── openrouter_provider.py # OpenRouter integration
│   ├── knowledge/               # LightRAG integration
│   │   ├── __init__.py
│   │   ├── world_rag.py         # WorldRAG wrapper
│   │   ├── chunking.py          # RAG profile configs
│   │   └── ingest.py            # PDF/txt/md ingestion
│   ├── engine/                  # Game logic & state
│   │   ├── __init__.py
│   │   ├── character.py         # Player character (6 attributes, classes, races)
│   │   ├── world.py             # World state
│   │   ├── inventory.py         # Item management
│   │   ├── quests.py            # Quest chains
│   │   ├── party.py             # Multi-character parties
│   │   ├── relationships.py     # NPC relationships & factions
│   │   ├── events.py            # Dynamic world events
│   │   ├── combat.py            # D&D combat with dice rolls
│   │   ├── encounters.py        # Enemy generation & loot
│   │   ├── narrator.py          # AI narrator & LLM integration
│   │   ├── tts.py               # Text-to-speech support
│   │   ├── game.py              # Main game loop & commands
│   │   ├── achievements.py      # 11 achievements
│   │   ├── dungeon.py           # Procedural dungeon generation
│   │   └── saves.py             # Save/load & serialization
│   ├── multiplayer/             # Local multiplayer
│   │   ├── __init__.py
│   │   ├── session.py           # MultiplayerSession
│   │   ├── trading.py           # Item trading between players
│   │   └── sync.py              # State synchronization
│   ├── worlds/                  # World sharing
│   │   ├── __init__.py
│   │   ├── exporter.py          # Export to .rqworld
│   │   ├── importer.py          # Import from .rqworld
│   │   └── templates.py         # Built-in templates
│   ├── prompts/                 # System prompts
│   │   ├── __init__.py
│   │   └── templates.py         # Prompt templates
│   └── saves/                   # Save slot storage
├── lore/                        # Example lore files
│   └── EXAMPLE_WORLD.md
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   ├── TEST_REPORT.md
│   └── RAG-Quest_User_Guide.docx  # Downloadable user guide
├── pyproject.toml               # Project config
├── README.md                    # User-facing docs
├── QUICKSTART.md                # Quick start guide
├── CONTRIBUTING.md              # Contribution guidelines
├── AGENTS.md                    # LLM provider guide
├── LICENSE                      # MIT License
└── CLAUDE.md                    # This file
```

## Core Classes & Patterns

### Startup & Welcome (startup.py)

**print_welcome_screen()** — Displays friendly ASCII art banner, version, and intro message.

**check_ollama_health()** — Detects if Ollama is running on localhost:11434.

**get_available_ollama_models()** — Lists available models in Ollama.

**print_ollama_setup_needed()** — Displays helpful setup instructions if Ollama isn't running.

### Configuration Management (config.py)

**ConfigManager** — Persistent configuration with fallback to environment variables.

```python
class ConfigManager:
    def get(self, key: str) -> Any:
        # e.g., "llm.provider", "rag.profile"
        return self._config[key]
    
    def set(self, key: str, value: Any) -> None:
        self._config[key] = value
        self._save()  # Immediately persist to file
```

**get_config()** — Returns singleton ConfigManager instance.

**setup_first_run()** — Interactive setup wizard with three start modes:
1. **Fresh Adventure** — Blank world, custom name
2. **Quick Start** — Choose from 4 templates
3. **Upload Lore** — Ingest custom files

Config location: `~/.config/rag-quest/config.json`

### Game State

**GameState** — Central state container:
```python
@dataclass
class GameState:
    character: Character
    world: World
    inventory: Inventory
    quest_log: QuestLog
    party: Party
    relationships: RelationshipManager
    conversation_history: list[dict]
    
    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> 'GameState': ...
```

All game objects are fully serializable. Saves are JSON at: `~/.local/share/rag-quest/saves/{world_name}.json`

### Character System

**Character** — Player character with:
- Attributes: name, race, class, level, HP, XP
- Six D&D attributes: STR, DEX, CON, INT, WIS, CHA
- Location, inventory references, status effects
- Methods: `take_damage()`, `heal()`, `level_up()`, `get_status()`

**Race & Class** — 5 races (Human, Elf, Dwarf, Orc, Halfling) and 5 classes (Fighter, Rogue, Mage, Cleric, Ranger) with stat bonuses.

### World System

**World** — World state container:
- name, setting, tone, time_of_day, weather
- visited_locations, npcs_met
- recent_events (last 5 for narrative context)
- Methods: `advance_time()`, `add_visited_location()`, `get_context()`

**Events** — Dynamic world events with consequences, recorded in RAG knowledge graph.

### Combat System

**CombatEncounter** — Handles D&D combat:
- Dice rolling (d4-d20, attack rolls vs AC)
- Initiative calculation
- Damage calculation with critical hits
- Turn-based combat flow

**Enemy** — NPC/monster with HP, attack, defense, loot drops.

**Encounter Generation** — Location-based enemy tables, difficulty scaling, loot tables.

### Quest System

**Quest** — Quest object with:
- title, description, objectives
- status (pending, active, completed)
- reward_xp, reward_items
- Methods: `check_objectives()`, `complete()`

**QuestLog** — Maintains active and completed quests, methods: `add_quest()`, `complete_quest()`, `get_active_quests()`

### NPC & Relationship System

**RelationshipManager** — Tracks NPC dispositions:
```python
def add_npc(self, name: str, role: str, disposition: float = 0.0):
    # disposition: -1.0 (enemy) to +1.0 (ally)
    pass

def change_disposition(self, npc_name: str, delta: float):
    # Modify trust level
    pass
```

**Faction System** — Faction reputation tracking with methods: `create_faction()`, `change_reputation()`, `get_reputation()`.

### Narrator (narrator.py)

**Narrator** — Lightweight AI narrator that:
1. Receives player action (natural language)
2. Queries RAG for relevant world context
3. Builds LLM prompt with game state + RAG context + conversation history
4. Calls LLM provider (synchronous)
5. Records event back to RAG
6. Returns narrative response

**Key Method**:
```python
def process_action(self, action: str, game_state: GameState) -> str:
    # Returns narrated response
    # (Currently doesn't update game state; see Known Issues)
```

### LLM Providers (llm/)

All providers inherit from **BaseLLMProvider**:

```python
class BaseLLMProvider(ABC):
    def complete(self,
                messages: list[dict],
                temperature: float = None,
                max_tokens: int = None,
                **kwargs) -> str:  # SYNCHRONOUS
        """Call LLM and return response."""
```

**Implementations**:
- **OllamaProvider** — Local inference via `http://localhost:11434/api/generate`
- **OpenAIProvider** — OpenAI API, models like gpt-4, gpt-3.5-turbo
- **OpenRouterProvider** — OpenRouter.ai, 100+ models

All now **synchronous** (were async before v0.5.0).

### Knowledge Layer (knowledge/)

**WorldRAG** — LightRAG wrapper:
```python
class WorldRAG:
    def initialize(self, world_name: str):  # Synchronous
        # Lazy initialization, creates or loads RAG index
    
    def ingest_text(self, text: str, source: str = "manual"):
        # Add knowledge to graph
    
    def ingest_file(self, path: str):
        # Handle .txt, .md, .pdf files
    
    def query_world(self, question: str, context: str = "") -> str:
        # Retrieve relevant knowledge
    
    def record_event(self, event: str):
        # Insert event with metadata
```

**RAG Profiles** — Configurable chunking and query strategies:
- **fast**: 4000-char chunks, vector-only search
- **balanced**: 2000-char chunks, entity-focused search (recommended)
- **deep**: 1000-char chunks, hybrid entity+relationship search

**Implementation Detail**: LightRAG is async internally. `WorldRAG` uses `ThreadPoolExecutor` to run async operations from synchronous code via `_run_async()` helper.

### Game Loop (game.py)

**run_game()** — Main game loop:
1. Print welcome banner
2. Load or create character/world
3. Initialize RAG knowledge graph
4. Game loop:
   - Print game state
   - Prompt player
   - Handle command (if `/...`)
   - Otherwise: narrator.process_action()
   - Update game state
   - Auto-save every N turns
   - Repeat

**Commands Implemented**:
- `/i`, `/inventory` — Show inventory
- `/s`, `/stats` — Show character stats
- `/q`, `/quests` — Show quests
- `/p`, `/party` — Show party
- `/rel`, `/relationships` — Show NPC relationships
- `/h`, `/help` — Show full help
- `/config` — Change settings
- `/new` — New game
- `/save` — Manual save
- `/exit` — Quit

**All commands have short aliases** for quick access.

### Achievements System (achievements.py)

**AchievementEngine** — Tracks 11 achievements:
1. Explorer — Visit 10 locations
2. Warrior — Win 5 combats
3. Diplomat — Increase NPC disposition by 50 points
4. Scholar — Complete 5 quests
5. Treasure Hunter — Find 10 items
6. Dragon Slayer — Defeat a boss
7. Indestructible — Reach level 5 without dying
8. Hoarder — Have 50 items
9. Wealthy — Collect 1000 gold
10. Legendary — Reach level 10
11. Well-Connected — Meet 10 NPCs

**Methods**:
```python
def check_achievements(self, player: Character, game_state: GameState):
    # Called each turn, checks for achievement triggers
    
def get_achievements(self) -> list[Achievement]:
    # Returns all achievements with progress
```

### Dungeon Generation (dungeon.py)

**DungeonGenerator** — Procedural dungeon creation:
```python
def generate_level(self, level: int) -> DungeonLevel:
    # 5-15 rooms per level
    # Room types: corridors, chambers, traps, treasure, boss
    # Returns DungeonLevel with ASCII map
```

### Multiplayer (multiplayer/)

**MultiplayerSession** — Hot-seat multiplayer:
- Shared world state
- Per-player character
- Turn management
- Item trading system
- Cooperative and PvP combat options

### World Sharing (worlds/)

**WorldExporter** — Package world as `.rqworld`:
- Exports RAG knowledge graph
- Includes metadata and configuration
- Compressed format for distribution

**WorldImporter** — Load `.rqworld` packages:
- Validation and integrity checking
- Prevents corrupted worlds
- Merges knowledge into existing world

## Important Implementation Details

### Synchronous Architecture

All I/O is now synchronous (v0.5.0+). No async/await in game loop:

```python
def process_action(action: str) -> str:
    context = world_rag.query_world(action)  # Synchronous
    response = llm_provider.complete(messages)  # Synchronous
    return response
```

**Note**: LightRAG is still async internally. `WorldRAG._run_async()` uses `ThreadPoolExecutor` to bridge.

### State Serialization

All game objects implement round-trip serialization:

```python
# Save
state_dict = game_state.to_dict()
json_str = json.dumps(state_dict)

# Load
game_state = GameState.from_dict(json.loads(json_str))
```

### Prompt Building

Prompts are composed at call-time, not templated:

```python
messages = [
    {'role': 'system', 'content': NARRATOR_SYSTEM + world_context},
    {'role': 'user', 'content': player_action},
]
response = llm_provider.complete(messages)
```

### Terminal Output

Always use Rich for formatting:

```python
from rich.console import Console
from rich.panel import Panel

console = Console()
console.print(Panel(text, title="Narrator", style="blue"))
```

**Color convention**:
- Green: Success, gains
- Red: Danger, loss
- Blue: Narrative
- Yellow: Warnings
- Magenta: System messages

## Error Handling Philosophy (v0.5.2)

**Zero tracebacks shown to users.** Every error path returns a friendly, actionable message.

Error categories with example messages:

**Ollama not running**:
```
It looks like Ollama isn't running. Please:
1. Download Ollama from https://ollama.ai
2. Open Ollama from your Applications folder
3. Try again!
```

**Model not found**:
```
Model gemma4:e4b not found. To download it, run:
ollama pull gemma4:e4b
```

**API key invalid**:
```
Your OpenAI API key doesn't look right. Check /config
or environment variable OPENAI_API_KEY.
```

**Timeout**:
```
The AI took too long to respond. This usually means:
- Your computer is slow (try 'fast' RAG profile)
- The model is large (try gemma4:e2b)
- The network is slow

You can change settings with: /config
```

**File not found**:
```
Lore file not found: /path/to/file
Make sure the file exists and try again.
```

## How to Run & Develop

### Initial Setup

```bash
git clone https://github.com/mattwag05/rag-quest.git
cd rag-quest
pip install -e ".[dev]"
```

### Running

```bash
# Interactive setup (first time)
python -m rag_quest

# With environment config (scripting)
export LLM_PROVIDER=ollama OLLAMA_MODEL=gemma4:e4b
python -m rag_quest

# With specific world/character
export WORLD_NAME="My World" CHARACTER_NAME="Hero"
python -m rag_quest
```

### Testing

```bash
# Run all tests
pytest -v

# Run specific test
pytest test_v051_core.py -v

# With coverage
pytest --cov=rag_quest --cov-report=html
```

### Development Workflow

```bash
# Format
black rag_quest/
isort rag_quest/

# Type check
mypy rag_quest/

# Check syntax
python -m py_compile rag_quest/**/*.py
```

## Known Issues & Limitations

### ✓ Fixed (v0.5.2)
- Inventory serialization — Fixed, all data preserved
- DifficultyLevel enum — Complete with all values
- Zero tracebacks — All error paths return friendly messages
- Command abbreviations — All implemented
- Character creation confirmation — All implemented

### Known Design Limitations

1. **Character Location Not Parsed** — Narrator doesn't extract location changes from responses. Would need regex patterns for "move to", "go to", etc.

2. **Inventory/Quest Integration Limited** — Items and quests exist but limited integration with narrator feedback. Narrator doesn't always parse item gains or quest completion.

3. **RAG Query Latency** — First query takes 30-60 seconds (LightRAG initialization). Typical query 1-3 seconds.

4. **PDF Ingestion Slow** — Large PDFs take minutes to ingest due to entity extraction. Recommend 5-10 page files for testing.

## File Locations

- **Config**: `~/.config/rag-quest/config.json`
- **Saves**: `~/.local/share/rag-quest/saves/`
- **RAG Data**: `~/.local/share/rag-quest/worlds/{world_name}/`
- **Lore**: `./lore/`

## Performance Characteristics

**Ollama Response Times** (M1 Mac):
- Gemma 4 E4B (GPU): 2-10 sec per response
- Gemma 4 E2B (CPU): 10-60 sec per response

**RAG Query Times**:
- First query: 30-60 sec (initialization)
- Typical query: 1-3 sec
- Large world: 3-5 sec

**Memory Usage**:
- Base game: <50 MB
- Per 100 conversation exchanges: ~100 KB
- RAG storage: 50-200 MB per world

## Contributing

1. Check beads: `bd list`
2. Claim work: `bd update <id> --claim`
3. Create branch
4. Make changes
5. Test: `pytest`
6. Format: `black`, `isort`, `mypy`
7. Commit: atomic messages
8. PR & review

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

## Resources

- **LightRAG**: https://github.com/hkuds/LightRAG
- **Ollama**: https://ollama.ai
- **Gemma**: https://blog.google/technology/developers/gemma-open-models/
- **Rich**: https://rich.readthedocs.io/
- **httpx**: https://www.python-httpx.org/

---

**Last Updated**: April 2026  
**For**: Claude and other AI assistants contributing to RAG-Quest

**Key Principle**: LightRAG does the heavy lifting. Keep the LLM lightweight and focused on narrative.
