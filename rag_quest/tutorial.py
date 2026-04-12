"""Interactive TUI tutorial for new RAG-Quest players."""

from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def print_tutorial_welcome() -> None:
    """Print welcome screen for tutorial."""
    console.clear()
    title = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                  WELCOME TO RAG-QUEST!                    ║
    ║          Interactive Tutorial (5 minutes)                  ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(title, style="cyan")

    intro = """
This tutorial will teach you everything you need to know to start your 
adventure in RAG-Quest, an AI-powered D&D-style text RPG.

You'll learn about exploration, combat, inventory, NPCs, and more!

Ready? Press Enter to continue...
    """
    console.print(Panel(intro, border_style="cyan", expand=False))
    input()


def step_1_basic_movement() -> None:
    """Teach basic movement and exploration."""
    console.clear()

    title = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                  STEP 1: EXPLORATION                      ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(title, style="cyan")

    content = """
The core of RAG-Quest is simple: **describe what you want to do**.

Just type your action in plain English. The AI Dungeon Master will 
respond and the world will react to your choices.

[bold cyan]Example Scenario:[/bold cyan]
You're standing in a worn-out tavern. The air smells of ale and smoke.
Patrons huddle around wooden tables. A bard strums a lute in the corner.

[bold cyan]What you might type:[/bold cyan]
  > look around
  > examine the bar
  > talk to the bartender
  > go to the marketplace
  > climb the stairs

Try typing actions that are specific and descriptive. The more detail
you provide, the better the AI can respond!

[bold yellow]Pro tip:[/bold yellow] "I carefully examine the ancient chest" 
works much better than just "look".
    """
    console.print(Panel(content, border_style="cyan", expand=False))
    input("\nPress Enter to continue...\n")


def step_2_talking_to_npcs() -> None:
    """Teach NPC interaction."""
    console.clear()

    title = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                  STEP 2: MEETING NPCs                     ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(title, style="cyan")

    content = """
NPCs (Non-Player Characters) are people in the world. Some give quests,
some trade items, some become allies.

[bold cyan]Talking to NPCs:[/bold cyan]
The world is full of interesting characters. Here are some actions:

  > talk to the merchant
  > ask the guard about bandits
  > greet the mysterious stranger
  > try to convince the innkeeper to tell me a story

[bold cyan]Example NPC Interaction:[/bold cyan]

[bold cyan]You:[/bold cyan] > talk to the blacksmith

[bold blue]Dungeon Master:[/bold blue]
A burly man with singed arms looks up from his forge. "Aye, 
what brings ye to me smithy?" he asks, eyes narrowing. "Need 
a new blade? I've got steel that's seen many battles."

[bold yellow]Remember:[/bold yellow]
  • NPCs have personalities and remember you
  • Some will become allies if you treat them well
  • Dialogue is how you learn about quests and lore
  • Your choices affect how NPCs react to you
    """
    console.print(Panel(content, border_style="cyan", expand=False))
    input("\nPress Enter to continue...\n")


def step_3_inventory() -> None:
    """Teach inventory and item management."""
    console.clear()

    title = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                 STEP 3: MANAGING ITEMS                    ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(title, style="cyan")

    content = """
As you explore, you'll find items: weapons, armor, potions, treasure.
You can carry a limited amount, so manage your inventory wisely.

[bold cyan]Picking Up Items:[/bold cyan]

When you see an item (the AI will tell you):
  > pick up the sword
  > take the health potion
  > grab the golden amulet

[bold cyan]Checking Inventory:[/bold cyan]

During the game, type:
  /i    or    /inventory

This shows everything you're carrying, including weight/capacity.

[bold cyan]Example:[/bold cyan]
[bold]Inventory (4/10 items):[/bold]
  • Rusty Sword (weapon)
  • Leather Armor (armor)
  • Health Potion x2 (healing)
  • Gold Coins x50 (currency)

[bold yellow]Tips:[/bold yellow]
  • Items take up space — you can only carry so much
  • Sell items you don't need to free up space
  • Equip weapons and armor to improve your stats
  • Use potions to heal during combat
    """
    console.print(Panel(content, border_style="cyan", expand=False))
    input("\nPress Enter to continue...\n")


