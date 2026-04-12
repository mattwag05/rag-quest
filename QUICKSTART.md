# RAG-Quest Quick Start Guide

Get from zero to playing in 5 minutes.

## 1. Install

### Option A: Homebrew (Recommended)
```bash
brew install mattwag05/tap/rag-quest
rag-quest
```

### Option B: pip
```bash
pip install rag-quest
rag-quest
```

### Option C: From Source
```bash
git clone https://github.com/mattwag05/rag-quest.git
cd rag-quest
pip install -e .
rag-quest
```

## 2. Set Up Ollama (For Local Play)

If you want to play for free, locally, and privately:

```bash
# Download Ollama from ollama.ai, then:
ollama pull gemma4:e4b   # 4B, best quality (needs GPU)
# OR
ollama pull gemma4:e2b   # 2B, fast on CPU
```

Keep the Ollama server running in a terminal:
```bash
ollama serve
```

## 3. Start a Game

```bash
rag-quest
```

You'll see an interactive setup menu:

```
RAG-Quest: New Game Setup

LLM Provider? [openai/openrouter/ollama]
  > ollama

Ollama Model? [gemma4:e4b]
  > gemma4:e4b

RAG Profile (speed vs fidelity)? [fast/balanced/deep]
  > balanced

World Name?
  > The Shattered Citadel

World Setting?
  > Post-apocalyptic ruins

World Tone?
  > Dark and mysterious

Character Name?
  > Kael

Character Race? [HUMAN/ELF/DWARF/HALFLING/ORC]
  > HUMAN

Character Class? [FIGHTER/MAGE/ROGUE/RANGER/CLERIC]
  > RANGER

Upload custom lore? (txt/md/pdf, space-separated)
  > lore/shattered_citadel.pdf
  
Ingesting lore...
████████████████████ 100%

Creating game...
Done! Ready to play.
```

## 4. Play

```
═══════════════════════════════════════════════════════════════════════════════
  THE SHATTERED CITADEL — Post-Apocalyptic Ruins
═══════════════════════════════════════════════════════════════════════════════

📍 LOCATION: Rusted Plaza
Broken towers loom overhead, their facades crumbling. The smell of rust and
decay fills the air. You notice a path leading east to the collapsed library...

💚 KAEL | HP: 30/30 | Level 1 | Ranger
📦 Inventory: Worn Backpack (5/20)
⚔️  Active Quests: None

> I cautiously move north toward the makeshift shelter

You carefully approach the shelter, hand on your knife. As you draw near,
smoke curls from an opening. A figure emerges—a grizzled woman with a rifle...

> I raise my hands peacefully

"Easy, friend," she says, lowering her weapon. "Name's Vera. Most folks
'round here ain't friendly. You look like you got a story..."

> Ask about the safehouse

"The safehouse? That's a legend..." she says. "But three weeks back, I found
a map showing a route to the old military bunker below the citadel..."

✨ NEW QUEST: Vera's Map — Find the Military Bunker

> /quests

Active Quests:
  • Vera's Map (ACTIVE) — Find the Military Bunker

> /inventory

Inventory (5/20 lbs):
  • Worn Backpack
  • Water Canteen
  • Rope
  • Knife
  
> /status

═══════════════════════════════════════════════════════════════════════════════
  KAEL — Ranger (Level 1)
═══════════════════════════════════════════════════════════════════════════════
  HP: 30/30 ████████████████████████████████ 100%
  Location: Rusted Plaza
  Experience: 0/100
  
Inventory: 5/20 lbs
Quests Active: 1

> I take Vera's map and thank her

You carefully take the worn map from Vera's hands...

> /save

Game saved.
```

## In-Game Commands

Type naturally or use commands:

| Action | Example |
|--------|---------|
| **Natural Language** | `I search the desk for clues` |
| **Movement** | `I go north to the library` |
| **Combat** | `I attack the goblin with my sword` |
| **Dialogue** | `Ask Vera about the bunker` |
| **Inventory** | `/i` or `/inventory` |
| **Quests** | `/q` or `/quests` — see quest chains and choices |
| **Status** | `/s` or `/status` |
| **Party** | `/party` — view party roster and morale |
| **Recruit** | `/recruit <NPC name>` — add companion to party |
| **Dismiss** | `/dismiss <companion name>` — remove from party |
| **Relationships** | `/relationships` — view trust and disposition with NPCs |
| **Factions** | `/factions` — see faction reputation and standing |
| **Events** | `/events` — view active world events and consequences |
| **Look** | `/look` or `/examine` |
| **Map** | `/map` to see discovered locations |
| **Save** | `/save` to save progress |
| **Help** | `/help` for full command reference |
| **Quit** | `/quit` to exit (prompts to save) |

## Configuration (Advanced)

Skip interactive setup with environment variables:

