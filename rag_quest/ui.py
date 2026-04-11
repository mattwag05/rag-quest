"""Rich terminal UI components for RAG-Quest."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.rule import Rule
from rich.align import Align
from rich.layout import Layout

console = Console()


def print_welcome_screen() -> None:
    """Print the welcome screen with game title and menu."""
    console.clear()
    
    # ASCII Art Title
    title = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                   RAG-QUEST                               ║
    ║        AI-Powered D&D with Knowledge Graphs               ║
    ║                 Version 0.1.0                             ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(title, style="cyan")
    console.print(
        Align.center("An adventure awaits in a world shaped by AI..."),
        style="yellow"
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
    console.print(Panel(response, title="[bold]Dungeon Master[/bold]", border_style="blue"))


def print_command_prompt() -> str:
    """Print input prompt and get user input."""
    return console.input("\n[bold cyan]> [/bold cyan]").strip()


def print_inventory_panel(inventory) -> None:
    """Print inventory in a styled panel."""
    inventory_text = inventory.list_items()
    console.print(Panel(inventory_text, title="[bold]Inventory[/bold]", border_style="magenta"))


def print_quest_log_panel(quest_log) -> None:
    """Print quest log in a styled panel."""
    quest_text = quest_log.list_quests()
    console.print(Panel(quest_text, title="[bold]Quest Log[/bold]", border_style="yellow"))


def print_character_status(character) -> None:
    """Print detailed character status."""
    status_text = character.get_status()
    console.print(Panel(status_text, title="[bold]Character Status[/bold]", border_style="green"))


def print_world_context(world) -> None:
    """Print world context and discovered locations."""
    locations = ", ".join(world.visited_locations) if world.visited_locations else "None yet"
    context = f"""[bold]Setting:[/bold] {world.setting}
[bold]Tone:[/bold] {world.tone}
[bold]Day:[/bold] {world.day_number}
[bold]Time:[/bold] {world.current_time.value}
[bold]Weather:[/bold] {world.weather.value}
[bold]Visited Locations:[/bold]
{locations}"""
    console.print(Panel(context, title="[bold]World[/bold]", border_style="cyan"))


def print_help() -> None:
    """Print in-game help."""
    help_text = """
# RAG-Quest Commands

## Navigation & Interaction
Type natural language actions to interact with the world:
- `go to the tavern`
- `examine the chest`
- `talk to the merchant`

## In-Game Commands

- `/help` - Show this help
- `/inventory` or `/i` - Show inventory
- `/quests` or `/q` - Show active quests
- `/status` or `/s` - Show character stats
- `/look` - Examine current location
- `/map` - Show discovered locations
- `/save` - Save game
- `/load` - Load game (next session)
- `/quit` - Exit game (with save prompt)

## Tips

1. **Be creative** - The AI responds to creative descriptions and actions
2. **Combat** - Describe tactical actions like "dodge and counterattack"
3. **Dialogue** - Talk to NPCs to learn about quests and lore
4. **Exploration** - Visit new locations to discover items and meet NPCs
5. **Resources** - Manage your HP and inventory carefully
"""
    console.print(Panel(Markdown(help_text), title="[bold]Help[/bold]", border_style="green"))


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
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            console.print("[red]Please enter 'y' or 'n'.[/red]")
        except EOFError:
            # Default to no if stdin is closed
            return False
