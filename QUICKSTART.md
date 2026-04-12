# RAG-Quest Quick Start Guide

Welcome! This guide takes you from zero to adventuring in about 5 minutes. **No command-line experience needed.**

## What You'll Need

1. A Mac, Linux, or Windows computer
2. About 30 minutes for the first time (mostly downloading)
3. Internet connection (for downloading; gameplay is offline)

That's it! No coding skills required.

## Step 1: Install Ollama (The Free AI Brain)

Ollama is the AI engine that runs locally on your computer. It's your dungeon master.

### Mac Users:
1. Go to **https://ollama.ai**
2. Click **Download** and choose **Mac**
3. Wait for download to complete
4. Open the `.dmg` file and drag Ollama to Applications
5. Open Applications and double-click Ollama
6. You should see the Ollama icon in your menu bar (top right) — you're done!

### Linux Users:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve &
```

### Windows Users:
1. Go to **https://ollama.ai**
2. Click **Download** and choose **Windows**
3. Run the installer and follow prompts
4. Open Ollama from your Start menu
5. Done!

## Step 2: Download the AI Narrator Model

This step downloads the language model that will be your narrator. It's about 5-6GB.

Open **Terminal** (Mac/Linux) or **Command Prompt** (Windows) and paste this:

```bash
ollama pull gemma4:e4b
```

Wait for it to finish. You'll see a progress bar showing the download. This takes 5-10 minutes depending on your internet speed. Grab a coffee!

**Note**: If you have a very slow connection or old computer, use the smaller model instead:
```bash
ollama pull gemma4:e2b
```

## Step 3: Install RAG-Quest

Choose the option that matches your system:

### Option A: Homebrew (Mac) — Easiest
```bash
brew install mattwag05/tap/rag-quest
rag-quest
```

### Option B: pip (Mac/Linux/Windows) — Universal
```bash
pip install git+https://github.com/mattwag05/rag-quest.git
python -m rag_quest
```

### Option C: From Source (Mac/Linux/Windows) — For Developers
```bash
git clone https://github.com/mattwag05/rag-quest.git
cd rag-quest
pip install -e .
python -m rag_quest
```

## Step 4: Welcome Screen

When you run RAG-Quest for the first time, you'll see:

1. **Welcome Banner** — ASCII art and version info
2. **Three Start Modes** — Pick one:
   - **Fresh Adventure** — Blank world, create your character
   - **Quick Start** — Choose from 4 templates (dungeons, forests, cities)
   - **Upload Lore** — Bring your own world description (optional, advanced)

3. **Character Creation**:
   - Choose your race (Human, Elf, Dwarf, Orc, Halfling)
   - Choose your class (Fighter, Rogue, Mage, Cleric, Ranger)
   - Enter your character name
   - Confirm your selections

4. **Game Configuration**:
   - LLM Provider — Ollama is recommended and auto-detected
   - RAG Profile — "balanced" is recommended for most systems
   - World Settings — Name your world, set the tone (fantasy, horror, sci-fi, etc.)

5. **Adventure Begins!** — You're in the game!

## Step 5: Playing the Game

You're now in the game! The AI describes a scene, and you type what you want to do:

```
You stand at the entrance of a dark forest. Twisted trees loom overhead.
What do you do?

> Walk into the forest and look for signs of life
```

That's it! Just type natural language and press Enter. The AI understands:
- Actions: "swing my sword," "cast a spell," "run away"
- Dialogue: "ask the NPC about the quest," "demand the treasure"
- Exploration: "search the room," "climb the wall," "knock on the door"

### New to the Game? Try the Tutorial!

Type `/tutorial` at any time to start a guided 9-step walkthrough that teaches you exploration, NPCs, inventory, combat, commands, quests, saving, and pro tips. It takes about 5 minutes and is the fastest way to learn the game.

### Essential Commands

Type these anytime during the game:

| Command | What it does |
|---------|-------------|
| `/tutorial` | Start the interactive guided tutorial |
| `/i` or `/inventory` | See what you're carrying |
| `/s` or `/stats` | Check your health, level, attributes |
| `/q` or `/quests` | View active quests and objectives |
| `/p` or `/party` | See your companions |
| `/tutorial` | Interactive 9-step guided tutorial |
| `/h` or `/help` | Full command reference |
| `/config` | Change LLM or settings |
| `/save` | Save your game manually |
| `/new` | Start a new game |
| `/exit` | Quit (you'll be asked to save) |

### Game Concepts

**Combat**: Encounter an enemy? You'll enter combat automatically. Dice rolls, attacks, damage — all handled for you. Just type your action (attack, cast spell, defend, flee).

**Quests**: NPCs offer quests with objectives. Complete them for experience and loot.

**Leveling Up**: Gain experience from combat and quests. Level up to unlock new abilities and increase your stats.

**Inventory**: Pick up items and equipment. Your gear affects your stats and combat abilities.

**Multiplayer**: Start a local game and pass the controller between players on the same machine.

## Troubleshooting

### "Ollama isn't running"
- **Mac**: Look for the Ollama icon in your menu bar (top right)
- **Linux**: Run `ollama serve &` in Terminal
- **Windows**: Open Ollama from your Start menu
- If it's not there, download from https://ollama.ai again

### "Model not found" error
Run this command again:
```bash
ollama pull gemma4:e4b
```

If you're on a slow connection or old computer:
```bash
ollama pull gemma4:e2b
```

### "Connection refused" when starting RAG-Quest
Ollama crashed or wasn't running when you started the game. Restart Ollama and try again.

### Slow responses during gameplay
The game is CPU/GPU bound. Slow hardware + large models = slow responses. Try:
1. Use the smaller model: `ollama pull gemma4:e2b`
2. Use the "fast" RAG profile: `/config` → choose "fast"
3. Close other apps to free up memory

### Narrative quality is poor
RAG-Quest needs knowledge about your world to work well. During setup, choose "Upload Lore" and provide a description of your world. The more context you give, the better the storytelling.

## Next Steps

- Read the full command list: `/help` (in-game)
- Explore the world: Travel, meet NPCs, find quests
- Level up your character: Gain XP through combat and quests
- Try multiplayer: Invite a friend for hot-seat gameplay
- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand how RAG-Quest works

## Getting Help

- **In-game help**: Type `/help`
- **Full documentation**: See [CLAUDE.md](CLAUDE.md) (for developers)
- **GitHub issues**: https://github.com/mattwag05/rag-quest/issues
- **Troubleshooting**: See section above

## Need More Help?

Download the full **RAG-Quest User Guide** (Word document) from the `docs/` folder in the repository. It covers everything in 8 detailed chapters.

## Next Releases

- **v0.6**: Web UI, cloud deployment
- **v0.7**: iOS app, offline packages
- **v0.8**: Voice I/O, Apple Intelligence

---

Have fun! Your adventure awaits.
