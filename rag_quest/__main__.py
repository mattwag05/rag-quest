"""Main entry point for RAG-Quest."""

import sys
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from . import config, startup, ui
from .engine import GameState, Narrator, run_game
from .knowledge import WorldRAG

console = Console()


def main() -> None:
    """Main entry point."""
    # Subcommand dispatch. First positional non-flag arg is the subcommand.
    positional = [a for a in sys.argv[1:] if not a.startswith("-")]
    if positional and positional[0] == "validate-module":
        sys.exit(_cmd_validate_module(positional[1:]))
    if positional and positional[0] == "new-module":
        sys.exit(_cmd_new_module(positional[1:]))
    if positional and positional[0] == "export-campaign":
        sys.exit(_cmd_export_campaign(positional[1:]))
    if positional and positional[0] == "import-campaign":
        sys.exit(_cmd_import_campaign(positional[1:]))
    if positional and positional[0] == "serve":
        sys.exit(_cmd_serve(sys.argv[2:]))

    try:
        _main()
    except KeyboardInterrupt:
        console.print(
            "\n[yellow]Thanks for playing! Your progress has been saved.[/yellow]"
        )
        sys.exit(0)
    except Exception as e:
        # Never show traceback to users - always friendly messages
        error_msg = str(e)
        if "Ollama" in error_msg or "localhost:11434" in error_msg:
            ui.print_error(
                "Could not connect to Ollama. Is it running? Check the startup guide with /help."
            )
        elif "API" in error_msg or "provider" in error_msg.lower():
            ui.print_error(
                f"LLM provider error: {error_msg}. Check your configuration with /config."
            )
        elif "file" in error_msg.lower() or "path" in error_msg.lower():
            ui.print_error(
                f"File error: {error_msg}. Check the file path and try again."
            )
        else:
            ui.print_error(f"An unexpected error occurred: {error_msg}")

        if "--debug" in sys.argv:
            console.print("\n[dim]Debug trace:[/dim]")
            import traceback

            traceback.print_exc()
        sys.exit(1)


def _cmd_validate_module(args: list[str]) -> int:
    """Subcommand: rag-quest validate-module <dir-or-modules.yaml>.

    Returns a process exit code — 0 if the manifest is clean, 1 on any
    fatal error. Warnings do not fail the check.
    """
    from .worlds.modules import MANIFEST_FILENAME
    from .worlds.validate import validate_manifest

    if not args:
        ui.print_error(
            f"Usage: rag-quest validate-module <world-dir or path to {MANIFEST_FILENAME}>"
        )
        return 1

    target = Path(args[0])
    if target.is_file() and target.name == MANIFEST_FILENAME:
        world_dir = target.parent
    elif target.is_dir():
        world_dir = target
    else:
        ui.print_error(f"Not a directory or {MANIFEST_FILENAME}: {target}")
        return 1

    result = validate_manifest(world_dir)

    module_count = len(result.registry) if result.registry is not None else 0
    console.print(
        f"[bold]Validating {world_dir / MANIFEST_FILENAME}[/bold] "
        f"({module_count} module(s))"
    )

    for warning in result.warnings:
        ui.print_warning(warning)
    for error in result.errors:
        ui.print_error(error)

    if result.ok:
        ui.print_success(f"Manifest is clean — {module_count} module(s) validated.")
        return 0
    return 1


def _cmd_new_module(args: list[str]) -> int:
    """Subcommand: rag-quest new-module <world-dir>.

    Drives the interactive new-module flow, appending a validated stanza to
    `<world-dir>/modules.yaml`. Exits 0 on success, 1 on validator failure
    or missing/invalid args.
    """
    from .worlds.modules import ModuleManifestError
    from .worlds.new_module import run_interactive

    if not args:
        ui.print_error("Usage: rag-quest new-module <world-dir>")
        return 1

    world_dir = Path(args[0])
    if world_dir.exists() and not world_dir.is_dir():
        ui.print_error(f"Not a directory: {world_dir}")
        return 1

    try:
        run_interactive(world_dir)
    except ModuleManifestError as e:
        ui.print_error(f"Could not add module: {e}")
        return 1
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Cancelled.[/yellow]")
        return 1
    return 0


