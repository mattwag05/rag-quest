# ARCHITECTURE.md — RAG-Quest System Design (v0.5.3)

This document describes RAG-Quest's system architecture, how all components integrate, and the design decisions that make it work.

## Core Architecture: LightRAG + Lightweight LLM

```
┌─────────────────────────────────────────────────────────┐
│                    Game Loop (game.py)                   │
│  Synchronous turn-based input/output, no async          │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              Narrator (narrator.py)                      │
│  Orchestrates LLM calls with RAG context                │
└─────────────────────────────────────────────────────────┘
                   ↙              ↘
        ┌──────────────┐    ┌──────────────┐
        │  WorldRAG    │    │  LLM Provider│
        │(knowledge.py)│    │(llm/\*)      │
        │              │    │              │
        │ - Entity+    │    │ - Ollama     │
        │   vector     │    │ - OpenAI     │
        │   search     │    │ - OpenRouter │
        │ - Event      │    │              │
        │   recording  │    │ Lightweight: │
        │              │    │ Gemma 4 E2B/E4B
        └──────────────┘    └──────────────┘
             ↓                      ↓
    [RAG Knowledge Graph]  [LLM API or Local]
    ~/.local/share/        Produces narrative
    rag-quest/worlds/      responses
```

## Key Design Decision: Division of Responsibility

**LightRAG**: "What is the world like?"
- Stores all facts, entities, relationships
- Answers knowledge queries
- Maintains consistency
- Grounded, factual

**LLM Narrator**: "Tell me a story based on this context"
- Receives player action + RAG context
- Generates narrative response
- Can be small (2-4B parameters)
- Only needs good storytelling skills, not world knowledge

**Game State**: "What's the player's current status?"
- Character attributes, inventory, quests
- Serializable to JSON
- Restored on load
- Independent from narration

## System Components

### 1. Game Loop (engine/game.py)

**Synchronous turn-based game loop**:

```python
def run_game():
    # 1. Load/create character and world
    game_state = create_game_state()
    world_rag = WorldRAG(game_state.world.name)
    world_rag.initialize()
    
    # 2. Main loop
    while game_running:
        # Print current state
        print_status(game_state)
        
        # Get player input
        action = input("> ")
        
        # Handle commands (/inventory, /help, etc.)
        if action.startswith("/"):
            handle_command(action, game_state)
        else:
            # Normal action: call narrator
            response = narrator.process_action(action, game_state)
            print(response)
            
            # Auto-save every N turns
            if turn_count % AUTO_SAVE_INTERVAL == 0:
                save_game(game_state)
```

**All commands implemented**:
- `/i` — Inventory
- `/s` — Stats
- `/q` — Quests
- `/p` — Party
- `/rel` — Relationships
- `/h` — Help
- `/tutorial` — Interactive tutorial
- `/config` — Settings
- `/new` — New game
- `/save` — Manual save
- `/exit` — Quit

### 2. Narrator (engine/narrator.py)

**Orchestrates LLM narration with RAG context**:

```python
def process_action(self, action: str, game_state: GameState) -> str:
    # 1. Query RAG for relevant world knowledge
    world_context = self.world_rag.query_world(
        f"Context for action: {action}",
        context=game_state.get_context()
    )
    
    # 2. Build LLM messages
    messages = [
        {
            "role": "system",
            "content": NARRATOR_SYSTEM_PROMPT + world_context
        },
        {"role": "user", "content": action}
    ]
    
    # Add conversation history (last 6 messages for context)
    messages.extend(self.conversation_history[-6:])
    
    # 3. Call LLM (synchronous)
    response = self.llm_provider.complete(messages)

    # 4. Update conversation history
    self.conversation_history.append({"role": "assistant", "content": response})

    return response
```

Post-turn, `engine/turn.py::collect_post_turn_effects` reads
`narrator.last_change` and shadow-writes the structured state delta
into `WorldDB` (events, entities, relationships). LightRAG is no
longer written per turn — v0.9+ treats LightRAG as a read-only lore
store and keeps per-turn facts in SQLite.

**Key insight**: The RAG knowledge graph provides world context. The LLM just needs to be a good storyteller.

### 3. Knowledge Graph (knowledge/world_rag.py)

**LightRAG wrapper for persistent world knowledge**:

