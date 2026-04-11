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
from .. import ui
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


def run_game(
    game_state: GameState,
    save_path: Optional[Path] = None,
) -> None:
    """
    Main game loop with comprehensive error handling and auto-save.
    """
    console.clear()
    _print_banner(game_state.world)

    action_count = 0
    errors_in_row = 0
    max_errors_in_row = 3

    try:
        while game_state.character.is_alive():
            # Print status
            ui.print_status_bar(game_state.character, game_state.world)

            # Get player input
            try:
                player_input = ui.print_command_prompt()
            except EOFError:
                break

            if not player_input:
                continue

            # Handle special commands
            if player_input.startswith("/"):
                if not _handle_command(player_input, game_state, save_path):
                    break
                continue

            # Process action through narrator with error recovery
            with console.status("[bold green]The Dungeon Master considers your action...[/bold green]"):
                try:
                    response = game_state.narrator.process_action(player_input)
                    errors_in_row = 0  # Reset error counter on success
                except Exception as e:
                    errors_in_row += 1
                    ui.print_error(f"Error generating response: {type(e).__name__}")
                    
                    # If too many errors in a row, suggest exiting
                    if errors_in_row >= max_errors_in_row:
                        ui.print_error("Too many errors. Consider saving and restarting.")
                        response = (
                            "The world seems unstable. You should find a safe place to rest "
                            "before continuing your adventure."
                        )
                    else:
                        continue

            # Display response
            ui.print_narrator_response(response)

            # Auto-save frequently to protect progress
            action_count += 1
            if save_path:
                # Save every 3 actions or every 5 minutes of gameplay
                if action_count % 3 == 0:
                    try:
                        _save_game(game_state, save_path)
                    except Exception as e:
                        ui.print_warning(f"Could not auto-save: {e}")

    except KeyboardInterrupt:
        console.print("\n[yellow]Game interrupted by player.[/yellow]")
    finally:
        # Cleanup
        try:
            game_state.world_rag.close()
        except Exception as e:
            pass
        
        try:
            game_state.llm.close()
        except Exception as e:
            pass

    ui.print_game_over(game_state.character, game_state.world)


def _handle_command(
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

    if cmd == "/inventory" or cmd == "/i":
        ui.print_inventory_panel(game_state.inventory)

    elif cmd == "/quests" or cmd == "/q":
        ui.print_quest_log_panel(game_state.quest_log)

    elif cmd == "/look":
        context_query = f"Detailed description of {game_state.character.location}"
        description = game_state.world_rag.query_world(
            context_query, param="hybrid"
        )
        console.print(
            Panel(description or "You see nothing special here.", 
                  title=game_state.character.location)
        )

    elif cmd == "/map":
        ui.print_world_context(game_state.world)

    elif cmd == "/status" or cmd == "/s":
        ui.print_character_status(game_state.character)

    elif cmd == "/save":
        if save_path:
            _save_game(game_state, save_path)
            ui.print_success("Game saved!")
        else:
            ui.print_warning("No save location specified.")

    elif cmd == "/help":
        ui.print_help()

    elif cmd == "/quit":
        if save_path:
            if ui.get_yes_no_confirmation("[yellow]Save before quitting?[/yellow]"):
                _save_game(game_state, save_path)
        return False

    else:
        ui.print_error(f"Unknown command: {cmd}")

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