def step_4_combat() -> None:
    """Teach combat system."""
    console.clear()

    title = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                    STEP 4: COMBAT                         ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(title, style="cyan")

    content = """
Sometimes you'll encounter enemies. Combat is automatic but you can 
describe your tactics to influence the outcome.

[bold cyan]Example Combat Scenario:[/bold cyan]

[bold blue]Dungeon Master:[/bold blue]
A goblin emerges from the shadows, weapon raised! Combat begins!

[bold cyan]What you might do:[/bold cyan]
  > dodge left and strike at its leg
  > cast a fireball spell
  > block with my shield and counterattack
  > try to disarm it

[bold cyan]Example Combat Result:[/bold cyan]

[red]⚔ COMBAT! ⚔[/red]

You face a Goblin Warrior (HP: 15)
Your HP: 20/20

[bold cyan]You attack![/bold cyan]
Dice roll: 15 + 3 (STR bonus) = 18 vs AC 12 [bold green]HIT![/bold green]
Damage: 6 + 2 (weapon bonus) = 8 damage!

[red]Goblin HP:[/red] 15 → 7

[red]Goblin counter-attacks![/red]
Dice roll: 8 vs AC 14 [bold red]MISS![/bold red]

[bold green]Victory![/bold green] You defeated the goblin!
+50 XP gained
Found: Goblin Dagger, 25 Gold Coins

[bold yellow]Combat Tips:[/bold yellow]
  • Be tactical — describe your combat moves
  • Watch your HP — heal when needed
  • Defeated enemies drop loot (items and gold)
  • Victory grants experience and levels
  • Each level increases your abilities
    """
    console.print(Panel(content, border_style="cyan", expand=False))
    input("\nPress Enter to continue...\n")


def step_5_commands() -> None:
    """Teach in-game commands."""
    console.clear()

    title = """
    ╔═══════════════════════════════════════════════════════════╗
    ║              STEP 5: USEFUL COMMANDS                      ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(title, style="cyan")

    # Create command table
    table = Table(
        title="Essential Commands", show_header=True, header_style="bold cyan"
    )
    table.add_column("Command", style="yellow")
    table.add_column("Shortcut", style="green")
    table.add_column("What It Does", style="white")

    table.add_row("/inventory", "/i", "Check items you're carrying")
    table.add_row("/stats", "/s", "View your character stats")
    table.add_row("/quests", "/q", "See active quests")
    table.add_row("/party", "/p", "View your party members")
    table.add_row("/relationships", "/rel", "See NPC trust levels")
    table.add_row("/help", "/h", "Show full help menu")
    table.add_row("/save", "", "Manually save your game")
    table.add_row("/new", "", "Start a new adventure")
    table.add_row("/quit", "", "Exit the game")

    console.print(table)

    content = """
[bold cyan]Types of Commands:[/bold cyan]

[bold yellow]Exploration:[/bold yellow]
  /look — Examine your surroundings
  /map — See locations you've discovered

[bold yellow]Character:[/bold yellow]
  /stats — Your attributes and health
  /abilities — Unlocked powers and spells
  /equipment — What you're wearing

[bold yellow]Social:[/bold yellow]
  /relationships — How NPCs feel about you
  /party — Your companions
  /recruit NAME — Ask an NPC to join you

[bold yellow]Advanced:[/bold yellow]
  /dungeon — Enter a procedural dungeon
  /achievements — View unlocked achievements
  /config — Change settings
  /voice — Toggle text-to-speech

[bold green]Remember:[/bold green] You don't need to use commands for 
normal actions. Just type what you want to do!

