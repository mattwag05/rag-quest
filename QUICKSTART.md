# RAG-Quest Quick Start Guide

Welcome! This guide takes you from zero to adventuring in about 5 minutes. **No command-line experience needed.**

## What You'll Need

1. A Mac or Linux computer
2. About 30 minutes for the first time (mostly downloading)
3. Internet connection (for downloading, play is offline)

That's it! No coding skills required.

## Step 1: Install Ollama (Free AI Brain)

Ollama is the AI that runs locally on your computer. Think of it as the dungeon master.

1. Go to **https://ollama.ai**
2. Click **Download** and choose your operating system (Mac/Linux/Windows)
3. Install it like any other program (click the installer, drag to Applications, etc.)
4. Open Ollama from your Applications folder
5. Let it finish installing (you'll see a progress bar)

**You're done!** Ollama is now running in the background.

## Step 2: Download the Ollama Model (The Narrator)

Open your **Terminal** (Mac) or **Command Prompt** (Windows/Linux) and paste this:

```bash
ollama pull gemma4:e4b
```

This downloads the AI model that will be your narrator. It's about 5-6GB, so grab a coffee—this takes 5-10 minutes depending on your internet speed.

**If you have a very slow connection or old computer**, use the smaller model instead:
```bash
ollama pull gemma4:e2b
```

## Step 3: Install RAG-Quest

Choose one of these options:

### Option A: Homebrew (Mac) — Easiest
```bash
brew install mattwag05/tap/rag-quest
```

### Option B: pip (Mac/Linux/Windows)
```bash
pip3 install rag-quest
```

### Option C: From Source (Most Control)
```bash
git clone https://github.com/mattwag05/rag-quest.git
cd rag-quest
pip3 install -e .
```

## Step 4: Play!

Open Terminal and type:
```bash
rag-quest
```

Press Enter and watch the magic happen. You'll see a friendly welcome screen, then a **Setup Wizard** that guides you through the rest.

### The Setup Wizard (Don't Worry, It's Simple!)

When you run `rag-quest`, you'll be asked to pick a start mode:

**🌟 Fresh Adventure** (Recommended for first time)
- Start with a brand new world
- Name your character and world
- Pick a race (Human, Elf, Dwarf, etc.) and class (Warrior, Mage, Rogue, etc.)
- The narrator creates the adventure for you

**⚡ Quick Start** (Fastest way to play)
- Choose a pre-built world (Classic Dungeon, Enchanted Forest, etc.)
- Customize your character
- Start playing immediately

**📚 Custom Lore** (For world builders)
- Upload your own PDF, Word document, or text file
- The game learns from your world
- More advanced, skip for now

Pick "Fresh Adventure" if you're not sure. The wizard will ask you a few simple questions, then you'll be ready to play!

## Step 5: Start Playing!

Once you're in the game, just type what you want to do:

```
You are standing in a dark forest.

What do you do? > Go north
```

The AI narrator will tell you what happens next. Combat, treasure, NPCs—it all unfolds as you play.

### Useful Commands

Once you're playing, try these:

- `/help` — Shows all commands and tips
- `/save` — Save your game manually
- `/load` — Load a previous save
- `/inventory` — See what you're carrying
- `/status` — Check your health and abilities
- `/party` — See your party members
- `/quests` — See active quests
- `/achievements` — See badges you've unlocked
- `/settings` — Change game settings

Type `/help` during the game to see everything.

## Troubleshooting

### "Command not found: rag-quest"
Make sure the installation finished. Try:
```bash
pip3 install rag-quest --force-reinstall
```

### "Cannot connect to Ollama"
Ollama needs to be running. Open Ollama from your Applications folder and make sure the icon is in the menu bar at the top of your screen.

### "Model download failed"
Your internet might have hiccupped. Try the pull command again:
```bash
ollama pull gemma4:e4b
```

### "Game is running very slowly"
You might be using the model that's too heavy for your computer. Try the smaller model:
```bash
ollama pull gemma4:e2b
rag-quest  # Game will automatically use the smaller model
```

### Still stuck?
Open an issue on GitHub: **https://github.com/mattwag05/rag-quest/issues**

Include what you tried and the error message you got. We'll help!

## Tips for a Great First Adventure

1. **Be creative** — The game responds to anything you type. Describe what you want to do in detail.
2. **Save often** — Use `/save` to create checkpoints. You can load them later.
3. **Try new things** — Talking to NPCs, exploring, trying weird combinations—the game handles it all.
4. **Don't worry about "right answers"** — There's no one way to play. Your story is unique.
5. **Check your stats** — Type `/status` to see your health, abilities, and inventory.

## Next Steps

Once you're comfortable playing:

- **Upload custom lore** — Next game, try Mode 3 to make the world truly yours
- **Try multiplayer** — Play with friends in hot-seat mode (everyone takes turns on same computer)
- **Export your world** — Share your world with others via `.rqworld` files
- **Read the full docs** — GitHub README has advanced features and command reference

## Still Have Questions?

- **README.md** — Feature overview and detailed documentation
- **`/help` command** — In-game help for all commands
- **GitHub Issues** — Report bugs or request features

---

**Welcome to RAG-Quest, adventurer.** Your legend awaits!
