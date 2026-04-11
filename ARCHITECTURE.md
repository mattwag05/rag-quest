# RAG-Quest Architecture Documentation

This document describes the internal architecture of RAG-Quest, including design decisions, data flows, and extension points.

## System Overview

RAG-Quest is a modular text RPG engine with three main layers:

1. **Presentation Layer** (Terminal UI)
2. **Game Engine Layer** (State & Logic)
3. **Knowledge Layer** (LightRAG)

```
┌─────────────────────────────────────────┐
│         Terminal UI (Rich)              │
│  - Game loop & command handling         │
│  - Player input & response display      │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Game Engine (engine/)              │
│  - Character, World, Inventory          │
│  - Lightweight Narrator (LLM agent)     │
│  - State management & serialization     │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
┌───────▼─────────┐  ┌───▼──────────────────┐
│  LLM Providers  │  │  LightRAG (Heavy     │
│  (llm/)         │  │   Lifting)           │
│  - OpenAI       │  │  (knowledge/)        │
│  - OpenRouter   │  │  - Dual-level query  │
│  - Ollama       │  │  - Knowledge graph   │
│    (~3B-7B      │  │  - Lore storage      │
│     lightweight)│  └──────────────────────┘
└─────────────────┘
```

**Design Principle**: LightRAG's knowledge graph stores all world facts. The Narrator (LLM) is lightweight (~3B-7B parameters) because it retrieves only what's needed per query. This allows consumer-hardware deployment while maintaining narrative quality.

## Module Breakdown

### 1. LLM Providers (`rag_quest/llm/`)

Abstracts LLM APIs behind a consistent interface.

**File Structure:**
- `base.py` - `BaseLLMProvider` abstract class
- `openai_provider.py` - OpenAI API implementation
- `openrouter_provider.py` - OpenRouter API implementation
- `ollama_provider.py` - Local Ollama implementation

**Key Class: `BaseLLMProvider`**

```python
class BaseLLMProvider(ABC):
    def __init__(self, config: LLMConfig)
    async def complete(messages: list[dict]) -> str
    def lightrag_complete_func() -> callable
```

**Design Decisions:**
- Uses httpx for async HTTP (lightweight, no SDK)
- All providers implement same interface
- `lightrag_complete_func()` adapts our interface to LightRAG's expectations
- Temperature & max_tokens are configurable per call
- **Narrator expects lightweight models**: Ollama 7B or Llama deliver excellent results with RAG context

**Extension Point:**
To add a new provider, inherit from `BaseLLMProvider`:

```python
class MyProvider(BaseLLMProvider):
    async def complete(self, messages, temperature=None, max_tokens=None) -> str:
        # Implement API call
        ...
```

### 2. Knowledge Management (`rag_quest/knowledge/`)

Wraps LightRAG and handles lore ingestion. This is the "heavy lifter."

**File Structure:**
- `world_rag.py` - `WorldRAG` wrapper class
- `ingest.py` - File ingestion (txt, md, pdf)

**Key Class: `WorldRAG`**

```python
class WorldRAG:
    def __init__(world_name, llm_config, llm_provider)
    async def initialize()
    async def ingest_text(text, source)
    async def ingest_file(path)
    async def query_world(question, context, param) -> str
    async def record_event(event)
```

**Design Decisions:**
- Lazy initialization (RAG starts on first use)
- Stored in `~/.local/share/rag-quest/worlds/{world_name}/`
- Uses "hybrid" mode for queries (entity + theme matching)
- Events are inserted with metadata for tracking
- **RAG is the "long-term memory"**: all world facts live here, not in the LLM context window

**Data Flow: Query**

```
Player action: "I go to the forest"
       ↓
Narrator builds context query:
"Location: Tavern, Action: I go to the forest"
       ↓
WorldRAG.query_world(context_query)
       ↓
LightRAG returns relevant facts about forests, journeys, etc.
       ↓
Narrator includes this in system prompt (with RAG context, LLM can be lightweight)
       ↓
Lightweight LLM generates response based on injected context
```

**Data Flow: Ingestion**

```
Lore file (txt/md/pdf)
       ↓
ingest.py reads & chunks file
       ↓
For each chunk:
  WorldRAG.ingest_text(chunk, source=filename)
       ↓
LightRAG processes & stores in knowledge graph
```

### 3. Game Engine (`rag_quest/engine/`)

Contains game logic and state management.

**File Structure:**
- `character.py` - Player character (stats, race, class)
- `world.py` - World state (time, weather, locations)
- `inventory.py` - Item management
- `quests.py` - Quest tracking
- `narrator.py` - Lightweight AI narrator & response generation
- `game.py` - Main game loop