Commands are for checking status and accessing special features.
    """
    console.print(Panel(content, border_style="cyan", expand=False))
    input("\nPress Enter to continue...\n")


def step_6_quests() -> None:
    """Teach quest system."""
    console.clear()

    title = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                   STEP 6: QUESTS                          ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(title, style="cyan")

    content = """
Quests are the backbone of your adventure. They give purpose, reward,
and drive the story forward.

[bold cyan]How Quests Work:[/bold cyan]

1. [bold]Discover:[/bold] Meet an NPC who offers a quest
   > "Will you help me find my lost amulet?"
   
2. [bold]Accept:[/bold] Agree to the quest
   > "I'll find your amulet."
   
3. [bold]Complete:[/bold] Accomplish the objective
   > Explore, gather clues, defeat enemies, find items
   
4. [bold]Reward:[/bold] Get experience and items
   > +100 XP, Mystical Amulet, 50 Gold Coins

[bold cyan]Viewing Quests:[/bold cyan]
Type /q or /quests to see:
  • Quest name and description
  • Current objectives
  • Rewards (XP, items, gold)
  • Progress toward completion

[bold cyan]Example Quest Log:[/bold cyan]

[bold]ACTIVE QUESTS:[/bold]

[bold yellow]►[/bold yellow] Find the Lost Amulet
   Description: Help the merchant locate his family heirloom
   Objectives:
     ☐ Search the old ruins for clues
     ☐ Defeat the shadow creatures
     ☐ Return with the amulet
   Reward: 100 XP, Mystical Amulet, 50 Gold

[bold yellow]►[/bold yellow] Rid the Village of Bandits
   Description: Clear the road of bandits harassing travelers
   Objectives:
     ☑ Scout the bandit camp
     ☐ Gather information about their leader
     ☐ Defeat the bandit captain
   Reward: 150 XP, Bandit's Sword, 100 Gold

[bold yellow]Tips:[/bold yellow]
  • Some quests chain together into longer stories
  • Complete quests for experience and level up
  • Reward items often unlock new story paths
  • Treat quests as suggestions — explore freely!
    """
    console.print(Panel(content, border_style="cyan", expand=False))
    input("\nPress Enter to continue...\n")


def step_7_saving() -> None:
    """Teach save system."""
    console.clear()

    title = """
    ╔═══════════════════════════════════════════════════════════╗
    ║              STEP 7: SAVING YOUR PROGRESS                 ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(title, style="cyan")

    content = """
Your progress is automatically saved frequently. But you can also save
manually anytime you want.

[bold cyan]How Saving Works:[/bold cyan]

[bold yellow]Auto-Save:[/bold yellow]
The game automatically saves your progress every 5 actions. You'll see
a subtle notification: [dim]✓ Progress saved[/dim]

[bold yellow]Manual Save:[/bold yellow]
To save manually, type:
  /save

The game will confirm your save with a message:
  [green]✓ Game saved![/green]

[bold cyan]What Gets Saved:[/bold cyan]
  • Your character (name, level, stats, HP)
  • Your inventory (items and equipment)
  • Your location and the world state
  • All NPCs you've met and their relationships
  • Quest progress
  • Achievements unlocked

[bold cyan]Save Locations:[/bold cyan]
Your saves are stored in:
  ~/.local/share/rag-quest/saves/

Each world has its own save file with all your characters.

[bold yellow]Remember:[/bold yellow]
  • Your progress is constantly saved automatically
  • You can quit anytime and resume later
  • Saves persist between sessions
  • Each world is separate from others
    """
    console.print(Panel(content, border_style="cyan", expand=False))
    input("\nPress Enter to continue...\n")


def step_8_pro_tips() -> None:
    """Teach pro tips and best practices."""
    console.clear()

    title = """
    ╔═══════════════════════════════════════════════════════════╗
    ║              STEP 8: PRO TIPS FOR SUCCESS                 ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(title, style="cyan")

    content = """
Here are pro tips to get the most out of RAG-Quest:

