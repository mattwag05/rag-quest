# CLAUDE.md - AI Assistant Developer Guide

This document provides AI assistants (Claude, GPT, etc.) with a comprehensive understanding of RAG-Quest architecture, conventions, and development practices. Use this as your primary reference when contributing to the codebase.

## Project Overview

**RAG-Quest** is an AI-powered D&D-style text RPG that uses LightRAG (a knowledge graph system) to eliminate hallucinations in narrative generation. The game maintains consistency through a RAG backend that stores and retrieves world knowledge, allowing a lightweight AI narrator to generate coherent, context-aware storytelling.

**Core Design Philosophy**: LightRAG does the heavy lifting. The LLM acting as dungeon master is intentionally kept small—Gemma 4 E2B (2B) or E4B (4B) parameters, ≤8K token context—because it doesn't memorize the world. Instead, LightRAG's dual-level retrieval (entity matching + vector similarity) injects precisely the relevant knowledge per query. This architecture enables RAG-Quest to run entirely on consumer hardware with local models via Ollama, while producing narrative quality comparable to much larger models running blind.

**Why this matters**: A Gemma 4 model with excellent RAG context beats much larger models without RAG. The knowledge graph is the "long-term memory"; the LLM is just the "narrator."

**Current Version**: v0.3.0 (Combat, progression, encounters, TTS narration)

**Status**: v0.3 complete. Game loop fully functional with D&D combat system, character progression with leveling, dynamic encounter generation, text-to-speech narration, and real LLM narrator. All core gameplay mechanics verified and production-ready.

**Technology Stack**:
- **Python 3.11+** - Core language
- **LightRAG** - Knowledge graph backend (the architectural cornerstone)
- **httpx** - Async HTTP for LLM APIs (synchronous wrapper for turn-based game)
- **Rich** - Terminal UI and formatting
- **PyMuPDF** - PDF text extraction
- **pytest** - Testing framework

## v0.3.0 Release Summary (2026-04-11)

RAG-Quest v0.3.0 adds D&D combat mechanics, character progression, and immersive TTS narration:

### Combat & Progression
- **Combat System**: Dice rolling (d4-d20), initiative, attack rolls vs AC, damage calculation, critical hits
- **Character Progression**: Six attributes (STR/DEX/CON/INT/WIS/CHA), XP, leveling to 10, class abilities
- **Encounters**: Location-based enemy tables, difficulty scaling, boss encounters with 5x XP, loot tables
- **Equipment**: Weapon, armor, and accessory slots with stat bonuses

### Narration & Audio
- **Real LLM Narrator**: Actual LLM calls for dynamic narration, no hardcoded responses
- **Context Injection**: Game state, RAG knowledge, and conversation history in every prompt
- **TTS Narration**: pyttsx3 (offline) and gTTS (online) support with voice selection
- **Voice Commands**: /abilities, /equipment, /voice for game mechanics

### Verification
- All combat mechanics tested and working
- Character progression with leveling system verified
- Encounter generation with scaling and loot working
- TTS narration functional with multiple voices
- Real LLM narrator with context injection verified
- All LLM providers compatible (Ollama, OpenRouter, OpenAI)

## RAG Profiles & Speed vs Fidelity Configuration

RAG-Quest now supports user-configurable speed vs fidelity tradeoffs via **RAG Profiles**. This allows the system to adapt to different hardware capabilities and use cases.

### Available Profiles

**fast** - Speed optimized (weak hardware, quick testing)
- Larger text chunks (4000 chars with 200 overlap)
- Naive query mode (pure vector search, fastest)
- Lower token limits (top_k: 15, chunk_top_k: 10)
- Best for: CPU-only systems, fast iteration during development

**balanced** - Default (recommended for most users)
- Moderate chunks (2000 chars with 300 overlap)
- Local query mode (entity-focused, good quality)
- Standard token limits (top_k: 30, chunk_top_k: 15)
- Best for: Consumer hardware with moderate GPU, typical gameplay