```python
class WorldRAG:
    def __init__(self, world_name: str):
        self.world_name = world_name
        self.index_path = f"~/.local/share/rag-quest/worlds/{world_name}"
    
    def initialize(self):
        """Initialize RAG index (lazy, on first query)."""
        # Creates or loads existing index
        self.rag = LightRAG(
            working_dir=self.index_path,
            llm_model_func=self.llm_provider.lightrag_complete_func()
        )
    
    def query_world(self, question: str, context: str = "") -> str:
        """Retrieve relevant knowledge for a question."""
        # LightRAG dual-level retrieval:
        # 1. Entity matching (exact entity names)
        # 2. Vector similarity (semantic matching)
        return self.rag.query(question, param=QueryParam(...))

    # (v0.9+: per-turn event writes moved to WorldDB.
    # WorldRAG is now a read-only lore store. ingest_text / ingest_file
    # are the only write paths — used for world lore and /canonize.)

    def ingest_text(self, text: str, source: str = "manual"):
        """Add knowledge from text (lore)."""
        self.rag.insert_text(text, source)
```

**Storage**: `~/.local/share/rag-quest/worlds/{world_name}/`
- Knowledge graph index
- Entity embeddings
- Relationship metadata

**Why separate from game state**: The RAG knowledge graph is the "persistent world knowledge." The game state is the "player's current status." They serve different purposes.

### 4. Game State Serialization