```bash
# LLM Setup
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=gemma4:e4b
export OLLAMA_BASE_URL=http://localhost:11434

# World Setup
export WORLD_NAME="The Shattered Citadel"
export WORLD_SETTING="Post-apocalyptic"
export WORLD_TONE="Dark"

# Character Setup
export CHARACTER_NAME="Kael"
export CHARACTER_RACE=HUMAN
export CHARACTER_CLASS=RANGER

# RAG Profile (optional)
export RAG_PROFILE=balanced  # fast, balanced, or deep

# Then start
rag-quest
```

## LLM Provider Comparison

### Ollama (Recommended for First Play)
- **Cost**: Free
- **Speed**: 2-20 seconds per response
- **Quality**: Excellent with RAG
- **Setup**: Download ollama.ai, run `ollama serve`
- **Models**: `gemma4:e4b` (GPU) or `gemma4:e2b` (CPU)
- **Privacy**: Everything local, no data sent anywhere

### OpenAI (Highest Quality)
- **Cost**: ~$0.05-0.30 per turn
- **Speed**: 3-10 seconds
- **Quality**: Excellent
- **Setup**: Get API key from openai.com
- **Models**: GPT-4, GPT-4 Turbo, GPT-3.5-turbo

### OpenRouter (Flexibility, Great Value)
- **Cost**: ~$0.005-0.15 per turn
- **Speed**: 1-5 seconds
- **Quality**: Good to excellent (depends on model)
- **Setup**: Get API key from openrouter.ai
- **Models**: 100+ options (Claude, Llama, Mistral, etc.)

## Gameplay Tips

### Combat
- Describe your action vividly: "I dodge left and counterattack with a thrust"
- Combat is turn-based; the narrator responds to each action
- Monitor your HP with `/status`

### Dialogue
- Talk to NPCs to discover quests and lore
- Try asking about things: "Ask the innkeeper about rumors"
- NPCs remember previous conversations

### Exploration
- Visit new locations to find items and meet NPCs
- Use `/map` to see where you've been
- Every location has secrets to discover

### Inventory Management
- Keep an eye on weight (`/inventory`)
- Find useful items during exploration
- Use items in actions: "Use the rope to climb down"

### Saving
- Auto-save happens every 3 turns
- Use `/save` before dangerous actions
- Saves are stored in `~/.local/share/rag-quest/saves/`

## Troubleshooting

### "No response from LLM"
1. **Ollama**: Make sure `ollama serve` is running in another terminal
2. **Check connectivity**: `curl http://localhost:11434/api/tags`
3. **OpenAI/OpenRouter**: Verify API key is set and valid

### Game runs slow
1. **Ollama on CPU**: Try `gemma4:e2b` instead of E4B
2. **GPU users**: Increase VRAM allocated to Ollama
3. **OpenAI/OpenRouter**: These are cloud-hosted and should be fast

### Config errors
1. Set environment variables: `echo $LLM_PROVIDER`
2. Check `~/.config/rag-quest/config.json` exists
3. Try interactive setup again (delete config and re-run `rag-quest`)

### Class not recognized
Valid classes: FIGHTER, MAGE, ROGUE, RANGER, CLERIC (case-sensitive)

## What's New in v0.2.0

- ✅ Full game loop with character location, combat, inventory, quests
- ✅ 50-turn playtest verified all systems working
- ✅ Three RAG profiles (fast/balanced/deep) for speed vs quality
- ✅ PDF lore ingestion with intelligent chunking
- ✅ Auto-save every turn with error recovery
- ✅ Works with Ollama, OpenAI, and OpenRouter

## What's New in v0.3.0

- ✅ D&D combat with dice rolls, initiative, and critical hits
- ✅ Character progression with 6 attributes and leveling to 10
- ✅ Equipment system with weapon, armor, and accessory slots
- ✅ Dynamic encounter generation with loot and difficulty scaling
- ✅ Text-to-speech narrator (pyttsx3 and gTTS support)
- ✅ Real LLM narrator with context injection

## What's New in v0.4.0

- ✅ Multi-character parties (recruit NPCs, up to 4 members)
- ✅ NPC relationship system (trust, disposition, faction reputation)
- ✅ Quest chains with branching paths and player choices
- ✅ Dynamic world events affecting gameplay (10+ event types)
- ✅ Companion AI with personality and loyalty system
- ✅ Relationship-gated dialogue and quests

## What's Coming in v0.5

- Multiplayer support with shared worlds
- Cloud save synchronization
- Community world sharing and templates
- Procedural dungeon generation

## Have Fun!

RAG-Quest is designed for creative, emergent storytelling. Your choices matter. Every playthrough is unique. Enjoy your adventure!

---

**Version**: v0.2.0 MVP  
**Status**: Ready for Game Night!  
**License**: MIT