**Key Classes:**

**Character**
- Tracks: name, race, class, HP, location, level
- Methods: `take_damage()`, `heal()`, `get_status()`
- Serializable via `to_dict()/from_dict()`

**World**
- Tracks: time of day, weather, visited locations, NPCs met, recent events
- Methods: `advance_time()`, `add_visited_location()`, `get_context()`
- Enums: `TimeOfDay`, `Weather`

**Inventory**
- Tracks: items, max weight capacity
- Methods: `add_item()`, `remove_item()`, `get_total_weight()`
- Items have: name, description, weight, quantity, rarity

**QuestLog**
- Tracks: quests with objectives and status
- Methods: `add_quest()`, `get_active_quests()`, `complete_quest()`
- Quests can have multiple objectives

**Narrator**
- Core AI logic
- Methods: `process_action()` - main entry point
- Performs: RAG query, message building, LLM call, state parsing
- Maintains conversation history
- **Design note**: Narrator is intentionally simple; RAG complexity does the work

**GameState**
- Bundles all state together
- Serializable to JSON
- Passed to game loop and all systems

**Game Loop**

```python
async def run_game(game_state):
    while character.is_alive():
        1. Display status (HP, location, time)
        2. Get player input
        3. If command: handle_command()
        4. Else: narrator.process_action()
        5. Display response
        6. Auto-save (periodic)
```

### 4. Configuration (`rag_quest/config.py`)

Interactive setup and configuration management.

**Functions:**
- `get_config()` - Get existing or run setup
- `setup_first_run()` - Interactive wizard
- `load_llm_provider()` - Load provider from config
- `create_character_from_config()` - Hydrate character
- `create_world_from_config()` - Hydrate world

**Config File Location:** `~/.config/rag-quest/config.json`

**Config Structure:**
```json
{
  "llm": {
    "provider": "openrouter|openai|ollama",
    "model": "string",
    "api_key": "string (optional)",
    "base_url": "string (optional)"
  },
  "world": {
    "name": "string",
    "setting": "string",
    "tone": "string",
    "starting_location": "string",
    "lore_path": "string (optional)"
  },
  "character": {
    "name": "string",
    "race": "Human|Elf|Dwarf|Halfling|Orc",
    "class": "Fighter|Mage|Rogue|Ranger|Cleric",
    "background": "string (optional)"
  }
}
```

### 5. Prompts (`rag_quest/prompts/templates.py`)

System prompts that shape AI behavior.

**Templates:**
- `NARRATOR_SYSTEM` - Main DM prompt
- `WORLD_GENERATOR` - For future world generation
- `NPC_DIALOGUE` - For NPC interactions
- `CHARACTER_INTRO` - Initial character intro
- `ACTION_PARSER` - For extracting action details

**Design Note:**
Prompts are strings, not f-strings. This allows dynamic filling of context at runtime while keeping prompts editable.

## Data Flows

### Action Processing (Core Loop)

```
Player Input: "I search the desk for clues"
       ↓
Narrator.process_action(input)
       ↓
1. Query RAG:
   question = "Player action: search desk for clues"
   context = "Location: study, Recent: found a letter"
   ↓
   RAG returns: "Desk contains: old books, jewels, secret compartment..."
       ↓
2. Build Messages:
   - System prompt (NARRATOR_SYSTEM)
   - RAG context (injected knowledge)
   - World state (time, location, character)
   - Conversation history (last 3 exchanges)
   - Current input
       ↓
3. Generate Response:
   llm.complete(messages, temperature=0.85, max_tokens=1024)
   ↓ (Lightweight model sufficient with RAG context)
   ↓
   Response: "You pull open the drawer carefully..."
       ↓
4. Parse for State Changes:
   - Look for location changes ("move to X", "enter X")
   - Look for NPC meetings ("meet X", "encounter X")
   - Look for item discoveries ("find X", "gain X")
       ↓
5. Update State:
   - Modify character location if detected
   - Add NPCs to world.npcs_met
   - Add items to world.discovered_items
   - Add event to world.recent_events
       ↓
6. Record to RAG:
   world_rag.record_event(f"{character.name} searched the desk")
       ↓
7. Save History:
   conversation_history.append({"role": "user", ...})
   conversation_history.append({"role": "assistant", ...})
       ↓
Return Response to Display
```

### Game State Serialization

```
Character, World, Inventory, QuestLog
       ↓
Each has to_dict() method
       ↓
GameState.to_dict() combines all
       ↓
json.dump() to ~/.local/share/rag-quest/saves/{world_name}.json
       ↓
Load: json.load() + from_dict() for each component
```

