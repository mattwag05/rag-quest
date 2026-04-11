"""Main game loop and state management."""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ..knowledge import WorldRAG
from ..llm import BaseLLMProvider
from .character import Character
from .inventory import Inventory
from .narrator import Narrator
from .quests import QuestLog
from .world import World


console = Console()


@dataclass
class GameState:
    """Complete game state."""

    character: Character
    world: World
    inventory: Inventory
    quest_log: QuestLog
    narrator: Narrator
    world_rag: WorldRAG
    llm: BaseLLMProvider

    def to_dict(self) -> dict:
        """Serialize game state."""
        return {
            "character": self.character.to_dict(),
            "world": self.world.to_dict(),
            "inventory": self.inventory.to_dict(),
            "quest_log": self.quest_log.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
        narrator: Narrator,
        world_rag: WorldRAG,
        llm: BaseLLMProvider,
    ) -> "GameState":
        """Deserialize game state."""
        character = Character.from_dict(data["character"])
        world = World.from_dict(data["world"])
        inventory = Inventory.from_dict(data["inventory"])
        quest_log = QuestLog.from_dict(data["quest_log"])

        return cls(
            character=character,
            world=world,
            inventory=inventory,
            quest_log=quest_log,
            narrator=narrator,
            world_rag=world_rag,
            llm=llm,
        )


async def run_game(
    game_state: GameState,
    save_path: Optional[Path] = None,
) -> None:
    """
    Main game loop.
    """
    console.clear()
    _print_banner(game_state.world)

    try:
        while game_state.character.is_alive():
            # Print prompt
            _print_status(game_state)

            # Get player input
            try:
                player_input = console.input("\n[bold cyan]> [/bold cyan]").strip()
            except EOFError:
                break

            if not player_input:
                continue

            # Handle special commands
            if player_input.startswith("/"):
                if not await _handle_command(player_input, game_state, save_path):
                    break
                continue

            # Process action through narrator
            with console.status("[bold green]Thinking...[/bold green]"):
                try:
                    response = await game_state.narrator.process_action(player_input)
                except Exception as e:
                    console.print(
                        f"[red]Error generating response: {e}[/red]"
                    )
                    continue

            # Display response
            console.print(Panel(response, border_style="blue"))

            # Auto-save periodically
            if save_path and len(game_state.narrator.conversation_history) % 4 == 0:
                _save_game(game_state, save_path)

    finally:
        # Cleanup
        await game_state.world_rag.close()
        await game_state.llm.close()

    _print_game_over(game_state)


async def _handle_command(
    command: str,
    game_state: GameState,
    save_path: Optional[Path] = None,
) -> bool:
    """
    Handle special commands.
    Returns False to quit, True to continue.
    """
    parts = command.split()
    cmd = parts[0].lower()

    if cmd == "/inventory":
        console.print(
            Panel(game_state.inventory.list_items(), title="Inventory")
        )

    elif cmd == "/quests":
        console.print(
            Panel(game_state.quest_log.list_quests(), title="Quest Log")
        )

    elif cmd == "/look":
        context_query = f"Detailed description of {game_state.character.location}"
        description = await game_state.world_rag.query_world(
            context_query, param="hybrid"
        )
        console.print(
            Panel(description or "You see nothing special here.", 
                  title=game_state.character.location)
        )

    elif cmd == "/map":
        locations = ", ".join(game_state.world.visited_locations)
        console.print(
            Panel(
                locations or "No locations discovered yet.",
                title="Visited Locations",
            )
        )

    elif cmd == "/status":
        console.print(
            Panel(game_state.character.get_status(), title="Character Status")
        )

    elif cmd == "/save":
        if save_path:
            _save_game(game_state, save_path)
            console.print("[green]Game saved![/green]")
        else:
            console.print("[yellow]No save location specified.[/yellow]")

    elif cmd == "/help":
        help_text = """
**Commands:**
- `/inventory` - Show inventory
- `/quests` - Show quest log
- `/look` - Examine current location
- `/map` - Show visited locations
- `/status` - Show character status
- `/save` - Save game
- `/help` - Show this help
- `/quit` - Quit game

**Gameplay:**
Type natural language actions to interact with the world. The AI narrator will respond to your actions.
"""
        console.print(Panel(Markdown(help_text), title="Help"))

    elif cmd == "/quit":
        if save_path:
            response = console.input("[yellow]Save before quitting? (y/n): [/yellow]")
            if response.lower() == "y":
                _save_game(game_state, save_path)
        return False

    else:
        console.print(f"[red]Unknown command: {cmd}[/red]")

    return True


def _print_banner(world: World) -> None:
    """Print game banner."""
    banner = f"""
 ██████╗  █████╗  ██████╗       ██████╗ ██╗   ██╗███████╗███████╗████████╗
██╔════╝ ██╔══██╗██╔════╝       ██╔═══██╗██║   ██║██╔════╝██╔════╝╚══██╔══╝
██║  ███╗███████║██║  ███╗█████╗██║   ██║██║   ██║█████╗  ███████╗   ██║   
██║   ██║██╔══██║██║   ██║╚════╝██║▄▄ ██║██║   ██║██╔══╝  ╚════██║   ██║   
╚██████╔╝██║  ██║╚██████╔╝      ╚██████╔╝╚██████╔╝███████╗███████║   ██║   
 ╚═════╝ ╚═╝  ╚═╝ ╚═════╝        ╚══▀▀═══╝ ╚═════╝ ╚══════╝╚══════╝   ╚═╝   
"""
    console.print(banner, style="cyan")
    console.print(
        f"Welcome to [bold]{world.name}[/bold] - {world.setting}",
        justify="center",
    )
    console.print(f"A {world.tone} adventure awaits...\n", justify="center")


def _print_status(game_state: GameState) -> None:
    """Print current status."""
    status = (
        f"[cyan]{game_state.character.name}[/cyan] | "
        f"[yellow]{game_state.character.location}[/yellow] | "
        f"[red]HP: {game_state.character.current_hp}/{game_state.character.max_hp}[/red] | "
        f"{game_state.world.get_context()}"
    )
    console.print(status)


def _print_game_over(game_state: GameState) -> None:
    """Print game over message."""
    console.print("\n")
    if game_state.character.is_alive():
        console.print(
            Panel(
                "Thanks for playing RAG-Quest!",
                title="Until Next Time",
                border_style="blue",
            )
        )
    else:
        console.print(
            Panel(
                f"[red]{game_state.character.name} has fallen...[/red]\n"
                f"Survived {game_state.world.day_number} days.",
                title="Game Over",
                border_style="red",
            )
        )


def _save_game(game_state: GameState, save_path: Path) -> None:
    """Save game state to file."""
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w") as f:
        json.dump(game_state.to_dict(), f, indent=2)
