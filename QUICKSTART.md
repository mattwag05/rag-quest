# RAG-Quest Quick Start Guide

Get your RPG adventure running in 5 minutes.

## Prerequisites

- Python 3.11 or higher
- pip package manager
- An LLM API key (OpenAI, OpenRouter) OR a local Ollama instance

## Installation (2 minutes)

### Step 1: Clone the repository

```bash
cd ~/Desktop/Projects
git clone https://github.com/yourusername/rag-quest.git
cd rag-quest
```

### Step 2: Install dependencies

```bash
# Option A: Using pip with requirements.txt
pip install -r requirements.txt

# Option B: Using pip install with pyproject.toml (recommended)
pip install -e .

# Option C: Manual installation
pip install lightrag-hku httpx rich pymupdf
```

### Step 3: Verify installation

```bash
python -c "import rag_quest; print('RAG-Quest installed successfully!')"
```

## Setup (2 minutes)

### Start the game

```bash
python -m rag_quest
```

On first run, you'll be guided through setup:

```
RAG-Quest - First Run Setup

LLM Provider Setup
Select LLM provider: (openai/openrouter/ollama) [openrouter]
> openrouter
Model (e.g., anthropic/claude-sonnet-4) [anthropic/claude-sonnet-4]
> anthropic/claude-sonnet-4
OpenRouter API key
> sk-or-xxx...

How would you like to set up your world?
1. Fresh start with prompt
2. Manual configuration
3. Upload lore
> 2

World name [Untitled Realm]
> The Shattered Realms

World setting [Medieval Fantasy]
> Dark Medieval Fantasy

World tone (Dark, Heroic, Whimsical, etc.) [Dark]
> Dark

Starting location [A small tavern]
> The Crooked Raven Tavern

Character Creation
Character name
> Aerion

Race (0: Human, 1: Elf, 2: Dwarf, 3: Halfling, 4: Orc)
> 0

Class (0: Fighter, 1: Mage, 2: Rogue, 3: Ranger, 4: Cleric)
> 3

Character background (optional)
> A wanderer from distant lands

Configuration saved!
```

## Play! (1 minute)

You're now in the game. Try these commands:

### Basic Commands

```
> I look around carefully
> I sit at the bar and order a drink
> I talk to the bartender about recent news
> /help
```

### Essential Commands

```
/inventory              - Check your items
/quests                 - View active quests
/look                   - Examine current location
/map                    - See visited locations
/status                 - Character info
/save                   - Save game
/quit                   - Exit (with save prompt)
```

## LLM Provider Setup

### OpenRouter (Easiest)

1. Sign up at https://openrouter.ai
2. Get your API key from account settings
3. During setup, select "openrouter"
4. Paste your API key when prompted

**Recommended models:**
- `anthropic/claude-sonnet-4` (best quality)
- `anthropic/claude-opus-4` (faster)
- `gpt-4o` (from OpenAI via OpenRouter)

### OpenAI (Direct)

1. Sign up at https://openai.com
2. Get your API key from https://platform.openai.com/api-keys
3. During setup, select "openai"
4. Paste your API key when prompted

**Recommended models:**
- `gpt-4o` (best overall)
- `gpt-4-turbo` (faster)
- `gpt-3.5-turbo` (cheapest)

### Ollama (Local - Free!)

1. Install Ollama: https://ollama.ai
2. Start Ollama server: `ollama serve`
3. Pull a recommended model:
   - `ollama pull gemma4:latest` (2B-4B, fastest)
   - `ollama pull mistral` (7B, excellent quality)
   - `ollama pull llama2` (7B, good alternative)
4. During setup, select "ollama"
5. Use default URL: `http://localhost:11434`
6. Use model name: `gemma4:latest` (or your chosen model)

## Example First Actions

```
> I look around the tavern and observe the patrons
> I approach the bar and order a drink
> I ask the bartender if she knows of any interesting work
> I notice someone watching me from the corner
> /quests
> I walk over to speak with the mysterious figure
```

