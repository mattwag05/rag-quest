"""Main entry point for RAG-Quest."""

import asyncio
import sys
from pathlib import Path

from rich.console import Console

from . import config, ui
from .engine import run_game, GameState, Narrator
from .knowledge import WorldRAG

console = Console()


def main() -> None:
    """Main entry point."""
    try:
        _main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Game interrupted by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        ui.print_error(str(e))
        if "--debug" in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _main() -> None:
    """Main logic."""
    ui.print_welcome_screen()
    
    # Load or create configuration
    try:
        game_config = config.get_config()
    except RuntimeError as e:
        ui.print_error(str(e))
        sys.exit(1)

    # Load LLM provider
    try:
        llm_provider, llm_config = config.load_llm_provider(game_config)
        ui.print_success("LLM provider loaded!")
    except Exception as e:
        ui.print_error(f"Failed to load LLM provider: {e}")
        if "--debug" in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # Create world and character
    try:
        world = config.create_world_from_config(game_config)
        character = config.create_character_from_config(game_config)
        ui.print_success(f"Welcome, {character.name}!")
    except Exception as e:
        ui.print_error(f"Failed to create world or character: {e}")
        sys.exit(1)

    # Get RAG profile from config
    rag_config = game_config.get("rag", {})
    rag_profile = rag_config.get("profile", "balanced")
    
    ui.print_info(f"Using RAG profile: {rag_profile}")

    # Initialize RAG system with profile (lazy - will initialize on first use)
    try:
        world_rag = WorldRAG(world.name, llm_config, llm_provider, rag_profile=rag_profile)
        ui.print_success("Knowledge graph system ready!")
    except Exception as e:
        ui.print_error(f"Failed to create RAG system: {e}")
        if "--debug" in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # Check for lore files to ingest
    lore_path = game_config["world"].get("lore_path")
    if lore_path:
        lore_file = Path(lore_path)
        if lore_file.exists():
            ui.print_info(f"Lore file found at {lore_path} (will ingest during game)")

    # Create narrator
    from .engine.inventory import Inventory
    from .engine.quests import QuestLog

    inventory = Inventory()
    quest_log = QuestLog()
    narrator = Narrator(llm_provider, world_rag, character, world, inventory, quest_log)

    # Create game state
    game_state = GameState(
        character=character,
        world=world,
        inventory=inventory,
        quest_log=quest_log,
        narrator=narrator,
        world_rag=world_rag,
        llm=llm_provider,
    )

    # Determine save path
    save_dir = Path.home() / ".local/share/rag-quest/saves"
    save_path = save_dir / f"{world.name}.json"

    # Run the game
    run_game(game_state, save_path)


if __name__ == "__main__":
    main()
