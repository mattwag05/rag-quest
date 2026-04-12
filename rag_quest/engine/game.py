"""Main game loop and state management."""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm

from ..knowledge import WorldRAG
from ..llm import BaseLLMProvider
from ..saves import SaveManager
from .. import ui
from .character import Character
from .inventory import Inventory
from .narrator import Narrator
from .quests import QuestLog
from .world import World
from .combat import CombatManager, CombatEncounter
from .encounters import EncounterGenerator
from .tts import TTSNarrator
from .party import Party
from .relationships import RelationshipManager
from .events import EventManager
from .achievements import AchievementManager
from .dungeon import DungeonGenerator


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
    party: Party
    relationships: RelationshipManager
    events: EventManager
    combat_manager: Optional[CombatManager] = None
    tts_narrator: Optional[TTSNarrator] = None
    achievements: Optional[AchievementManager] = None
    turn_number: int = 0
    playtime_seconds: float = 0.0

    def to_dict(self) -> dict:
        """Serialize game state."""
        return {
            "character": self.character.to_dict(),
            "world": self.world.to_dict(),
            "inventory": self.inventory.to_dict(),
            "quest_log": self.quest_log.to_dict(),
            "party": self.party.to_dict(),
            "relationships": self.relationships.to_dict(),
            "events": self.events.to_dict(),
            "achievements": self.achievements.to_dict() if self.achievements else {},
            "turn_number": self.turn_number,
            "playtime_seconds": self.playtime_seconds,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
        narrator: Narrator,
        world_rag: WorldRAG,
        llm: BaseLLMProvider,
        tts_enabled: bool = False,
    ) -> "GameState":
        """Deserialize game state."""
        character = Character.from_dict(data["character"])
        world = World.from_dict(data["world"])
        inventory = Inventory.from_dict(data["inventory"])
        quest_log = QuestLog.from_dict(data["quest_log"])
        party = Party.from_dict(data.get("party", {"members": [], "max_size": 4}))
        relationships = RelationshipManager.from_dict(data.get("relationships", {"relationships": {}, "factions": {}, "faction_reputation": {}}))
        events = EventManager.from_dict(data.get("events", {"active_events": [], "event_history": []}))
        achievements = AchievementManager.from_dict(data.get("achievements", {})) if data.get("achievements") else AchievementManager()
        
        combat_mgr = CombatManager(narrator)
        tts = TTSNarrator(enabled=tts_enabled) if tts_enabled else None

        return cls(
            character=character,
            world=world,
            inventory=inventory,
            quest_log=quest_log,
            narrator=narrator,
            world_rag=world_rag,
            llm=llm,
            party=party,
            relationships=relationships,
            events=events,
            achievements=achievements,
            combat_manager=combat_mgr,
            tts_narrator=tts,
            turn_number=data.get("turn_number", 0),
            playtime_seconds=data.get("playtime_seconds", 0.0),
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
                ui.print_info("[dim]Type an action like 'look around' or /help for commands[/dim]")
                continue

            # Handle special commands
            if player_input.startswith("/"):
                if not _handle_command(player_input, game_state, save_path):
                    break
                continue

            # Check for world events and advance turn
            game_state.turn_number += 1
            new_event = game_state.events.check_for_events(game_state.turn_number, event_chance=0.08)
            if new_event:
                ui.print_world_event(f"[bold cyan]WORLD EVENT:[/bold cyan] {new_event.name}\n{new_event.description}")
            
            # Expire old events
            expired = game_state.events.expire_events()
            for event_name in expired:
                ui.print_world_event(f"[cyan]Event ended:[/cyan] {event_name}")
            
            # Check for party loyalty departures
            departing = game_state.party.check_loyalty_departures()
            for member_name in departing:
                ui.print_warning(f"{member_name} has left the party due to low loyalty!")

            # Process action through narrator with error recovery
            try:
                with console.status("[bold green]The Dungeon Master considers your action...[/bold green]"):
                    response = game_state.narrator.process_action(player_input)
                    errors_in_row = 0  # Reset error counter on success
            except Exception as e:
                errors_in_row += 1
                error_msg = str(e).lower()
                
                # Provide helpful, user-friendly error messages
                if "timeout" in error_msg or "connection" in error_msg:
                    ui.print_error("The LLM is taking too long. Try again or check your connection.")
                elif "ollama" in error_msg or "llm" in error_msg:
                    ui.print_error("Problem with the AI narrator. Make sure Ollama is running.")
                elif "rag" in error_msg or "knowledge" in error_msg:
                    ui.print_error("Issue with the world knowledge system. Try a simpler action.")
                else:
                    ui.print_error(f"The Dungeon Master stumbles: {type(e).__name__}")
                
                # If too many errors in a row, suggest exiting
                if errors_in_row >= max_errors_in_row:
                    ui.print_error("Too many errors. Consider saving with /save and restarting RAG-Quest.")
                    response = (
                        "The world seems unstable. You should find a safe place to rest "
                        "before continuing your adventure."
                    )
                else:
                    continue

            # Display response
            ui.print_narrator_response(response)
            
            # Check for new achievements
            if game_state.achievements:
                new_achievements = game_state.achievements.check_achievements(game_state.to_dict())
                for achievement in new_achievements:
                    ui.print_achievement_unlocked(achievement.name, achievement.icon)

            # Auto-save frequently to protect progress
            action_count += 1
            if save_path:
                # Save every 5 actions
                if action_count % 5 == 0:
                    try:
                        _save_game(game_state, save_path)
                        console.print("[dim]✓ Progress saved[/dim]")
                    except Exception as e:
                        console.print(f"[yellow]⚠ Could not auto-save: {e}[/yellow]")

    except KeyboardInterrupt:
        # Graceful exit with save prompt
        console.print("\n[yellow][bold]Exiting RAG-Quest[/bold][/yellow]")
        if save_path and Confirm.ask("Save your progress before quitting?", default=True):
            try:
                _save_game(game_state, save_path)
                console.print("[green]✓ Game saved![/green]")
            except Exception as e:
                console.print(f"[yellow]Could not save: {e}[/yellow]")
        console.print("[cyan]Thanks for playing, adventurer. See you next time![/cyan]\n")
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

    elif cmd == "/map" or cmd == "/world":
        ui.print_world_context(game_state.world)

    elif cmd == "/status" or cmd == "/s":
        ui.print_character_status(game_state.character)

    elif cmd == "/save":
        if save_path:
            try:
                _save_game(game_state, save_path)
                ui.print_save_confirmation(
                    save_path.name,
                    game_state.character.name,
                    game_state.world.name
                )
            except Exception as e:
                ui.print_error(f"Could not save: {e}")
        else:
            ui.print_warning("No save location specified.")

    elif cmd == "/abilities":
        abilities_str = "\n".join(game_state.character.get_abilities()) or "No abilities unlocked yet"
        console.print(Panel(abilities_str, title="Abilities", border_style="yellow"))
    
    elif cmd == "/stats":
        ui.print_character_status(game_state.character)
    
    elif cmd == "/equipment":
        equipment = game_state.character.equipment
        eq_str = f"Weapon: {equipment.weapon or 'None'}\n"
        eq_str += f"Armor: {equipment.armor or 'None'}\n"
        eq_str += f"Accessory: {equipment.accessory or 'None'}"
        console.print(Panel(eq_str, title="Equipment", border_style="cyan"))
    
    elif cmd == "/voice":
        if game_state.tts_narrator:
            game_state.tts_narrator.toggle()
            state = "enabled" if game_state.tts_narrator.is_enabled() else "disabled"
            ui.print_success(f"Text-to-speech {state}!")
        else:
            ui.print_warning("TTS not available in this game.")
    
    elif cmd == "/party" or cmd == "/p":
        console.print(Panel(game_state.party.get_party_status(), title="Party Status", border_style="magenta"))

    elif cmd == "/relationships" or cmd == "/rel":
        console.print(Panel(game_state.relationships.relationship_summary(), title="Relationships", border_style="green"))

    elif cmd == "/factions" or cmd == "/f":
        if not game_state.relationships.factions:
            console.print("[yellow]No factions discovered yet.[/yellow]")
        else:
            faction_text = "\n".join([
                f"[{faction.color}]{faction.name}[/{faction.color}]: {faction.description}"
                for faction in game_state.relationships.factions.values()
            ])
            console.print(Panel(faction_text, title="Factions", border_style="cyan"))

    elif cmd == "/recruit" and len(parts) > 1:
        npc_name = " ".join(parts[1:])
        rel = game_state.relationships.get_or_create_relationship(npc_name)
        if rel.can_recruit():
            from .party import PartyMember
            member = PartyMember(
                name=npc_name,
                race="Unknown",
                character_class="Unknown",
                backstory=f"Recruited from adventure"
            )
            if game_state.party.add_member(member):
                console.print(f"[green]{npc_name} has joined your party![/green]")
            else:
                console.print("[yellow]Your party is at maximum size.[/yellow]")
        else:
            console.print(f"[red]{npc_name} is not interested in joining your party.[/red]")

    elif cmd == "/dismiss" and len(parts) > 1:
        npc_name = " ".join(parts[1:])
        if game_state.party.remove_member(npc_name):
            console.print(f"[yellow]{npc_name} has left your party.[/yellow]")
        else:
            console.print(f"[red]{npc_name} is not in your party.[/red]")

    elif cmd == "/events":
        events_list = game_state.events.get_active_event_descriptions()
        if events_list:
            events_text = "\n".join(events_list)
            console.print(Panel(events_text, title="Active World Events", border_style="red"))
        else:
            console.print("[yellow]No active world events.[/yellow]")

    elif cmd == "/achievements":
        if game_state.achievements:
            unlocked = game_state.achievements.get_unlocked()
            if unlocked:
                ach_text = "\n".join([f"{a.icon} {a.name}: {a.description}" for a in unlocked])
                console.print(Panel(ach_text, title="Achievements", border_style="blue"))
            else:
                console.print("[yellow]No achievements unlocked yet.[/yellow]")
        else:
            console.print("[yellow]Achievements not enabled.[/yellow]")

    elif cmd == "/dungeon":
        # Start a procedural dungeon crawl
        dungeon = DungeonGenerator.generate(depth=5, difficulty="normal")
        room = dungeon.enter()
        console.print(Panel(dungeon.get_map_ascii(), title="Dungeon Map", border_style="red"))
        if room:
            console.print(f"\n[bold]You enter a {room.room_type.value}:[/bold] {room.description}")
            if room.enemies:
                console.print(f"[red]Enemies:[/red] {', '.join(room.enemies)}")
            if room.items:
                console.print(f"[green]Items:[/green] {', '.join(room.items)}")

    elif cmd == "/config" or cmd == "/settings":
        # In-game settings menu
        from ..config import ConfigManager
        config_manager = ConfigManager()
        config_manager.modify_settings_menu()

    elif cmd == "/help" or cmd == "/h":
        ui.print_help()

    elif cmd == "/tutorial":
        from ..tutorial import run_interactive_tutorial
        run_interactive_tutorial()

    elif cmd == "/new":
        if ui.get_yes_no_confirmation("[yellow]Start a new game? Current progress will be saved.[/yellow]"):
            ui.print_success("Restart your game by quitting and running RAG-Quest again!")
        return True

    elif cmd == "/quit" or cmd == "/exit":
        if save_path:
            if ui.get_yes_no_confirmation("[yellow]Save before quitting?[/yellow]"):
                _save_game(game_state, save_path)
        return False

    else:
        ui.print_unknown_command(cmd)

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