## Troubleshooting

### Error: "Connection refused"

**OpenRouter/OpenAI**: Check your internet connection and API key
```bash
# Test your API key (OpenRouter example)
curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer sk-or-..." \
  -H "Content-Type: application/json" \
  -d '{"model": "anthropic/claude-sonnet-4", "messages": [{"role": "user", "content": "test"}]}'
```

**Ollama**: Make sure Ollama is running
```bash
ollama serve
# In another terminal:
ollama pull llama3.1
```

### Error: "No such command"

Make sure you're using correct command syntax:
```
/help              # Shows all commands
/inventory         # Check inventory
/look              # Examine location
```

### Model Taking Too Long

Some models are slower. Try:
1. Use OpenRouter's faster models
2. Switch to a smaller local model
3. Check your internet connection
4. Ensure your LLM provider isn't overloaded

## Customization

### Custom Worlds

Create a world with your own lore:

1. Write lore files in Markdown or plain text
2. Save them to `./lore/` directory
3. During setup, choose "Upload lore"
4. Point to your lore directory

Example lore file (`./lore/kingdoms.md`):

```markdown
# The Kingdom of Aethoria

Aethoria is a prosperous kingdom known for...

## Cities
- Silvermere: The capital, on the coast
- Ashford: A trading hub in the mountains

## Rulers
- King Aldric: Strong military leader
- Queen Lydia: Wise diplomat
```

### Configuration File

Edit `~/.config/rag-quest/config.json` to change settings:

```json
{
  "llm": {
    "provider": "openrouter",
    "model": "anthropic/claude-sonnet-4",
    "temperature": 0.85,
    "max_tokens": 1024
  },
  "world": {
    "name": "The Shattered Realms",
    "setting": "Medieval Fantasy",
    "tone": "Dark",
    "starting_location": "The Crooked Raven"
  },
  "character": {
    "name": "Aerion",
    "race": "Human",
    "class": "Ranger",
    "background": "A wanderer"
  }
}
```

## Tips for Great Gameplay

### For the Best Experience

1. **Be descriptive**: "I approach the tavern cautiously and observe the patrons before entering" works better than "I go to tavern"

2. **Role-play**: Think like your character. Ask yourself what they would do.

3. **Explore**: Use `/look` to get detailed descriptions of locations.

4. **Take notes**: Important NPCs, locations, and plot points are tracked in your world.

5. **Use context**: The AI remembers what you've done and said before.

### Avoiding Common Issues

- **Keep it in character**: The narrator expects you to act like your character
- **Be specific**: "I cast a fireball at the enemies" is better than "attack"
- **Manage inventory**: Items have weight limits
- **Check quests**: `/quests` shows active objectives
- **Save often**: Use `/save` to not lose progress

## Next Steps

1. **Play your first game** - Follow the prompts and have fun!
2. **Create custom worlds** - Write lore and use the upload feature
3. **Invite others** - Share your worlds with friends
4. **Join the community** - Share your adventures and lore

## Need Help?

- **In-game**: Type `/help` to see all commands
- **Configuration**: Edit `~/.config/rag-quest/config.json`
- **Documentation**: Read README.md for detailed guides
- **Contributing**: See CONTRIBUTING.md to help improve RAG-Quest

## Common Questions

**Q: Do I need internet for Ollama?**
A: No! Ollama runs locally and doesn't need internet once the model is downloaded.

**Q: How much do API calls cost?**
A: OpenRouter and OpenAI charge per token. Budget ~$0.01-0.05 per action. Ollama is free.

**Q: Can I switch providers later?**
A: Yes! Edit `~/.config/rag-quest/config.json` and restart.

**Q: Where are my saves stored?**
A: `~/.local/share/rag-quest/saves/`

**Q: How do I reset my configuration?**
A: Delete `~/.config/rag-quest/config.json` and restart the game.

---

**Ready for adventure? Run `python -m rag_quest` and begin your legend!**
