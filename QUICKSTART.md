# RAG-Quest Quick Start Guide

## Installation

### From Source
```bash
cd /Users/matthewwagner/Desktop/Projects/rag-quest
pip install -e .
```

### Command-Line Usage
Once installed, run:
```bash
rag-quest
```

Or from source directory:
```bash
python3 -m rag_quest
```

## Configuration

The game requires LLM configuration. You can set it via:

### Option 1: Environment Variables (Quick)
```bash
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=qwen3.5:latest
export OLLAMA_BASE_URL=http://localhost:11434
export CHARACTER_NAME="Hero Name"
export CHARACTER_RACE=HUMAN
export CHARACTER_CLASS=FIGHTER
export WORLD_NAME="World Name"
export WORLD_SETTING="Fantasy"
export WORLD_TONE="Heroic"

rag-quest
```

### Option 2: Config File
Create `~/.config/rag-quest/config.json`:
```json
{
  "llm": {
    "provider": "ollama",
    "model": "qwen3.5:latest",
    "base_url": "http://localhost:11434"
  },
  "world": {
    "name": "The Blue Rose Realm",
    "setting": "Fantasy World",
    "tone": "Dark and Mysterious",
    "starting_location": "A quaint tavern"
  },
  "character": {
    "name": "Adventurer",
    "race": "HUMAN",
    "class": "FIGHTER",
    "background": null
  },
  "rag": {
    "profile": "balanced"
  }
}
```

### Option 3: Interactive Setup
If no config exists and stdin is a TTY, the game will prompt you to set up configuration.

## In-Game Commands

### Navigation & Interaction
Simply type actions in natural language:
- `go to the tavern`
- `examine the chest`
- `talk to the merchant`
- `attack the goblin`
- `rest and heal`

### Commands (type with `/` prefix)
- `/help` - Show help and command reference
- `/inventory` or `/i` - View your items
- `/quests` or `/q` - View active quests
- `/status` or `/s` - View character stats with HP bar
- `/look` - Examine your current location
- `/map` - View discovered locations
- `/save` - Save your game progress
- `/quit` - Exit the game (prompts to save)

## Game Features

### Character System
- Name, race (Human, Elf, Dwarf, Halfling, Orc), and class (Fighter, Mage, Rogue, Ranger, Cleric)
- Hit points (HP) that track health
- Equipment and inventory with item rarity
- Experience and leveling (framework in place)

### World System
- Persistent world state with time of day and weather
- Location discovery and tracking
- NPC encounters
- Recent event history

### Combat
- Describe your attacks in natural language
- Damage calculation based on action descriptions
- Health management

### Inventory
- Collect items during gameplay
- Track item rarities (common, uncommon, rare, legendary)
- Weight management (max 100 lbs)

### Quests
- Receive quests from NPCs
- Track quest objectives
- Complete quests to advance

## LLM Providers

### Ollama (Recommended - Local)
Fastest and most private. Run Ollama locally:
```bash
ollama serve
ollama pull qwen3.5:latest  # Or gemma4:latest, mistral, etc.
```

Then set:
```bash
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=qwen3.5:latest
export OLLAMA_BASE_URL=http://localhost:11434
```

### OpenAI
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4o
```

### OpenRouter
```bash
export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY=sk-or-...
export OPENROUTER_MODEL=anthropic/claude-sonnet-4
```

## Gameplay Tips

1. **Be Creative** - Describe what you want to do in detail. The AI responds to creative and specific actions.
2. **Combat** - Describe tactical movements: "dodge and counterattack", "perform a shield bash", etc.
3. **Dialogue** - Talk to NPCs to learn about quests and the world.
4. **Exploration** - Visit new locations to discover items and meet NPCs.
5. **Resource Management** - Watch your HP and manage your inventory carefully.
6. **Save Often** - Use `/save` to save progress before dangerous actions.

## Troubleshooting

### "Configuration not found" Error
Set environment variables or create a config file (see Configuration section above).

### Slow Responses
The game uses fast fallback responses by default. If you want AI narration:
1. Make sure Ollama is running: `ollama serve`
2. Verify the model is pulled: `ollama pull qwen3.5:latest`
3. Check connectivity: `curl http://localhost:11434/api/tags`

### Character Class Not Found
Valid classes are: FIGHTER, MAGE, ROGUE, RANGER, CLERIC (case-sensitive)

### World Not Found
World name is used to store game state. Custom world names work fine.

## Game Flow

1. Start the game with `rag-quest`
2. See welcome screen and game initialization messages
3. Game prints your status bar (character, location, HP, world context)
4. Type actions or commands to interact with the world
5. Narrator responds to your actions
6. Use `/status`, `/inventory`, `/quests` to check progress
7. Use `/save` to save important progress
8. Use `/quit` to exit (with save prompt)

## Save Files

Game progress is saved to:
```
~/.local/share/rag-quest/saves/{WorldName}.json
```

Games are saved automatically every 3 actions. Manual save with `/save` command.

## Next Steps

After the MVP, we're planning:
- Dynamic AI narration with LLM integration
- Knowledge graph queries for world context
- PDF/text lore file ingestion
- Character progression and leveling
- More complex combat mechanics
- Multi-player support
- Distribution via pip/brew

## Have Fun!

RAG-Quest is designed for creative, emergent storytelling. The narrator responds to your actions and helps create a unique adventure each playthrough. Enjoy your adventure in the world of RAG-Quest!

---

**Version:** 0.1.0 (MVP)  
**Status:** Ready for Game Night!  
**License:** MIT