## Design Patterns

### 1. Provider Pattern (LLM)

Different implementations (OpenAI, OpenRouter, Ollama) behind common interface.

**Benefits:**
- Easy to swap providers
- Easy to add new providers
- Client code doesn't need to know about specific APIs

### 2. State Pattern (GameState)

All game state bundled together and serializable.

**Benefits:**
- Clean save/load mechanism
- Easy to reason about game state
- Supports multiple games/saves

### 3. Adapter Pattern (LightRAG)

`lightrag_complete_func()` adapts our complete() interface to LightRAG's expectations.

**Benefits:**
- LightRAG can use any LLM provider
- Our providers don't need to know about LightRAG

### 4. Template Method (Narrator)

`process_action()` defines the template; sub-steps can be overridden.

**Benefits:**
- Clear, testable flow
- Easy to add new processing steps
- Can mock/test individual steps

## Extension Points

### Adding a New LLM Provider

1. Create `rag_quest/llm/my_provider.py`
2. Inherit from `BaseLLMProvider`
3. Implement `async def complete(messages, ...)`
4. Add to `config.py` setup wizard
5. Add to `llm/__init__.py` imports

### Adding a New Game Mechanic

1. Add to appropriate engine module (character.py, world.py, etc.)
2. Update `GameState.to_dict()` for serialization
3. Update `GameState.from_dict()` for deserialization
4. Update game loop in `game.py` if needed
5. Add commands in `_handle_command()` if user-facing

### Custom Narrator Behavior

Override `Narrator.process_action()` or modify:
- `_build_messages()` - Change what context is included
- `_parse_and_apply_changes()` - Add new state detection
- Prompt templates in `prompts/templates.py`

### Adding New Commands

In `game.py`, add to `_handle_command()`:

```python
elif cmd == "/mynewcommand":
    # Your logic here
    console.print("Result")
```

## Performance Considerations

### RAG Query Timing

- First query: 30-60 seconds (LightRAG initialization)
- Subsequent queries: 1-3 seconds (cached)
- Large lore files: Slower initialization
- Query response: Depends on LLM provider

### Memory Usage

- Character & world state: <1 MB
- Conversation history: ~100 KB per 100 exchanges
- LightRAG storage: ~50-200 MB per world (grows with lore)

### LLM Model Size Impact

- **3B model + RAG**: Fast, excellent quality
- **7B model + RAG**: Very good quality, good speed
- **70B model + RAG**: Excellent quality, slower
- **Large model without RAG**: Slower, hallucination risk

**Key insight**: A 7B model with RAG often outperforms a 70B model without RAG.

### Optimization Tips

1. **Lore chunking** - Break large lore files into smaller pieces
2. **History pruning** - Conversation history is limited to last 6 messages
3. **Lazy initialization** - RAG doesn't start until first query
4. **Hybrid queries** - Balances speed vs. relevance
5. **Lightweight models** - Use 7B or smaller with strong RAG

## Testing Strategy

### Unit Tests

- `test_llm_providers.py` - Mock HTTP calls
- `test_engine/` - Test character, world, inventory in isolation
- `test_narrator.py` - Mock LLM calls
- `test_config.py` - Configuration loading

### Integration Tests

- Full game loop with mock provider
- Save/load round-trip
- Multi-turn conversation consistency

### Manual Testing

- Try with different providers
- Test with custom lore files
- Verify state persistence
- Check error handling

## Debugging

### Enable Debug Mode

```bash
python -m rag_quest --debug
```

This shows:
- Full tracebacks
- RAG query results
- Message building
- State changes

### Common Issues

**RAG returning irrelevant context:**
- Check lore ingestion
- Verify query is descriptive
- Try hybrid vs other modes

**Character state not updating:**
- Check regex patterns in `_parse_and_apply_changes()`
- Verify state changes are actually in response
- Check console output for parsed changes

**LLM API errors:**
- Verify API key
- Check rate limits
- Confirm model name
- Test with curl

## Future Architecture Improvements

1. **Plugin System** - Allow third-party providers/mechanics
2. **Event Bus** - Decouple narrator from state updates
3. **Async RAG** - Queue queries instead of blocking
4. **Memory Management** - Compress old conversation history
5. **Metrics** - Track game events, costs, performance
6. **Multiplayer** - State sync via Tailscale or similar

---

*Last Updated: v0.1.0*

**Core Principle**: LightRAG does the heavy lifting. Keep the LLM lightweight and focused on narrative synthesis.
