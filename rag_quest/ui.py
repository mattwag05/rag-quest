"""Rich terminal UI components for RAG-Quest."""

from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from rag_quest import __version__

console = Console()


def print_welcome_screen() -> None:
    """Print the welcome screen with game title and menu."""
    console.clear()

    # ASCII Art Title
    title = f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║                   RAG-QUEST                               ║
    ║        AI-Powered D&D with Knowledge Graphs               ║
    ║                 Version {__version__:<36s}║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(title, style="cyan")
    console.print(
        Align.center("An adventure awaits in a world shaped by AI..."), style="yellow"
    )
    console.print()


def print_menu(options: list[str]) -> int:
    """
    Print a menu and get user selection.

    Args:
        options: List of menu option strings

    Returns:
        Selected option index (0-based)
    """
    console.print()
    for i, option in enumerate(options, 1):
        console.print(f"  [{i}] {option}")

    while True:
        try:
            choice = console.input("\n[bold cyan]Choose an option:[/bold cyan] ")
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(options):
                return choice_idx
            console.print("[red]Invalid selection. Please try again.[/red]")
        except ValueError:
            console.print("[red]Please enter a number.[/red]")


def print_status_bar(character, world) -> None:
    """Print character and world status bar."""
    # HP bar
    hp_bar_length = 20
    hp_filled = int((character.current_hp / character.max_hp) * hp_bar_length)
    hp_bar = "█" * hp_filled + "░" * (hp_bar_length - hp_filled)

    # Color HP bar based on health
    if character.current_hp / character.max_hp > 0.5:
        hp_color = "green"
    elif character.current_hp / character.max_hp > 0.25:
        hp_color = "yellow"
    else:
        hp_color = "red"

    status = f"""[cyan]{character.name}[/cyan] | [yellow]{character.location}[/yellow]
[{hp_color}]HP: {hp_bar} {character.current_hp}/{character.max_hp}[/{hp_color}]
{world.get_context()}"""

    console.print(Panel(status, expand=False, border_style="blue"))


def print_narrator_response(response: str) -> None:
    """Print narrator response in a styled panel."""
    console.print(
        Panel(response, title="[bold]Dungeon Master[/bold]", border_style="blue")
    )


def stream_narrator_response(chunks) -> str:
    """Render a streaming narrator response via Rich `Live`, returning the
    full joined text after the stream is exhausted.

    `chunks` is any iterator yielding str pieces (typically from
    `Narrator.stream_action`). Updates the panel in place as each chunk
    arrives so the player sees prose unfold live rather than waiting for
    the full response. If `rich.live` is unavailable for any reason,
    degrades to a terminal-less accumulation that still returns the full
    text — the caller will just see a final `print_narrator_response`
    call instead.
    """
    from rich.live import Live

    buffer: list[str] = []

    def _panel(text: str) -> Panel:
        return Panel(
            text or "[dim]…[/dim]",
            title="[bold]Dungeon Master[/bold]",
            border_style="blue",
        )

    try:
        with Live(_panel(""), console=console, refresh_per_second=12) as live:
            for chunk in chunks:
                if not chunk:
                    continue
                buffer.append(chunk)
                live.update(_panel("".join(buffer)))
    except Exception:
        # Fall back to a final plain render if Live fails for any reason
        # (terminal shenanigans, nested Live contexts).
        for chunk in chunks:
            if chunk:
                buffer.append(chunk)
        print_narrator_response("".join(buffer))
    return "".join(buffer)


def print_command_prompt() -> str:
    """Print input prompt and get user input."""
    result = console.input("\n[bold cyan]What do you do? > [/bold cyan]").strip()
    if not result:
        console.print(
            "[dim]Tip: Type an action like 'look around' or '/help' for commands[/dim]"
        )
    return result


def print_inventory_panel(inventory) -> None:
    """Print inventory in a styled panel."""
    inventory_text = inventory.list_items()
    console.print(
        Panel(inventory_text, title="[bold]Inventory[/bold]", border_style="magenta")
    )


def print_quest_log_panel(quest_log) -> None:
    """Print quest log in a styled panel."""
    quest_text = quest_log.list_quests()
    console.print(
        Panel(quest_text, title="[bold]Quest Log[/bold]", border_style="yellow")
    )