[bold cyan]1. Be Descriptive[/bold cyan]
  Bad:    > search
  Better: > search the bookshelf carefully
  Best:   > search the old oak bookshelf for hidden compartments

The more detail you provide, the better the AI can respond!

[bold cyan]2. Use the World[/bold cyan]
Reference locations, items, and NPCs from earlier in your adventure.
The AI remembers everything you've discovered.

  > go back to the tavern where we met the merchant
  > use the key the blacksmith gave me on the chest
  > talk to the guard again about the shadow creatures

[bold cyan]3. Combat Tactics[/bold cyan]
Describe your combat strategy, not just "attack":

  > dodge left and counterattack
  > cast fireball at the group of goblins
  > block with my shield, then strike at its legs

[bold cyan]4. Dialogue Matters[/bold cyan]
Talk to NPCs to learn about quests, lore, and secrets:

  > ask the innkeeper what she knows about the bandits
  > inquire about rumors in the tavern
  > try to convince the hermit to help us

[bold cyan]5. Manage Your Inventory[/bold cyan]
You can only carry so much. Drop items you don't need:

  > drop the rusted sword
  > sell the broken shield to the blacksmith
  > store items at the inn for later

[bold cyan]6. Explore Everything[/bold cyan]
The world is full of secrets. Don't just follow quest objectives:

  > explore the side paths
  > check out that mysterious tower
  > investigate the strange symbols

[bold cyan]7. Rest and Recover[/bold cyan]
Find safe places to rest and heal. Your health is important!

  > sleep at the inn to restore health
  > meditate at the shrine
  > use a health potion if things get dangerous

[bold cyan]8. Use Your Resources[/bold cyan]
You earn experience, gold, and items. Use them strategically:

  > buy better equipment as you level up
  > collect armor to improve your defense
  > sell loot to fund your adventures

[bold yellow]Most Important:[/bold yellow] 
There's no "correct" way to play. Make choices that feel right to YOU.
The world reacts to your decisions. Have fun and be creative!
    """
    console.print(Panel(content, border_style="cyan", expand=False))
    input("\nPress Enter to continue...\n")


def step_9_campaign_memory() -> None:
    """Teach the v0.6 Campaign Memory commands."""
    console.clear()

    title = """
    ╔═══════════════════════════════════════════════════════════╗
    ║             STEP 9: CAMPAIGN MEMORY                       ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(title, style="cyan")

    content = """
Long campaigns generate a lot of story. RAG-Quest v0.6 adds a
[bold cyan]Campaign Memory[/bold cyan] layer so nothing gets lost.

[bold yellow]Three memory panels:[/bold yellow]

[bold]1. Timeline[/bold]   — every turn produces a short structured entry
  • [cyan]/timeline[/cyan] or [cyan]/t[/cyan] — view the log (filter: combat/quest/npc/item/all)
  • [cyan]/bookmark [note][/cyan] — save the current turn's full prose as a highlight
  • [cyan]/bookmarks[/cyan] — browse saved highlights

[bold]2. Notes[/bold]      — an AI chronicler summarizes recent turns on every save
  • [cyan]/notes[/cyan] or [cyan]/n[/cyan] — show the latest summary
  • [cyan]/notes refresh[/cyan] — force an immediate summary update
  • Stored as local JSON — nothing touches your world lore without permission
  • On paid LLM providers you can disable auto-summary in [cyan]/config[/cyan]

[bold]3. Canonize[/bold]  — player-approved promotion into permanent lore
  • [cyan]/canonize[/cyan] — list pending notes
  • [cyan]/canonize 1[/cyan] or [cyan]/canonize all[/cyan] — promote into LightRAG
  • Once canonized, notes show up in future RAG queries during narration

[bold]4. Lore Encyclopedia[/bold]
  • [cyan]/lore[/cyan] or [cyan]/l[/cyan] — category overview
  • [cyan]/lore npcs[/cyan], [cyan]/lore locations[/cyan], [cyan]/lore factions[/cyan], [cyan]/lore items[/cyan]
  • [cyan]/lore npcs Gandalf[/cyan] — runs a RAG query for rich detail

[bold green]Mental model:[/bold green] JSON notes are yours to keep private. LightRAG only
learns what you explicitly canonize. That hard boundary prevents AI
hallucinations from silently polluting retrieval.
    """
    console.print(Panel(content, border_style="cyan", expand=False))
    input("\nPress Enter to continue...\n")


