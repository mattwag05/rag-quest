# CLAUDE.md - AI Assistant Developer Guide

This document provides AI assistants (Claude, GPT, etc.) with a comprehensive understanding of RAG-Quest architecture, conventions, and development practices. Use this as your primary reference when contributing to the codebase.

## Project Overview

**RAG-Quest** is an AI-powered D&D-style text RPG that uses LightRAG (a knowledge graph system) to eliminate hallucinations in narrative generation. The game maintains consistency through a RAG backend that stores and retrieves world knowledge, allowing a lightweight AI narrator to generate coherent, context-aware storytelling.

**Core Design Philosophy**: LightRAG does the heavy lifting. The LLM acting as dungeon master is intentionally kept small—~3B parameters, ≤8K token context—because it doesn't memorize the world. Instead, LightRAG's dual-level retrieval (entity matching + vector similarity) injects precisely the relevant knowledge per query. This architecture enables RAG-Quest to run entirely on consumer hardware with local models via Ollama, while producing narrative quality comparable to much larger models running blind.

**Why this matters**: A 7B model with excellent RAG context beats a 70B model without RAG. The knowledge graph is the "long-term memory"; the LLM is just the "narrator."

**Current Version**: v0.1 (narrative + dialogue + inventory, single-player)

**Technology Stack**:
- **Python 3.11+** - Core language
- **LightRAG** - Knowledge graph backend (the architectural cornerstone)
- **httpx** - Async HTTP for LLM APIs
- **Rich** - Terminal UI and formatting
- **PyMuPDF** - PDF text extraction
- **pytest** - Testing framework

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
│   │   ├── character.py         # Player character
│   │   ├── world.py             # World state
│   │   ├── inventory.py         # Item management
│   │   ├── quests.py            # Quest tracking
│   │   ├── narrator.py          # Lightweight AI narrator & response generation
│   │   └── game.py              # Main game loop
│   └── prompts/                 # System prompts
│       ├── __init__.py
│       └── templates.py         # Prompt templates for narrator
├── lore/                        # Example/default lore
│   ├── .gitkeep
│   └── EXAMPLE_WORLD.md         # Example world definition
├── saves/                       # Player save games (git-ignored)
│   └── .gitkeep
├── tests/                       # Unit & integration tests
├── pyproject.toml               # Project metadata & dependencies
├── README.md                    # User-facing documentation
├── ARCHITECTURE.md              # Technical architecture
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
    async def complete(self, messages: list[dict], 
                      temperature: float = None,
                      max_tokens: int = None) -> str
    def lightrag_complete_func(self) -> callable
```

**Key Implementations**:
- `OpenAIProvider` - Direct OpenAI API calls
- `OpenRouterProvider` - OpenRouter.ai (multi-model access)
- `OllamaProvider` - Local Ollama inference (~3B-70B models)

**Design Patterns**:
- All providers are fully async
- Uses `httpx.AsyncClient` for HTTP
- `lightrag_complete_func()` adapts interface for LightRAG compatibility
- Temperature and max_tokens are call-time configurable
- **Narrator uses lightweight providers**: Ollama 7B or Llama-2 deliver excellent results

**Adding a New Provider**:
1. Create `rag_quest/llm/my_provider.py`
2. Inherit from `BaseLLMProvider`
3. Implement `async def complete()` method
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
- Attributes: time_of_day, weather, visited_locations, npcs_met, recent_events
- Enums: `TimeOfDay`, `Weather`
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
- Core method: `async process_action(player_input: str) -> tuple[str, GameState]`
- Orchestrates: RAG query → message building → LLM call → state parsing
- Maintains conversation history (last 6 messages)
- Returns: (response text, updated game state)
- **Design note**: Narrator is intentionally simple; RAG complexity does the world knowledge work

### Knowledge Layer (knowledge/)

**WorldRAG** - LightRAG wrapper (the heavyweight)
```python
class WorldRAG:
    async def initialize()
    async def ingest_text(text: str, source: str)
    async def ingest_file(path: str)
    async def query_world(question: str, context: str) -> str
    async def record_event(event: str)
```

**Design Decisions**:
- Lazy initialization (RAG starts on first query)
- Storage: `~/.local/share/rag-quest/worlds/{world_name}/`
- Uses "hybrid" mode for queries (entity + theme matching)
- Events recorded with metadata for tracking
- **RAG is the "long-term memory"**: all world facts live here, not in the LLM context

**Ingest Module** (ingest.py):
- Handles: .txt, .md, .pdf files
- Chunks large files automatically
- Integrates with `WorldRAG.ingest_text()`

## Key Patterns & Conventions

### Async/Await Pattern

All I/O operations are async (LLM calls, file I/O):

```python
async def process_action(action: str) -> str:
    context = await world_rag.query_world(action)
    response = await llm_provider.complete(messages)
    return response