def print_help() -> None:
    """Print in-game help."""
    help_text = """
# RAG-Quest Commands & Tips

## How to Play
Just type what you want to do! The AI understands natural language:
- `look around`
- `go to the tavern`
- `talk to the merchant about quests`
- `examine the ancient chest`
- `cast fireball at the goblin`
- `carefully search the bookshelf`

Be creative and descriptive — the AI remembers what happened and your choices matter!

## Quick Commands (Shortcuts)

| Command | Shortcut | Description |
|---------|----------|-------------|
| `/tutorial` | — | Interactive tutorial (5 minutes) |
| `/inventory` | `/i` | Check your inventory |
| `/quests` | `/q` | View active quests |
| `/stats` | `/s` | Show character stats |
| `/party` | `/p` | Show party members |
| `/relationships` | `/rel` | View NPC relationships |
| `/timeline` | `/t` | Show chronological event log |
| `/lore` | `/l` | Browse the lore encyclopedia |
| `/notes` | `/n` | View or refresh campaign notes |
| `/help` | `/h` | Show this help screen |

## All Commands

### Status & Inventory
- `/help` `/h` — Show this help screen
- `/tutorial` — Interactive tutorial (5 minutes)
- `/stats` `/s` — Show your character stats and attributes
- `/inventory` `/i` — Check what you're carrying and weight limit
- `/quests` `/q` — View active quests and objectives
- `/abilities` — List unlocked class abilities

### Exploration & World
- `/look` — Examine your current surroundings
- `/map` — See locations you've discovered
- `/events` — View active world events
- `/world` — World information and context

### Party & Relationships
- `/party` `/p` — Show party members and their status
- `/relationships` `/rel` — View NPC relationships and trust
- `/factions` `/f` — View faction standings
- `/recruit NAME` — Recruit an NPC to join your party
- `/dismiss NAME` — Remove party member

### Campaign Memory (v0.6)
- `/timeline` `/t` — Scrollable chronological event log (filter: combat, quest, npc, item, location, all)
- `/bookmark [note]` `/bm` — Save the current turn's full narrator prose as a highlight
- `/bookmarks` — List your saved highlights
- `/notes` `/n` — Show campaign notes; `/notes refresh` forces an update
- `/canonize [N|all]` — Promote notes into permanent world lore (LightRAG)
- `/lore [category] [name]` `/l` — Browse encyclopedia; drills into RAG for rich detail

### Advanced
- `/equipment` — Check equipped gear (weapon, armor, accessory)
- `/voice` — Toggle text-to-speech narration
- `/dungeon` — Enter a procedural dungeon crawl
- `/achievements` — View unlocked achievements
- `/config` — Change game settings
- `/save` — Manually save your game
- `/new` — Start a new game (without quitting)
- `/quit` — Exit game (prompts to save)

## Pro Tips

1. **Be specific** — "search carefully" works better than "search"
2. **Use the world** — Reference locations, NPCs, and items from earlier
3. **Combat tactics** — Describe your combat actions: "dodge left and counterattack"
4. **Dialogue** — Talk to NPCs to learn about quests and world lore
5. **Inventory** — Watch your carrying capacity and manage your gear
6. **Exploration** — New locations unlock new encounters and loot
7. **Party** — Recruit allies to enhance your abilities and story

## Game Features

**Persistent World** — Your actions change the world. NPCs remember you.
**Achievements** — Unlock achievements for exploring, fighting, and completing quests.
**Procedural Dungeons** — `/dungeon` generates new dungeons with scaling difficulty.
**Auto-Save** — Your progress is saved automatically every few turns.
**Character Progression** — Level up, unlock new abilities, and improve your stats.

## Stuck or Need Advice?

1. Describe what you want to do more specifically
2. Use `/look` to examine your surroundings
3. Check `/quests` to see current objectives
4. Visit `/stats` to review your abilities and equipment
5. Talk to NPCs to learn about available quests

Happy adventuring!
"""
    console.print(
        Panel(
            Markdown(help_text),
            title="[bold cyan]Help & Commands[/bold cyan]",
            border_style="green",
        )
    )


def print_game_over(character, world) -> None:
    """Print game over message."""
    if character.is_alive():
        message = f"[green]Thanks for playing RAG-Quest![/green]\n\nYou survived {world.day_number} days."
        title = "Until Next Time"
        border = "blue"
    else:
        message = f"""[red]{character.name} has fallen...[/red]

Rest in peace, brave adventurer.
Survived {world.day_number} days in {world.name}."""
        title = "Game Over"
        border = "red"

    console.print(Panel(message, title=f"[bold]{title}[/bold]", border_style=border))


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red][bold]ERROR:[/bold] {message}[/red]")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow][bold]WARNING:[/bold] {message}[/yellow]")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]{message}[/green]")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[cyan]{message}[/cyan]")


def print_status_message(message: str) -> None:
    """Print a status message (for loading, processing, etc.)."""
    console.status(f"[bold green]{message}[/bold green]")


def create_loading_status():
    """Return a context manager for status messages."""
    return console.status("[bold green]Processing...[/bold green]")


def get_yes_no_confirmation(prompt: str) -> bool:
    """Get yes/no confirmation from user."""
    while True:
        try:
            response = console.input(f"{prompt} [y/n]: ").strip().lower()
            if response in ["y", "yes"]:
                return True
            elif response in ["n", "no"]:
                return False
            console.print("[red]Please enter 'y' or 'n'.[/red]")
        except EOFError:
            # Default to no if stdin is closed
            return False


def print_world_event(message: str) -> None:
    """Print a world event notification."""
    console.print(
        Panel(message, title="[bold red]⚡ World Event[/bold red]", border_style="red")
    )