def step_10_ready() -> None:
    """Final encouragement and send-off."""
    console.clear()

    title = """
    ╔═══════════════════════════════════════════════════════════╗
    ║            YOU'RE READY FOR YOUR ADVENTURE!               ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(title, style="cyan")

    content = """
Congratulations! You've learned the basics of RAG-Quest.

[bold cyan]Quick Recap:[/bold cyan]

[bold yellow]✓[/bold yellow] Type actions to interact with the world
[bold yellow]✓[/bold yellow] Talk to NPCs for quests and lore
[bold yellow]✓[/bold yellow] Collect items and manage inventory
[bold yellow]✓[/bold yellow] Fight enemies and gain experience
[bold yellow]✓[/bold yellow] Use commands to check status (/i, /s, /q, etc.)
[bold yellow]✓[/bold yellow] Complete quests to advance
[bold yellow]✓[/bold yellow] Your progress auto-saves constantly

[bold cyan]Next Steps:[/bold cyan]

1. Create your character (race and class)
2. Choose or create a world
3. Start exploring!
4. Type /help anytime for more command info

[bold green]Remember:[/bold green]
  • The world reacts to YOUR choices
  • There's no winning or losing — just YOUR story
  • Be creative and have fun
  • The AI supports your imagination
  • Your adventure is unique to you

[bold cyan]And if you get stuck:[/bold cyan]
  • Type /help to see all commands
  • Be more specific with your actions
  • Try talking to NPCs for clues
  • Type /save before risky actions

The world of RAG-Quest awaits, adventurer. 

[bold cyan]Your legend begins now...[/bold cyan]

Press Enter to start your adventure!
    """
    console.print(Panel(content, border_style="cyan", expand=False))
    input()


def run_full_tutorial() -> None:
    """Run the complete tutorial sequence."""
    steps = [
        ("Welcome", print_tutorial_welcome),
        ("Exploration", step_1_basic_movement),
        ("NPCs", step_2_talking_to_npcs),
        ("Inventory", step_3_inventory),
        ("Combat", step_4_combat),
        ("Commands", step_5_commands),
        ("Quests", step_6_quests),
        ("Saving", step_7_saving),
        ("Pro Tips", step_8_pro_tips),
        ("Campaign Memory", step_9_campaign_memory),
        ("Ready", step_10_ready),
    ]

    for i, (step_name, step_func) in enumerate(steps, 1):
        try:
            step_func()
        except KeyboardInterrupt:
            console.print(
                "\n[yellow]Tutorial interrupted. You can resume anytime with /tutorial[/yellow]"
            )
            return
        except EOFError:
            # Handle piped input or EOF gracefully
            console.print(
                "\n[yellow]Tutorial ended. You can resume anytime with /tutorial[/yellow]"
            )
            return

    console.clear()
    console.print("""
[green]╔════════════════════════════════════════════════════════════╗[/green]
[green]║                                                            ║[/green]
[green]║         🎮 TUTORIAL COMPLETE - HAPPY ADVENTURING! 🎮       ║[/green]
[green]║                                                            ║[/green]
[green]╚════════════════════════════════════════════════════════════╝[/green]
    """)


def run_interactive_tutorial() -> None:
    """Entry point for tutorial from game menu."""
    try:
        run_full_tutorial()
    except Exception as e:
        console.print(f"[red]Tutorial error: {e}[/red]")