def _cmd_export_campaign(args: list[str]) -> int:
    """Subcommand: rag-quest export-campaign <world-name> [output.rqworld].

    Bundles the player's save, world directory (modules.yaml + lore), and
    world state into a single `.rqworld` file suitable for moving to
    another machine. Exits 0 on success, 1 on missing save.
    """
    import json

    from .worlds.exporter import WorldExporter

    if not args:
        ui.print_error("Usage: rag-quest export-campaign <world-name> [output.rqworld]")
        return 1

    world_name = args[0]
    out_path = Path(args[1]) if len(args) > 1 else Path(f"{world_name}.rqworld")

    install_dir = Path.home() / ".local/share/rag-quest"
    save_path = install_dir / "saves" / f"{world_name}.json"
    source_dir = install_dir / "worlds" / world_name

    if not save_path.exists():
        ui.print_error(f"No save file at {save_path}")
        return 1

    try:
        game_state = json.loads(save_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        ui.print_error(f"Could not read save file: {e}")
        return 1

    result = WorldExporter.export_world(
        game_state=game_state,
        output_path=out_path,
        author=game_state.get("character", {}).get("name", "Unknown"),
        source_dir=source_dir if source_dir.exists() else None,
        save_file=save_path,
    )
    if result is None:
        ui.print_error("Export failed.")
        return 1
    ui.print_success(f"Exported campaign to {result}")
    return 0


def _cmd_import_campaign(args: list[str]) -> int:
    """Subcommand: rag-quest import-campaign <file.rqworld>.

    Restores the bundled save, world directory, and lore into the
    standard RAG-Quest install dirs under `~/.local/share/rag-quest/`.
    """
    from .worlds.importer import WorldImporter

    if not args:
        ui.print_error("Usage: rag-quest import-campaign <file.rqworld>")
        return 1

    pack = Path(args[0])
    if not pack.exists():
        ui.print_error(f"File does not exist: {pack}")
        return 1

    result = WorldImporter.extract_campaign(pack)
    if result is None:
        ui.print_error(f"Could not extract {pack} — archive may be corrupt.")
        return 1

    world_name = result.get("world_name", "Imported World")
    ui.print_success(f"Imported campaign '{world_name}'")
    console.print(f"  world files: {result.get('worlds_dir')}")
    if result.get("save_path"):
        console.print(f"  save file:   {result['save_path']}")
    else:
        console.print(
            "  [dim]no save.json in archive — you'll start a new character[/dim]"
        )
    return 0


def _cmd_serve(args: list[str]) -> int:
    """Subcommand: rag-quest serve [--host HOST] [--port PORT].

    Launches the FastAPI web wrapper via uvicorn. Requires the
    optional `[web]` extras (fastapi + uvicorn) — install with
    `pip install -e '.[web]'`.
    """
    import argparse

    parser = argparse.ArgumentParser(prog="rag-quest serve", add_help=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    opts = parser.parse_args(args)

    from .web.app import run as run_web

    try:
        run_web(host=opts.host, port=opts.port)
    except ImportError as exc:
        ui.print_error(str(exc))
        return 1
    return 0


def _print_welcome_screen() -> None:
    """Print the welcome screen and main menu."""
    startup.print_welcome_screen()


def _show_start_menu() -> str:
    """Show the three start modes and return choice."""
    console.print("\n[bold cyan]How Would You Like to Start?[/bold cyan]\n")

    console.print("[bold cyan][1][/bold cyan] Fresh Adventure")
    console.print(
        "    Describe your world in a sentence and the AI will bring it to life."
    )
    console.print(
        "    [dim]Great for: Creative world-building, quick games, unique adventures[/dim]\n"
    )

    console.print("[bold cyan][2][/bold cyan] Quick Start — Choose a Template")
    console.print("    Pick from 4 pre-built worlds with established lore.")
    console.print("    [dim]Great for: Jump right in, no setup required[/dim]\n")
    console.print(
        "    [cyan]a)[/cyan] Classic Dungeon — Dark corridors, ancient traps, forgotten treasures"
    )
    console.print(
        "    [cyan]b)[/cyan] Enchanted Forest — Mystical creatures, fey courts, ancient magic"
    )
    console.print(
        "    [cyan]c)[/cyan] Port City — Maritime intrigue, merchant guilds, pirate threats"
    )
    console.print(
        "    [cyan]d)[/cyan] War-Torn Kingdom — Political conflict, siege warfare, divided loyalties\n"
    )

    console.print("[bold cyan][3][/bold cyan] Upload Lore")
    console.print("    Load a PDF, TXT, or Markdown file for the RAG knowledge base.")
    console.print(
        "    [dim]Great for: Published settings, custom lore, consistent world-building[/dim]\n"
    )

    console.print("[bold cyan][4][/bold cyan] Continue Saved Game")
    console.print("    Load a previously saved adventure.\n")

    console.print("[bold cyan][5][/bold cyan] Settings")
    console.print("    View and modify your configuration.\n")

    console.print("[bold cyan][6][/bold cyan] Quit\n")

    choice = Prompt.ask(
        "Choose [1-6]",
        choices=["1", "2", "3", "4", "5", "6"],
    )

    return choice


def _create_character_with_descriptions() -> dict:
    """Create character with race/class descriptions."""
    console.clear()
    console.print("\n[bold cyan]═══ Character Creation ═══[/bold cyan]\n")

    # Get valid name
    while True:
        name = Prompt.ask("\n[bold]Your character's name[/bold]").strip()
        if not name:
            console.print("[yellow]Name cannot be empty.[/yellow]")
            continue
        if len(name) > 50:
            console.print("[yellow]Name too long (max 50 characters).[/yellow]")
            continue
        break

    # Race selection with descriptions
    console.print("\n[bold cyan]Choose Your Race[/bold cyan]\n")
    console.print(
        "[bold cyan][1][/bold cyan] Human — Versatile and adaptable. +1 to all attributes."
    )
    console.print(
        "[bold cyan][2][/bold cyan] Elf — Graceful and perceptive. +2 DEX, +1 WIS."
    )
    console.print(
        "[bold cyan][3][/bold cyan] Dwarf — Tough and resilient. +2 CON, +1 STR."
    )
    console.print(
        "[bold cyan][4][/bold cyan] Halfling — Lucky and nimble. +2 DEX, +1 CHA."
    )
    console.print(
        "[bold cyan][5][/bold cyan] Orc — Powerful and fierce. +2 STR, +1 CON.\n"
    )

    races_map = {
        "1": "HUMAN",
        "2": "ELF",
        "3": "DWARF",
        "4": "HALFLING",
        "5": "ORC",
    }

    race_choice = Prompt.ask(
        "Choose [1-5]",
        choices=["1", "2", "3", "4", "5"],
        default="1",
    )
    race = races_map[race_choice]
    console.print(f"[green]✓ Race selected: {race}[/green]")

    # Class selection with descriptions and abilities
    console.print("\n[bold cyan]Choose Your Class[/bold cyan]\n")

    console.print(
        "[bold cyan][1][/bold cyan] Fighter — Master of weapons and armor. High HP, strong attacks."
    )
    console.print("     Abilities: Power Strike (L1), Shield Wall (L3), Cleave (L6)")

    console.print(
        "[bold cyan][2][/bold cyan] Mage — Wielder of arcane magic. Powerful spells, low HP."
    )
    console.print("     Abilities: Fireball (L1), Heal (L2), Arcane Shield (L4)")

    console.print(
        "[bold cyan][3][/bold cyan] Rogue — Stealthy and cunning. High damage from shadows."
    )
    console.print("     Abilities: Backstab (L1), Dodge (L3), Steal (L5)")

    console.print(
        "[bold cyan][4][/bold cyan] Ranger — Wilderness expert. Balanced combat and tracking."
    )
    console.print(
        "     Abilities: Arrow Volley (L1), Track (L3), Animal Companion (L6)"
    )

    console.print(
        "[bold cyan][5][/bold cyan] Cleric — Divine servant. Healing and holy magic."
    )
    console.print("     Abilities: Divine Heal (L1), Smite (L2), Bless (L4)\n")

    classes_map = {
        "1": "FIGHTER",
        "2": "MAGE",
        "3": "ROGUE",
        "4": "RANGER",
        "5": "CLERIC",
    }

    class_choice = Prompt.ask(
        "Choose [1-5]",
        choices=["1", "2", "3", "4", "5"],
        default="1",
    )
    character_class = classes_map[class_choice]
    console.print(f"[green]✓ Class selected: {character_class}[/green]")

    # Show confirmation
    console.print()
    confirm = Prompt.ask(
        f"\n[bold]Create {name}, a {race} {character_class}?[/bold]",
        choices=["y", "n"],
        default="y",
    )
    if confirm.lower() != "y":
        console.print("[yellow]Character creation cancelled. Starting over...[/yellow]")
        return _create_character_with_descriptions()  # Recursively restart

    return {
        "name": name,
        "race": race,
        "class": character_class,
        "background": None,
    }


def _main() -> None:
    """Main logic."""
    _print_welcome_screen()

    # Load or create configuration
    try:
        config_manager = config.ConfigManager()

        # Check if this is first run (no config file)
        if not config.CONFIG_FILE.exists():
            config_manager.setup_wizard()

        game_config = config_manager.config
    except RuntimeError as e:
        ui.print_error(str(e))
        sys.exit(1)

    # Show start menu
    start_choice = _show_start_menu()

    if start_choice == "5":
        # Settings menu
        config_manager.modify_settings_menu()
        return
    elif start_choice == "6":
        # Quit
        console.print("[cyan]Thanks for playing RAG-Quest![/cyan]")
        sys.exit(0)
    elif start_choice in ["1", "2", "3", "4"]:
        # Game start - handle each mode
        if start_choice == "4":
            console.print("[yellow]Continue Saved Game not yet implemented[/yellow]")
            console.print("[dim]For now, starting a Fresh Adventure instead...[/dim]")
            start_choice = "1"

        if start_choice == "1":
            # Fresh Adventure
            console.print("\n[cyan]Describe your world in a sentence or two.[/cyan]")
            console.print(
                "[dim]Examples: 'Dark medieval fantasy with dragon riders', 'Magical underwater kingdom', 'Post-apocalyptic desert'[/dim]"
            )
            world_desc = Prompt.ask("\n[bold]Your world[/bold]")

            # Create world from description
            world_name = Prompt.ask("World name", default="Generated World")
            world_setting = Prompt.ask("Setting", default=world_desc or "Fantasy")
            world_tone = Prompt.ask("Tone (Dark, Heroic, Whimsical)", default="Heroic")

            game_config["world"] = {
                "name": world_name,
                "setting": world_setting,
                "tone": world_tone,
                "starting_location": "A quaint tavern",
            }

        elif start_choice == "2":
            # Quick Start with templates
            console.print("\n[bold cyan]Choose a Template[/bold cyan]\n")
            console.print("[cyan]a)[/cyan] Classic Dungeon")
            console.print("[cyan]b)[/cyan] Enchanted Forest")
            console.print("[cyan]c)[/cyan] Port City")
            console.print("[cyan]d)[/cyan] War-Torn Kingdom\n")

            template_choice = Prompt.ask(
                "Choose [a-d]",
                choices=["a", "b", "c", "d"],
                default="a",
            )

            templates = {
                "a": {
                    "name": "Classic Dungeon",
                    "setting": "Ancient Dungeon",
                    "tone": "Dark",
                    "starting_location": "The entrance to a deep, dark dungeon",
                },
                "b": {
                    "name": "Enchanted Forest",
                    "setting": "Mystical Forest",
                    "tone": "Whimsical",
                    "starting_location": "A clearing in an ancient forest",
                },
                "c": {
                    "name": "Port City",
                    "setting": "Bustling Port City",
                    "tone": "Heroic",
                    "starting_location": "The docks of a busy trading port",
                },
                "d": {
                    "name": "War-Torn Kingdom",
                    "setting": "Divided Kingdom",
                    "tone": "Dark",
                    "starting_location": "A war-scarred village",
                },
            }

            template = templates[template_choice]
            game_config["world"] = {
                "name": template["name"],
                "setting": template["setting"],
                "tone": template["tone"],
                "starting_location": template["starting_location"],
            }

        elif start_choice == "3":
            # Upload Lore
            lore_path = Prompt.ask("Path to lore file or directory")

            world_name = Prompt.ask("World name")
            world_setting = Prompt.ask("World setting")
            world_tone = Prompt.ask("World tone (Dark, Heroic, Whimsical)")

            game_config["world"] = {
                "name": world_name,
                "setting": world_setting,
                "tone": world_tone,
                "starting_location": "A mysterious location",
                "lore_path": lore_path,
            }

        # Character creation
        game_config["character"] = _create_character_with_descriptions()

    # Load LLM provider
    try:
        llm_provider, llm_config = config.load_llm_provider(game_config)
        ui.print_success("LLM provider loaded!")

        # Run startup checks (e.g., verify Ollama is running)
        provider_type = game_config["llm"]["provider"]
        if provider_type == "ollama":
            base_url = game_config["llm"].get("base_url", "http://localhost:11434")
            startup.startup_checks(provider_type, base_url)
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
        world_rag = WorldRAG(
            world.name, llm_config, llm_provider, rag_profile=rag_profile
        )
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
    from .engine.achievements import AchievementManager
    from .engine.events import EventManager
    from .engine.inventory import Inventory
    from .engine.party import Party
    from .engine.quests import QuestLog
    from .engine.relationships import RelationshipManager

    inventory = Inventory()
    quest_log = QuestLog()
    party = Party()
    relationships = RelationshipManager()
    events = EventManager()
    achievements = AchievementManager()
    narrator = Narrator(llm_provider, world_rag, character, world, inventory, quest_log)

    # v0.6 Campaign Memory
    from .engine.encyclopedia import LoreEncyclopedia
    from .engine.notetaker import Notetaker
    from .engine.timeline import Timeline

    timeline = Timeline()
    try:
        notetaker = Notetaker(world_name=world.name, llm=llm_provider)
    except Exception:
        notetaker = None

    # Create game state
    game_state = GameState(
        character=character,
        world=world,
        inventory=inventory,
        quest_log=quest_log,
        narrator=narrator,
        world_rag=world_rag,
        llm=llm_provider,
        party=party,
        relationships=relationships,
        events=events,
        achievements=achievements,
        timeline=timeline,
        notetaker=notetaker,
    )
    game_state.encyclopedia = LoreEncyclopedia(game_state)

    # v0.7: Load modules.yaml if present. Checked in order:
    #   1. ./lore/modules.yaml (world-template authors)
    #   2. ~/.local/share/rag-quest/worlds/{name}/modules.yaml (shipped worlds)
    # Malformed manifests surface via ui.print_error — never abort the game.
    # Lore ingestion can take minutes on first boot — keep the user informed
    # via a Rich status spinner so it doesn't look like a silent hang.
    from .worlds.modules import ModuleManifestError, load_modules

    module_search_paths = [
        Path("lore"),
        Path.home() / ".local/share/rag-quest/worlds" / world.name,
    ]
    for mod_dir in module_search_paths:
        if not (mod_dir / "modules.yaml").exists():
            continue
        try:
            with console.status(
                f"[bold green]Loading modules from {mod_dir}/modules.yaml…[/bold green]"
            ):
                world.module_registry = load_modules(mod_dir, world_rag=world_rag)
            ui.print_success(
                f"Loaded {len(world.module_registry)} module(s) from {mod_dir}/modules.yaml"
            )
        except ModuleManifestError as e:
            ui.print_error(f"Could not load modules.yaml: {e}")
        break

    # Determine save path
    save_dir = Path.home() / ".local/share/rag-quest/saves"
    save_path = save_dir / f"{world.name}.json"

    # Run the game
    run_game(game_state, save_path)


if __name__ == "__main__":
    main()