def print_character_status(character) -> None:
    """Print detailed character status."""
    status_lines = [
        f"[cyan]{character.name}[/cyan]",
        f"Level: {character.level} | XP: {character.experience}",
        f"Race: {character.race.value} | Class: {character.character_class.value}",
        "",
        "Attributes:",
        f"  STR: {character.strength:2d} | DEX: {character.dexterity:2d} | CON: {character.constitution:2d}",
        f"  INT: {character.intelligence:2d} | WIS: {character.wisdom:2d} | CHA: {character.charisma:2d}",
        "",
        f"HP: {character.current_hp}/{character.max_hp}",
    ]
    console.print(
        Panel("\n".join(status_lines), title="Character Status", border_style="cyan")
    )


def print_world_context(world) -> None:
    """Print world state and locations."""
    context = world.get_context()
    console.print(Panel(context, title="World Status", border_style="blue"))


def print_achievement_unlocked(name: str, icon: str = "★") -> None:
    """Print achievement unlock celebration."""
    console.print(
        Panel(
            f"[bold green]{icon} Achievement Unlocked! {icon}[/bold green]\n\n{name}",
            border_style="yellow",
            expand=False,
        )
    )


def print_level_up(level: int, stats_gained: str = "") -> None:
    """Print level up celebration."""
    message = f"[bold cyan]⚔ LEVEL UP! ⚔[/bold cyan]\n\nYou're now [bold]Level {level}[/bold]!"
    if stats_gained:
        message += f"\n{stats_gained}"
    console.print(Panel(message, border_style="yellow", expand=False))


def print_game_recap(character, world, days_survived: int) -> None:
    """Print a recap of the game before loading/continuing."""
    recap = f"""[cyan]Last Adventure:[/cyan]
[bold]{character.name}[/bold] — {character.race.value} {character.character_class.value}
Level {character.level} | {character.current_hp}/{character.max_hp} HP
World: {world.name} ({world.setting})
Survived: {days_survived} days

Ready to continue? Type any action or [cyan]/help[/cyan] for commands."""
    console.print(Panel(recap, title="[bold]Welcome Back[/bold]", border_style="green"))


def print_save_confirmation(
    save_name: str, character_name: str, world_name: str
) -> None:
    """Print confirmation that save was successful."""
    msg = f"[green]✓ Game saved![/green]\n\n[cyan]{character_name}[/cyan] in [cyan]{world_name}[/cyan]\nSlot: [dim]{save_name}[/dim]"
    console.print(Panel(msg, border_style="green", expand=False))


def print_unknown_command(command: str) -> None:
    """Print helpful message for unknown command with suggestions."""
    console.print(f"[yellow]Hmm, '[bold]{command}[/bold]' isn't recognized.[/yellow]")
    console.print("[dim]Did you mean one of these?[/dim]")
    console.print("  /help — See all commands and tips")
    console.print("  /inventory — Check your items")
    console.print("  /stats — View your status")
    console.print("[dim]Or just type what you want to do, like 'look around'[/dim]")


def print_confirm_quit() -> bool:
    """Get confirmation for quit action."""
    console.print("\n[yellow]Are you sure you want to quit?[/yellow]")
    result = (
        console.input("[cyan]Your progress will be saved. Continue? [y/n]: [/cyan]")
        .strip()
        .lower()
    )
    return result in ["y", "yes"]


def validate_name_input(prompt: str, allow_empty: bool = False) -> str:
    """Get and validate a name from user with smart defaults."""
    while True:
        name = console.input(f"\n[bold]{prompt}[/bold]").strip()
        if not name:
            if allow_empty:
                return ""
            console.print("[yellow]Name cannot be empty. Try again.[/yellow]")
            continue
        if len(name) > 50:
            console.print(
                "[yellow]Name too long (max 50 characters). Try again.[/yellow]"
            )
            continue
        return name


def validate_number_input(prompt: str, min_val: int = 1, max_val: int = 99) -> int:
    """Get and validate a number from user."""
    while True:
        try:
            value = int(
                console.input(f"[bold]{prompt}[/bold] [{min_val}-{max_val}]: ").strip()
            )
            if min_val <= value <= max_val:
                return value
            console.print(
                f"[yellow]Please enter a number between {min_val} and {max_val}.[/yellow]"
            )
        except ValueError:
            console.print("[yellow]Please enter a valid number.[/yellow]")


def print_thinking() -> None:
    """Print thinking indicator."""
    with console.status(
        "[bold cyan]The Dungeon Master considers your action...[/bold cyan]"
    ):
        pass


def print_loading_world() -> None:
    """Print world loading indicator."""
    with console.status("[bold cyan]Loading world...[/bold cyan]"):
        pass


def print_character_creation_summary(
    name: str, race: str, character_class: str
) -> bool:
    """Show character creation summary and confirm."""
    summary = f"""[cyan]You'll be playing as:[/cyan]

[bold]{name}[/bold]
{race} {character_class}

Ready to begin your adventure? [y/n]"""
    console.print(Panel(summary, border_style="cyan"))
    result = console.input("[cyan]Continue? [y/n]: [/cyan]").strip().lower()
    return result in ["y", "yes"]