**deep** - Quality optimized (capable hardware, immersive experience)
- Smaller chunks (1000 chars with 400 overlap)
- Hybrid query mode (entity + relationship graph, best quality)
- Higher token limits (top_k: 50, chunk_top_k: 25)
- Best for: High-end systems, maximum narrative immersion

### Configuration

Set via environment variable:
```bash
export RAG_PROFILE=balanced  # or: fast, deep
python -m rag_quest
```

Or during interactive setup:
```
RAG Profile (speed vs fidelity): [fast/balanced/deep] ?
```

Or in config file (`~/.config/rag-quest/config.json`):
```json
{
  "rag": {
    "profile": "balanced"
  }
}
```

### Implementation Details

**New Files**:
- `rag_quest/knowledge/chunking.py` - RAGProfileConfig, TextChunker, intelligent chunking strategies

**Modified Files**:
- `config.py` - Added RAG profile setup in first-run wizard
- `world_rag.py` - Profile-aware QueryParam configuration, smart chunking on ingest
- `ingest.py` - PDF progress reporting, file hash caching for change detection
- `narrator.py` - Improved context injection, error recovery, retry logic
- `game.py` - Enhanced error handling, graceful fallbacks, frequent auto-save
- `__main__.py` - Pass profile to WorldRAG initialization

**Key Features**:
- Intelligent PDF chunking that respects section boundaries
- File hash caching to skip re-ingestion of unchanged files
- Profile-optimized QueryParam settings for LightRAG
- Better error recovery with retry logic and fallback responses
- More comprehensive context injection from multiple RAG queries

## Critical Fixes Applied (2026-04-11)

The following 6 critical bugs were fixed to make the game functional:

1. **Package Installation (setuptools error)** - Fixed by adding explicit package configuration to `pyproject.toml`
2. **Interactive Config Blocks Non-Interactive Environments** - Added environment variable support and TTY detection in `config.py`
3. **Async/Await Mismatch** - Converted entire codebase from async to synchronous (cleaner for turn-based game)
4. **PDF Ingestion Function Signature** - Fixed `ingest_file()` to use LightRAG's async insertion API
5. **Narrator Constructor Mismatch** - Fixed undefined variable `character_class` to use `character.character_class.value`
6. **Missing World Description** - Not actually needed in current implementation

Additionally:
- Created synchronous wrapper for LightRAG async operations using ThreadPoolExecutor
- Fixed Ollama API response format parsing
- Fixed LLM provider parameter handling with `**kwargs`
- Implemented proper embedding function setup with Ollama nomic-embed-text model

**Result**: Game loop is now functional. 35-turn playthrough completed successfully with 100% success rate.

## Directory Structure

```
rag-quest/
├── rag_quest/                    # Main package
│   ├── __init__.py              # Package initialization
│   ├── __main__.py              # Entry point (python -m rag_quest)
│   ├── config.py                # Configuration & setup wizard
│   ├── llm/                     # LLM provider implementations
│   │   ├── __init__.py
│   │   ├── base.py              # BaseLLMProvider abstract class
│   │   ├── openai_provider.py   # OpenAI implementation
│   │   ├── openrouter_provider.py
│   │   └── ollama_provider.py   # Local Ollama support
│   ├── knowledge/               # LightRAG integration (the heavy lifter)
│   │   ├── __init__.py
│   │   ├── world_rag.py         # WorldRAG wrapper class
│   │   └── ingest.py            # Lore ingestion (txt/md/pdf)
│   ├── engine/                  # Game logic & state
│   │   ├── __init__.py
│   │   ├── character.py         # Player character with attributes & progression
│   │   ├── world.py             # World state
│   │   ├── inventory.py         # Item management
│   │   ├── quests.py            # Quest tracking
│   │   ├── combat.py            # D&D combat system with dice rolls & mechanics
│   │   ├── encounters.py        # Encounter generation & loot tables
│   │   ├── narrator.py          # Lightweight AI narrator & response generation
│   │   ├── tts.py               # Text-to-speech narration (pyttsx3, gTTS)
│   │   └── game.py              # Main game loop
│   └── prompts/                 # System prompts
│       ├── __init__.py
│       └── templates.py         # Prompt templates for narrator
├── lore/                        # Example/default lore
│   ├── .gitkeep
│   └── EXAMPLE_WORLD.md         # Example world definition
├── saves/                       # Player save games (git-ignored)
│   └── .gitkeep
├── tests/                       # Unit & integration tests (to be added)
├── pyproject.toml               # Project metadata & dependencies
├── README.md                    # User-facing documentation
├── ARCHITECTURE.md              # Technical architecture
├── AGENTS.md                    # LLM provider guide
├── CONTRIBUTING.md              # Contribution guidelines
├── ROADMAP.md                   # Development roadmap
├── CLAUDE.md                    # This file
├── LICENSE                      # MIT License
└── .gitignore
```