**All game objects are fully serializable**:

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
    
    def to_dict(self) -> dict:
        return {
            "character": self.character.to_dict(),
            "world": self.world.to_dict(),
            "inventory": self.inventory.to_dict(),
            # ... etc
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GameState':
        return cls(
            character=Character.from_dict(data["character"]),
            world=World.from_dict(data["world"]),
            # ... etc
        )
```

**Save format**: JSON at `~/.local/share/rag-quest/saves/{world_name}.json`

**Design principle**: Game state is separate from world knowledge. Saves capture "what the player has done," not "what the world knows."

### 5. LLM Provider Interface (llm/base.py)

**All providers implement the same interface**:

```python
class BaseLLMProvider(ABC):
    def complete(self,
                messages: list[dict],
                temperature: float = None,
                max_tokens: int = None,
                **kwargs) -> str:
        """Call LLM synchronously and return response."""
    
    def lightrag_complete_func(self):
        """Return async function for LightRAG compatibility."""
```

**Why synchronous**: Turn-based game doesn't need async. Simpler, cleaner code.

**Implementations**:
- **OllamaProvider** — `POST http://localhost:11434/api/generate`
- **OpenAIProvider** — `POST https://api.openai.com/v1/chat/completions`
- **OpenRouterProvider** — `POST https://openrouter.ai/api/v1/chat/completions`

### 6. Configuration Management (config.py)

**Persistent, environment-aware configuration**:

```python
class ConfigManager:
    def __init__(self):
        # Load from ~/.config/rag-quest/config.json
        # Fall back to environment variables
        # Use sensible defaults
        self._config = self._load_config()
    
    def get(self, key: str) -> Any:
        # Returns nested config (e.g., "llm.provider")
        pass
    
    def set(self, key: str, value: Any) -> None:
        # Update and immediately persist
        pass
```

**Three initialization modes**:
1. **Fresh Adventure** — Blank world, new character
2. **Quick Start** — Choose template (4 built-in)
3. **Upload Lore** — Ingest custom PDF/text files

**Environment variables** (for scripting):
```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=gemma4:e4b
OLLAMA_BASE_URL=http://localhost:11434
RAG_PROFILE=balanced
WORLD_NAME="My World"
CHARACTER_NAME="Hero"
```

### 7. Save System (engine/saves.py)

**Multi-slot save system with auto-save rotation**:

```python
class SaveManager:
    def save_game(self, game_state: GameState, slot: int = -1) -> str:
        # slot=-1 means auto-save (rotates oldest)
        # Returns path to saved file
    
    def load_game(self, slot: int) -> GameState:
        # Loads from slot, handles format migration
    
    def export_save(self, slot: int, output_path: str):
        # Export as .rqsave for sharing
    
    def import_save(self, input_path: str, slot: int):
        # Import from .rqsave
```

**Save file structure**:
```
~/.local/share/rag-quest/saves/
├── MyWorld_slot_1.json
├── MyWorld_slot_2.json
├── MyWorld_auto_1.json  (most recent)
├── MyWorld_auto_2.json  (previous)
└── MyWorld_auto_3.json  (oldest)
```

**Format migration**: Old save formats are automatically upgraded. No loss of data.

### 8. Character & World State

**Character** — Player character:
- Attributes: name, race, class, level, HP, XP
- Six D&D attributes: STR, DEX, CON, INT, WIS, CHA
- Location, status effects
- Methods: `take_damage()`, `heal()`, `level_up()`, `get_status()`

**World** — World state:
- name, setting, tone, time_of_day, weather
- visited_locations, npcs_met
- recent_events (last 5 for narrative context)
- Methods: `advance_time()`, `add_visited_location()`, `get_context()`

**Inventory** — Item management:
- items dict with quantities
- max_weight capacity
- Methods: `add_item()`, `remove_item()`, `get_total_weight()`

### 9. Combat System (engine/combat.py)

**D&D-style turn-based combat**:

```python
class CombatEncounter:
    def __init__(self, player: Character, enemy: Enemy):
        self.player = player
        self.enemy = enemy
        self.initiative = self.calculate_initiative()
    
    def take_turn(self, combatant: Character, action: str):
        # Handle attack, defend, cast spell, flee
        # Apply damage, critical hits, etc.
    
    def calculate_damage(self, attacker: Character, defender: Character) -> int:
        # Base damage + attribute modifiers + critical hits
    
    def is_combat_over(self) -> bool:
        # Check if anyone has 0 HP
```

**Dice rolling**: d4, d6, d8, d10, d12, d20 support.

### 10. Quest System (engine/quests.py)

**Quest chains with objectives**:

```python
@dataclass
class Quest:
    title: str
    description: str
    objectives: list[str]
    status: QuestStatus  # pending, active, completed
    reward_xp: int
    reward_items: list[str]

class QuestLog:
    def add_quest(self, quest: Quest):
        """Add new quest."""
    
    def complete_quest(self, quest_id: str):
        """Mark quest complete, award rewards."""
    
    def get_active_quests(self) -> list[Quest]:
        """Get all pending/active quests."""
```

### 11. NPC & Relationship System (engine/relationships.py)

**Track NPC trust and faction reputation**:

```python
class RelationshipManager:
    def add_npc(self, name: str, role: str, disposition: float = 0.0):
        """Add NPC with initial disposition."""
    
    def change_disposition(self, npc_name: str, delta: float):
        """Modify trust level (+1.0 ally, -1.0 enemy)."""
    
    def create_faction(self, name: str, description: str):
        """Create a faction."""
    
    def change_reputation(self, faction_name: str, delta: float):
        """Change faction reputation."""
```

### 12. Achievement System (engine/achievements.py)

**11 built-in achievements**:

```python
class AchievementEngine:
    def check_achievements(self, game_state: GameState):
        """Called each turn, checks for triggers."""
        # Automatically detects and notifies
    
    def get_achievements(self) -> list[Achievement]:
        """Get all with progress."""
```

**Achievements**: Explorer, Warrior, Diplomat, Scholar, Treasure Hunter, Dragon Slayer, Indestructible, Hoarder, Wealthy, Legendary, Well-Connected.

### 13. Procedural Dungeon Generation (engine/dungeon.py)

**Randomly generated dungeons**:

```python
class DungeonGenerator:
    def generate_level(self, level: int) -> DungeonLevel:
        """5-15 rooms, ASCII map, difficulty scaling."""
        # Returns DungeonLevel with rooms and map
    
    def generate_room(self, room_type: str) -> Room:
        """Generate single room with enemies and loot."""
```

### 14. Text-to-Speech (engine/tts.py)

**Optional TTS narration**:

```python
class TTSEngine:
    def __init__(self, provider: str = "pyttsx3"):
        # pyttsx3: offline, local voices
        # gTTS: online, more natural
    
    def speak(self, text: str):
        """Convert text to speech and play."""
```

### 15. Multiplayer (multiplayer/)

**Hot-seat multiplayer**:

```python
class MultiplayerSession:
    def __init__(self, world: World, max_players: int = 4):
        self.world = world
        self.players: list[Character] = []
        self.current_player_index = 0
    
    def add_player(self, character: Character):
        """Add player to session."""
    
    def next_turn(self):
        """Rotate to next player."""
    
    def trade_items(self, player1: Character, player2: Character, items: list[str]):
        """Enable item trading."""
```

### 16. World Sharing (worlds/)

**Export/import worlds**:

```python
class WorldExporter:
    def export_world(self, world: World, output_path: str):
        """Package as .rqworld file."""
        # Includes RAG knowledge graph
        # Compressed format
    
class WorldImporter:
    def import_world(self, input_path: str) -> World:
        """Load from .rqworld file."""
        # Validates integrity
        # Merges knowledge
```

## Data Flow: A Single Turn

```
1. Player types action
   > "I cast fireball at the dragon"
   
2. Game loop receives input
   action = "I cast fireball at the dragon"
   
3. Query RAG for context
   context = "You're in the dragon's lair. The dragon is
   enraged. You have mana for one spell."
   
4. Build LLM prompt
   messages = [
     system: NARRATOR_SYSTEM_PROMPT + context,
     user: action
   ]
   
5. Call LLM (synchronous)
   response = llm_provider.complete(messages)
   → "The fireball erupts from your hands, engulfing the
      dragon in flames. It roars in pain..."

6. Shadow-write to WorldDB
   collect_post_turn_effects(game_state, player_input)
   → state_parser.parse_narrator_response(response) → StateChange
   → state_event_mapping.translate(change) → typed writes
   → world_db.record_event(...) + upsert_entity(...) + ...

7. Update game state
   character.mana -= cost
   enemy.hp -= damage

8. Auto-save
   save_game(game_state)

9. Print response
   "The fireball erupts..."

10. Loop (back to step 2)
```

## Synchronous Architecture

**Design decision**: Everything is synchronous (not async).

Why:
- Turn-based game doesn't benefit from async
- Simpler code (no callbacks, no event loops)
- Easier debugging
- Clear execution flow

How LightRAG compatibility is maintained:
- LightRAG's async API is wrapped with `ThreadPoolExecutor`
- `WorldRAG._run_async()` bridges sync/async gap
- No async/await in game code

## Error Handling Philosophy (v0.5.2)

**No tracebacks shown to users.** Every error path returns a friendly message.

**Error categories**:
1. **Ollama not running** — Setup guidance
2. **Model not found** — `ollama pull` instruction
3. **API key invalid** — Check `/config` or env vars
4. **Timeout** — Try faster RAG profile or smaller model
5. **File not found** — Path and retry instruction

All handled in try/except blocks with user-friendly messages.

## Performance Characteristics

**Latency**:
- RAG query: 1-3 sec (typical), 30-60 sec (first)
- LLM response: 2-10 sec (Gemma 4 E4B), 10-60 sec (E2B)
- Total turn: 3-70 sec depending on hardware/model

**Memory**:
- Game state: <50 MB
- RAG index: 50-200 MB per world
- Conversation history: ~100 KB per 100 exchanges

**Storage**:
- Save file: ~50-100 KB per save
- RAG index: ~100 MB per ~50K entities

## Testing Strategy

**Test levels**:
1. **Unit tests** — Individual components (Character, Inventory, etc.)
2. **Integration tests** — Systems working together (Game loop, Narrator, RAG)
3. **Playthrough tests** — Full game from start to finish

**Test files**:
- `test_v051_core.py` — Core systems (51+ tests)
- `test_v053.py` — v0.5.3 features and 25-turn validation (25 tests)
- `test_all_fixes.py` — API compatibility (41 tests)
- Integration test playthroughs (35+ turns)

## Design Principles

1. **Separation of Concerns** — RAG = knowledge, LLM = narrative, GameState = player status
2. **Synchronous Game Loop** — Clean, simple, no async complexity
3. **Full Serialization** — All state saved and loaded as JSON
4. **LightRAG-First** — Knowledge graph is the source of truth
5. **Lightweight Narrator** — Small models work great with good RAG
6. **Consumer Hardware** — Everything runs locally on modest hardware
7. **Zero Friction** — Setup is automatic, errors are friendly
8. **Backwards Compatibility** — All saves migrate cleanly between versions

---

**Last Updated**: April 2026  
**Version**: 0.5.3