```

**Important**: Always use `async def` and `await` for LLM/RAG calls. Use `asyncio.run()` in sync contexts (like `__main__.py`).

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

### Running the Game

```bash
# Normal play
python -m rag_quest

# With debug output
python -m rag_quest --debug

# Testing a specific provider
OPENAI_API_KEY=sk-... python -m rag_quest
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

### Testing Guidelines

**Unit Tests**:
- Mock LLM calls and RAG queries
- Test state transitions
- Test serialization round-trips
- Test config loading

**Integration Tests**:
- Full game loop with mock provider
- Save/load cycles
- Multi-turn conversations
- Lore ingestion

**Test Location**: `tests/` directory, mirror `rag_quest/` structure

## Important Implementation Details

### Action Processing (Core Loop)

The narrator's `process_action()` method implements this pipeline:

1. **RAG Query**: Ask knowledge graph for relevant context
2. **Message Building**: Compose system prompt + context + history + action
3. **LLM Generation**: Call provider with built messages (can be small model)
4. **State Parsing**: Extract location changes, NPC meetings, item discoveries from response
5. **State Update**: Modify GameState based on parsed changes
6. **RAG Record**: Insert event back into knowledge graph
7. **History Save**: Add to conversation history

See `narrator.py` for implementation details.

**Design insight**: RAG does the heavy lifting in step 1. LLM in step 3 can be lightweight.

### Configuration Flow

1. `config.py:get_config()` checks for existing config
2. If not found, calls `setup_first_run()` (interactive wizard)
3. User selects: provider → model → world setup → character
4. Config saved to `~/.config/rag-quest/config.json`
5. `load_llm_provider()` hydrates the provider from config
6. `create_character_from_config()` and `create_world_from_config()` create game objects

### Lore Ingestion

When user uploads lore during setup:

1. `config.py` gets lore directory path
2. `game.py` or `__main__.py` calls `WorldRAG.ingest_file()` for each file
3. `ingest.py` reads file (handles .txt, .md, .pdf)
4. `WorldRAG.ingest_text()` chunks and sends to LightRAG
5. User sees progress bar (via Rich)
6. RAG database ready for queries in step 1 of action processing

## Performance Considerations

### RAG Query Timing
- **First query**: 30-60 seconds (LightRAG initialization)
- **Typical query**: 1-3 seconds (cached)
- **Large lore files**: Slower initialization (>100MB)

**Optimization**: Lazy initialization, hybrid query mode, history pruning

### Memory Usage
- Character & world state: <1 MB
- Conversation history: ~100 KB per 100 exchanges
- RAG storage: 50-200 MB per world

**Optimization**: Limit conversation history to last 6 messages, chunk large lore files

### Async Considerations
- All LLM calls are concurrent (no blocking)
- RAG queries block narrator (sequential)
- Consider queue-based RAG for future scaling

## Common Debugging Scenarios

### "RAG returns irrelevant context"
**Cause**: Poor lore ingestion or vague query  
**Debug**: Check `debug=True` output, print RAG query, inspect ingested lore

### "Character state not updating"
**Cause**: Regex patterns in `_parse_and_apply_changes()` don't match response  
**Debug**: Print full response, check regex patterns, verify state change detection

### "LLM API errors (connection, rate limit)"
**Cause**: API key invalid, rate limit hit, or service down  
**Debug**: Test with curl, verify API key, check provider status

### "Game freezes during LLM call"
**Cause**: Async not properly awaited or blocking I/O  
**Debug**: Check all LLM calls are awaited, look for blocking operations

### "LLM response quality is poor"
**Cause**: Lightweight model struggling without RAG context  
**Debug**: Check RAG query is specific, verify lore is ingested, ensure context is in messages

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
async def process_action(
    action: str,
    game_state: GameState,
) -> tuple[str, GameState]:
    ...
```

## Contributing Workflow

1. **Fork & Branch**: `git checkout -b feature/my-feature`
2. **Develop**: Make changes, write tests, format code
3. **Test**: Run `pytest`, check coverage
4. **Format**: Run `black`, `isort`, `mypy`
5. **Commit**: Atomic commits with clear messages
6. **PR**: Push and create pull request with description
7. **Review**: Address feedback, re-test
8. **Merge**: Squash-merge to main

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
- **Tests**: `tests/`

## Getting Help

- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Check [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines
- Review [ROADMAP.md](ROADMAP.md) for planned features
- Check GitHub issues for known problems
- Read docstrings in source code for implementation details

---

**Last Updated**: April 2026  
**For**: Claude and other AI assistants contributing to RAG-Quest

**Key Principle**: LightRAG does the heavy lifting. Keep the LLM lightweight and focused on narrative.
