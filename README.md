# RAG-Quest

An AI-powered D&D-style text RPG that uses LightRAG knowledge graph backend to eliminate hallucinations. Play in immersive fantasy worlds crafted by AI, where consistency and lore accuracy are guaranteed.

## Features

- **LightRAG Integration**: Knowledge graph backend ensures the AI narrator never forgets world details or contradicts established lore
- **Multiple LLM Providers**: Works with OpenAI, OpenRouter, or local Ollama models
- **Dynamic Narration**: Every action generates vivid, contextual responses from an AI Dungeon Master
- **World Persistence**: Your game saves include the full knowledge graph, so picking up where you left off is seamless
- **Lore Ingestion**: Load your own lore documents (txt, md, pdf) to build custom worlds
- **Rich Terminal UI**: Beautiful colored text, formatted panels, and intuitive commands

## Quick Start

### Installation

```bash
# Clone or download the project
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
1. Choose an LLM provider (OpenAI, OpenRouter, or Ollama)
2. Configure the world (name, setting, tone)
3. Create your character (name, race, class)

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

## Architecture

### Core Components

#### LLM Providers (`rag_quest/llm/`)
- **BaseLLMProvider**: Abstract base class for all providers
- **OpenAIProvider**: Direct OpenAI API integration
- **OpenRouterProvider**: OpenRouter.ai integration
- **OllamaProvider**: Local Ollama support

#### Knowledge Management (`rag_quest/knowledge/`)
- **WorldRAG**: Wraps LightRAG for game-specific queries and updates
- **Ingest**: File handling for lore documents (txt, md, pdf)

#### Game Engine (`rag_quest/engine/`)
- **Character**: Player character with stats, inventory, location
- **World**: World state (time, weather, visited locations, NPCs met)
- **Inventory**: Item management with weight and rarity
- **QuestLog**: Quest tracking and objectives
- **Narrator**: AI narrator that queries RAG and generates responses
- **GameState**: Complete serializable game state

#### Configuration
- **config.py**: Setup wizard and configuration management
- **prompts/templates.py**: System prompts for narrator and world generation

### Data Flow

1. **Player Action** → Narrator receives input
2. **RAG Query** → WorldRAG queries LightRAG for relevant context
3. **Message Building** → System prompt + context + history + new action
4. **LLM Generation** → Provider generates response
5. **State Parsing** → Extract location changes, NPC meetings, item discoveries
6. **RAG Update** → Record new facts back to knowledge graph
7. **Display & Save** → Show response, auto-save game state

## Usage Guide

### Commands

```
/inventory          - View your items
/quests             - Check active quests
/look               - Examine current location in detail
/map                - See visited locations
/status             - Check character HP and stats
/save               - Manually save game
/help               - Show command help
/quit               - Exit game (prompts to save)
```

### Gameplay Tips

- **Use natural language**: The AI understands context and nuance
- **Be creative**: The world responds to unexpected actions
- **Explore thoroughly**: Find hidden details with `/look`
- **Track quests**: Check `/quests` to see active objectives
- **Manage inventory**: Items have weight limits

### Custom Worlds

To create a world with custom lore:

1. Write or gather lore documents (txt, md, or pdf)
2. During setup, choose "Upload lore" and point to the directory
3. RAG will ingest all files and make the lore queryable
4. The narrator will consistently reference your world

Example lore format:

```markdown
# The Kingdom of Aethoria

## Geography
- Aethoria is a crescent-shaped kingdom...
- The capital, Silvermere, lies on the coast...

## History
- Founded 500 years ago by the First King...
- Recently invaded by the Shadow Court...

## NPCs
- Queen Lydia: Wise ruler, skilled diplomat
- The Raven: Mysterious spymaster with unknown loyalties
```

## Configuration Details

Config saved to `~/.config/rag-quest/config.json`:

```json
{
  "llm": {
    "provider": "openrouter",
    "model": "anthropic/claude-sonnet-4",
    "api_key": "sk-or-..."
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

## Game State & Saves

Game state is saved to `~/.local/share/rag-quest/saves/{world_name}.json`.

The RAG database is stored at `~/.local/share/rag-quest/worlds/{world_name}/`.

Both are preserved when you load a save, ensuring world consistency.

## Troubleshooting

### "Connection refused" errors
- For OpenAI: Check your API key
- For OpenRouter: Verify API key and internet connection
- For Ollama: Make sure Ollama is running (`ollama serve`)

### RAG queries returning irrelevant results
- The hybrid mode balances entity and theme matching
- More detailed lore ingestion helps
- Restarting the game resets the RAG context

### Game not responding
- Check your LLM provider's API status
- For Ollama, ensure it's not overloaded
- Try a shorter response with `/help` to test

## Development

### Project Structure

```
rag-quest/
├── rag_quest/
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   ├── config.py            # Configuration
│   ├── llm/                 # LLM providers
│   ├── knowledge/           # RAG integration
│   ├── engine/              # Game logic
│   └── prompts/             # System prompts
├── lore/                    # Default lore directory
├── saves/                   # Save game files
├── pyproject.toml
├── .gitignore
└── README.md
```

### Running with Debug Info

```bash
python -m rag_quest --debug
```

### Testing

```bash
# Run pytest
pytest

# Run with coverage
pytest --cov=rag_quest
```

## Future Roadmap (v0.2+)

- [ ] World generation from prompts using LLM
- [ ] Combat system with dice rolls
- [ ] Dynamic quest generation
- [ ] Multi-player support via Tailscale
- [ ] Web UI alongside terminal
- [ ] Voice I/O for narration
- [ ] Character-specific abilities and spells
- [ ] Persistent NPC relationships and memory
- [ ] Procedural dungeon generation

## Limitations

- v0.1 is single-player only
- World generation from prompts requires manual setup
- No combat system yet (purely narrative)
- NPC interactions are reactive, not proactive
- Limited to text-based input

## Performance Notes

- First startup will initialize LightRAG (30-60 seconds)
- Subsequent queries are cached (typically <3 seconds)
- Larger lore files take longer to ingest
- RAG queries get faster as the knowledge graph grows

## License

MIT License - See LICENSE file for details

## Credits

- **LightRAG**: HKU's knowledge graph system
- **Rich**: Beautiful terminal UI
- **httpx**: Modern async HTTP client
- **PyMuPDF**: PDF text extraction

## Support

For issues, questions, or ideas:
- Check the troubleshooting section above
- Review example lore in `/lore`
- Try the `/help` command in-game
- Adjust provider settings in `~/.config/rag-quest/config.json`

---

**Ready to adventure?** Run `python -m rag_quest` and may your stories be legendary!