## Key Classes & Patterns

### LLM Provider Architecture (llm/)

**Base Class**: `BaseLLMProvider` (llm/base.py)

All providers inherit from this abstract class:

```python
class BaseLLMProvider(ABC):
    def __init__(self, config: dict)
    def complete(self, messages: list[dict], 
                 temperature: float = None,
                 max_tokens: int = None,
                 **kwargs) -> str  # Note: synchronous (was async before fix)
    def lightrag_complete_func(self) -> callable
```

**Key Implementations**:
- `OpenAIProvider` - Direct OpenAI API calls (sync)
- `OpenRouterProvider` - OpenRouter.ai (sync)
- `OllamaProvider` - Local Ollama inference (sync)

**Design Patterns**:
- All providers are now **synchronous** (converted from async in fix #3)
- Uses `httpx.Client` for HTTP (was AsyncClient)
- `lightrag_complete_func()` returns a function for LightRAG compatibility
- Temperature and max_tokens are call-time configurable
- Accept `**kwargs` from LightRAG without error
- **Narrator uses lightweight providers**: Ollama Gemma 4 E2B/E4B deliver excellent results on consumer hardware

**Adding a New Provider**:
1. Create `rag_quest/llm/my_provider.py`
2. Inherit from `BaseLLMProvider`
3. Implement `def complete()` method (synchronous)
4. Add to `config.py` setup wizard
5. Document in README.md

### Game Engine (engine/)

**GameState** - Central state container
- Bundles: `Character`, `World`, `Inventory`, `QuestLog`, conversation history
- Fully serializable via `to_dict()/from_dict()` for save/load

**Character** - Player character
- Attributes: name, race, class, HP, location, level
- Methods: `take_damage()`, `heal()`, `get_status()`
- Immutable fields on creation (name, race, class)

**World** - World state container
- Attributes: name, setting, tone, time_of_day, weather, visited_locations, npcs_met, recent_events
- Methods: `advance_time()`, `add_visited_location()`, `get_context()`
- Recent events (last 5) kept for narrative context

**Inventory** - Item management
- Items have: name, description, weight, quantity, rarity
- Max weight capacity (configurable)
- Methods: `add_item()`, `remove_item()`, `get_total_weight()`

**QuestLog** - Quest tracking
- Quests have objectives and status
- Methods: `add_quest()`, `get_active_quests()`, `complete_quest()`

**Narrator** - Lightweight AI narrator
- Core method: `process_action(player_input: str) -> tuple[str, GameState]` (synchronous)
- Orchestrates: RAG query → message building → LLM call → state parsing
- Maintains conversation history (last 6 messages)
- Returns: (response text, updated game state)
- **Known Issue**: Currently doesn't update character location or apply game state changes from narration

### Knowledge Layer (knowledge/)

**WorldRAG** - LightRAG wrapper (the heavyweight)
```python
class WorldRAG:
    def initialize()  # Synchronous
    def ingest_text(text: str, source: str)
    def ingest_file(path: str)
    def query_world(question: str, context: str) -> str
    def record_event(event: str)
```

**Design Decisions**:
- Lazy initialization (RAG starts on first query)
- Storage: `~/.local/share/rag-quest/worlds/{world_name}/`
- Uses "hybrid" mode for queries (entity + theme matching)
- Events recorded with metadata for tracking
- **Uses ThreadPoolExecutor to run async LightRAG operations from sync code**
- **RAG is the "long-term memory"**: all world facts live here, not in the LLM context

**Ingest Module** (ingest.py):
- Handles: .txt, .md, .pdf files
- Chunks large files automatically
- Integrates with `WorldRAG.ingest_text()`

## Key Patterns & Conventions

### Synchronous Architecture

After fix #3, all I/O operations are now **synchronous**:

```python
def process_action(action: str) -> str:
    context = world_rag.query_world(action)  # Synchronous
    response = llm_provider.complete(messages)  # Synchronous
    return response
```

**Why**: Turn-based text RPG doesn't need async. Synchronous is cleaner, simpler, and avoids callback hell.

**Important**: LightRAG still requires async internally. `WorldRAG` uses a ThreadPoolExecutor to run LightRAG's async operations from synchronous code via `_run_async()` helper.

### State Serialization

All game objects implement `to_dict()` and `from_dict()`:

```python
class MyGameObject:
    def to_dict(self) -> dict:
        return {
            'field1': self.field1,
            'field2': self.field2,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MyGameObject':
        return cls(
            field1=data['field1'],
            field2=data['field2'],
        )
```

Save files are JSON at: `~/.local/share/rag-quest/saves/{world_name}.json`

### Prompt Building

Prompts are composable strings. Avoid f-strings in templates; instead, compose at call-time:

```python
# Good
messages = [
    {'role': 'system', 'content': templates.NARRATOR_SYSTEM + f"\nWorld: {world_name}"},
    {'role': 'user', 'content': rag_context},
    {'role': 'user', 'content': player_action},
]

# Avoid
# Don't use f-strings in templates.py - keep them reusable
```

### Terminal Output

Use `Rich` for all terminal output:

```python
from rich.console import Console
from rich.panel import Panel

console = Console()
console.print(Panel(response, title="Narrator", style="blue"))
console.print(f"[green]You gain item[/green]: sword")
```

**Color Convention**:
- Green: Success, gains, positive
- Red: Danger, loss, errors
- Blue: Narrative text
- Yellow: Warnings
- Magenta: System messages

## How to Run & Develop

### Initial Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/rag-quest.git
cd rag-quest

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
python -m rag_quest --help
```

### Configuration via Environment Variables

For non-interactive environments, set these env vars:

```bash
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=gemma4:latest
export OLLAMA_BASE_URL=http://localhost:11434
export WORLD_NAME="The Blue Rose Realm"
export WORLD_SETTING="Fantasy World"
export WORLD_TONE="Dark"
export CHARACTER_NAME="Kael"
export CHARACTER_RACE=HUMAN
export CHARACTER_CLASS=FIGHTER

python -m rag_quest
```

### Running the Game

```bash
# Normal play
python -m rag_quest

# With environment config (non-interactive)
LLM_PROVIDER=ollama OLLAMA_MODEL=gemma4:latest python -m rag_quest

# Testing with mock LLM
python test_playthrough_mock.py

# Testing with real Ollama (slow for PDF ingestion)
python test_playthrough.py

# Fast test with small lore
python test_playthrough_fast.py
```

### Testing

Three test scripts available:

**test_playthrough_mock.py** - Uses mock LLM (fastest, ~200ms for 35 turns)
```bash
python test_playthrough_mock.py
# Outputs: playthrough_log_mock.txt, playthrough_results_mock.json
```

**test_playthrough_fast.py** - Uses real Ollama but small lore file (minutes)
```bash
python test_playthrough_fast.py
# Outputs: playthrough_log_fast.txt
```

**test_playthrough.py** - Full integration with PDF lore ingestion (very slow, 30+ min)
```bash
# Only run if you have time
python test_playthrough.py
# Outputs: playthrough_log.txt, playthrough_results.json
```

### Development Workflow

```bash
# Format code
black rag_quest/

# Sort imports
isort rag_quest/

# Type checking
mypy rag_quest/

# Run tests
pytest -v

# Test coverage
pytest --cov=rag_quest --cov-report=html
```

## Known Issues & Current Limitations

### P2 Issues (Major - Block Full Gameplay)

1. **Character Location Not Updating** (rag-quest-jjc)
   - Character stays at starting location despite actions
   - Narrator doesn't parse location changes from responses
   - Needs: Regex pattern matching in `narrator.py` to detect "move to", "go to", etc.

2. **No Combat System Integration** (rag-quest-y1u)
   - Game has no actual combat mechanics
   - Combat turns just return narrative text
   - No HP updates, damage calculation, or encounter tracking
   - Needs: Connect Narrator to `Game.combat()` system

3. **Inventory Not Used During Gameplay** (rag-quest-m2u)
   - Items exist but don't affect narrative or gameplay
   - Narrator never references or modifies inventory
   - Needs: Narrator to parse item gain/loss from responses, update game state

4. **Quest Log Not Integrated** (rag-quest-0ia)
   - QuestLog exists but is never populated
   - No quest offers or completion tracking
   - Needs: Narrator to generate quest offers and track completion

### P3 Issues (Medium - Nice to Have)

1. **PDF Ingestion Extremely Slow** (rag-quest-xvf)
   - LightRAG takes 30+ minutes for 178-page PDF
   - Entity extraction on every chunk is expensive
   - Workaround: Use smaller lore files for testing (5-10 pages)

2. **Insufficient Narrator Context Injection** (rag-quest-aej)
   - Narrator doesn't inject current game state into prompts
   - LLM doesn't see character HP, inventory, location, active quests
   - Needs: Add state to every LLM system prompt

3. **No Error Recovery** (rag-quest-mml)
   - Failed LLM calls crash the game
   - No retry logic or fallback behavior
   - Needs: Try/catch with sensible fallbacks

## Important Implementation Details

### Action Processing (Current Pipeline)

The narrator's `process_action()` method implements this pipeline:

1. **RAG Query**: Ask knowledge graph for relevant context
2. **Message Building**: Compose system prompt + context + history + action
3. **LLM Generation**: Call provider with built messages (can be small model)
4. **State Parsing**: (CURRENTLY MISSING) Extract location changes, NPC meetings, item discoveries
5. **State Update**: (CURRENTLY MISSING) Modify GameState based on parsed changes
6. **RAG Record**: Insert event back into knowledge graph
7. **History Save**: Add to conversation history

**Current Status**: Steps 1-3, 6-7 work. Steps 4-5 are TODO (these are the P2 issues).

**Design insight**: RAG does the heavy lifting in step 1. LLM in step 3 can be lightweight.

### Configuration Flow

1. `config.py:get_config()` checks for existing config file
2. If not found, checks environment variables
3. If neither found and running interactively, calls `setup_first_run()`
4. If neither found and non-interactive, raises ConfigError with helpful message
5. Config saved to `~/.config/rag-quest/config.json`
6. `load_llm_provider()` hydrates the provider from config
7. `create_character_from_config()` and `create_world_from_config()` create game objects

### Lore Ingestion

When user uploads lore during setup:

1. `config.py` gets lore directory path
2. `game.py` calls `WorldRAG.ingest_file()` for each file
3. `ingest.py` reads file (handles .txt, .md, .pdf)
4. `WorldRAG.ingest_text()` chunks and sends to LightRAG
5. User sees progress bar (via Rich)
6. RAG database ready for queries in step 1 of action processing

## Performance Considerations

### RAG Query Timing
- **First query**: 30-60 seconds (LightRAG initialization)
- **Typical query**: 1-3 seconds (cached)
- **Large lore files**: Slower initialization (>100MB)
- **PDF ingestion**: 1-2 minutes per 10 pages (entity extraction is expensive)

**Optimization**: Lazy initialization, hybrid query mode, history pruning

### Memory Usage
- Character & world state: <1 MB
- Conversation history: ~100 KB per 100 exchanges
- RAG storage: 50-200 MB per world

**Optimization**: Limit conversation history to last 6 messages, chunk large lore files

### LLM Response Times (Ollama on Mac)
- **Ollama Gemma 4 E4B (GPU)**: 2-10 seconds per response
- **Ollama Gemma 4 E2B (CPU)**: 10-60 seconds per response
- **Ollama Gemma 4 E4B (larger GPU)**: 1-5 seconds per response

## Common Debugging Scenarios

### "RAG returns irrelevant context"
**Cause**: Poor lore ingestion or vague query  
**Debug**: Check `debug=True` output, print RAG query, inspect ingested lore

### "Character state not updating"
**Cause**: Regex patterns in `_parse_and_apply_changes()` don't match response (or method not called)
**Debug**: Print full response, check regex patterns, verify state change detection is implemented

### "LLM API errors (connection, rate limit)"
**Cause**: API key invalid, rate limit hit, or service down  
**Debug**: Test with curl, verify API key, check provider status

### "Game freezes during LLM call"
**Cause**: Likely timeout or blocking operation  
**Debug**: Check LLM provider logs, verify network connection, try smaller model

### "LLM response quality is poor"
**Cause**: Lightweight model struggling without RAG context  
**Debug**: Check RAG query is specific, verify lore is ingested, ensure context is in messages

### "PDF ingestion takes forever"
**Cause**: LightRAG entity extraction on large PDFs is slow  
**Workaround**: Use smaller lore files (5-10 pages) for testing, full files for production

## Documentation Standards

### Docstring Format

```python
"""Brief one-line summary.

Longer description explaining purpose, usage, and important details.

Args:
    param1: Description of param1
    param2: Description of param2

Returns:
    Description of return value(s)

Raises:
    ValueError: When this happens
"""
```

### Code Comments

- **Explain why**, not what (code shows what)
- Use for non-obvious logic
- Keep updated with code changes
- Use `# TODO` for future work

### Type Hints

Always use type hints:

```python
def process_action(
    action: str,
    game_state: GameState,
) -> tuple[str, GameState]:
    ...
```

## Contributing Workflow

1. **Check beads issues**: `bd list` to see available work
2. **Claim issue**: `bd update <id> --claim` to start work
3. **Branch & develop**: `git checkout -b feature/my-feature`
4. **Make changes**: Write code, write tests, format
5. **Test**: Run `pytest`, check coverage
6. **Format**: Run `black`, `isort`, `mypy`
7. **Commit**: Atomic commits with clear messages
8. **File issues**: For remaining work use `bd create`
9. **Push to remote**: `git push origin feature/my-feature`
10. **PR & review**: Create pull request, address feedback
11. **Merge**: Squash-merge to main when ready

## Resources & References

- **LightRAG Docs**: https://github.com/hkuds/LightRAG
- **httpx Docs**: https://www.python-httpx.org/
- **Rich Docs**: https://rich.readthedocs.io/
- **pytest Docs**: https://docs.pytest.org/
- **Python Async**: https://docs.python.org/3/library/asyncio.html

## Quick Reference: File Locations

- **Config**: `~/.config/rag-quest/config.json`
- **Saves**: `~/.local/share/rag-quest/saves/{world_name}.json`
- **RAG Data**: `~/.local/share/rag-quest/worlds/{world_name}/`
- **Prompts**: `rag_quest/prompts/templates.py`
- **Tests**: `test_playthrough*.py`

## Getting Help

- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Check [AGENTS.md](AGENTS.md) for LLM provider details
- Check [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines
- Check [ROADMAP.md](ROADMAP.md) for planned features
- Review beads issues: `bd show <id>`
- Read docstrings in source code for implementation details

---

**Last Updated**: April 11, 2026  
**For**: Claude and other AI assistants contributing to RAG-Quest

**Key Principle**: LightRAG does the heavy lifting. Keep the LLM lightweight and focused on narrative.
