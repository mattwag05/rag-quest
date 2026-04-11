"""Main entry point for RAG-Quest."""

import asyncio
import sys
from pathlib import Path

from rich.console import Console

from . import config
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
        console.print(f"[red]Fatal error: {e}[/red]")
        if "--debug" in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _main() -> None:
    """Main logic."""
    # Load or create configuration
    game_config = config.get_config()

    # Load LLM provider
    llm_provider, llm_config = config.load_llm_provider(game_config)

    # Create world and character
    world = config.create_world_from_config(game_config)
    character = config.create_character_from_config(game_config)

    # Get RAG profile from config
    rag_config = game_config.get("rag", {})
    rag_profile = rag_config.get("profile", "balanced")
    
    console.print(f"[cyan]Using RAG profile: {rag_profile}[/cyan]")

    # Initialize RAG system with profile
    world_rag = WorldRAG(world.name, llm_config, llm_provider, rag_profile=rag_profile)
    world_rag.initialize()

    # Check for lore files to ingest
    lore_path = game_config["world"].get("lore_path")
    if lore_path:
        lore_file = Path(lore_path)
        if lore_file.exists():
            console.print(f"[cyan]Ingesting lore from {lore_path}...[/cyan]")
            try:
                if lore_file.is_file():
                    world_rag.ingest_file(str(lore_file))
                else:
                    from .knowledge.ingest import ingest_directory
                    files = ingest_directory(str(lore_file), profile=rag_profile)
                    for filename, content in files.items():
                        world_rag.ingest_text(content, source=filename)
                console.print("[green]Lore ingested successfully![/green]")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not ingest lore: {e}[/yellow]")

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
