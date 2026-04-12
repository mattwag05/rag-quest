"""Main game loop and state management."""

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm

from .. import ui
from ..knowledge import WorldRAG
from ..llm import BaseLLMProvider
from ..saves import SaveManager
from ..worlds.modules import ModuleStatus
from .achievements import AchievementManager
from .character import Character
from .combat import CombatEncounter, CombatManager
from .dungeon import DungeonGenerator
from .encounters import EncounterGenerator
from .encyclopedia import CATEGORIES as LORE_CATEGORIES
from .encyclopedia import LoreEncyclopedia
from .events import EventManager
from .inventory import Inventory
from .narrator import Narrator
from .notetaker import Notetaker
from .party import Party
from .quests import QuestLog
from .relationships import RelationshipManager
from .timeline import Bookmark, Timeline
from .tts import TTSNarrator
from .world import World

SAVE_FORMAT_VERSION = 3


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
    # v0.6 Campaign Memory — additive, new-save-only. Old v1 saves load with
    # empty timeline and notetaker cursor; notes/lore only populate from here on.
    timeline: Timeline = field(default_factory=Timeline)
    notetaker: Optional[Notetaker] = None
    encyclopedia: Optional[LoreEncyclopedia] = None
    # v0.7 (save v3): bases and modules live on `World`, so they round-trip via
    # `World.to_dict/from_dict`. v2 saves load with empty collections — same
    # clean-break policy as v0.6: new features on new saves only, no migration.

    def to_dict(self) -> dict:
        """Serialize game state."""
        return {
            "save_version": SAVE_FORMAT_VERSION,
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
            # v0.6 memory layer — the notes sidecar lives at ~/.local/share/rag-quest/notes/
            # so we only persist a pointer (world name) here.
            "timeline": self.timeline.to_dict(),
            "notes_world": self.notetaker.world_name if self.notetaker else None,
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
        relationships = RelationshipManager.from_dict(
            data.get(
                "relationships",
                {"relationships": {}, "factions": {}, "faction_reputation": {}},
            )
        )
        events = EventManager.from_dict(
            data.get("events", {"active_events": [], "event_history": []})
        )
        achievements = (
            AchievementManager.from_dict(data.get("achievements", {}))
            if data.get("achievements")
            else AchievementManager()
        )

        combat_mgr = CombatManager(narrator)
        tts = TTSNarrator(enabled=tts_enabled) if tts_enabled else None

        # v0.6: safe-default hydration for save v2 fields. Old v1 saves omit these
        # and load into empty containers — no retroactive migration.
        try:
            timeline = Timeline.from_dict(data.get("timeline"))
        except Exception:
            timeline = Timeline()

        notes_world = data.get("notes_world") or world.name
        try:
            notetaker = Notetaker(world_name=notes_world, llm=llm)
        except Exception:
            notetaker = None

        gs = cls(
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
            timeline=timeline,
            notetaker=notetaker,
        )
        gs.encyclopedia = LoreEncyclopedia(gs)
        return gs


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
                ui.print_info(
                    "[dim]Type an action like 'look around' or /help for commands[/dim]"
                )
                continue

            # Handle special commands
            if player_input.startswith("/"):
                if not _handle_command(player_input, game_state, save_path):
                    break
                continue

            # Check for world events and advance turn
            game_state.turn_number += 1
            new_event = game_state.events.check_for_events(
                game_state.turn_number, event_chance=0.08
            )
            if new_event:
                ui.print_world_event(
                    f"[bold cyan]WORLD EVENT:[/bold cyan] {new_event.name}\n{new_event.description}"
                )

            # Expire old events
            expired = game_state.events.expire_events()
            for event_name in expired:
                ui.print_world_event(f"[cyan]Event ended:[/cyan] {event_name}")

            # Check for party loyalty departures
            departing = game_state.party.check_loyalty_departures()
            for member_name in departing:
                ui.print_warning(
                    f"{member_name} has left the party due to low loyalty!"
                )

            # Process action through narrator with error recovery
            try:
                with console.status(
                    "[bold green]The Dungeon Master considers your action...[/bold green]"
                ):
                    response = game_state.narrator.process_action(player_input)
                    errors_in_row = 0  # Reset error counter on success
            except Exception as e:
                errors_in_row += 1
                error_msg = str(e).lower()

                # Provide helpful, user-friendly error messages
                if "timeout" in error_msg or "connection" in error_msg:
                    ui.print_error(
                        "The LLM is taking too long. Try again or check your connection."
                    )
                elif "ollama" in error_msg or "llm" in error_msg:
                    ui.print_error(
                        "Problem with the AI narrator. Make sure Ollama is running."
                    )
                elif "rag" in error_msg or "knowledge" in error_msg:
                    ui.print_error(
                        "Issue with the world knowledge system. Try a simpler action."
                    )
                else:
                    ui.print_error(f"The Dungeon Master stumbles: {type(e).__name__}")

                # If too many errors in a row, suggest exiting
                if errors_in_row >= max_errors_in_row:
                    ui.print_error(
                        "Too many errors. Consider saving with /save and restarting RAG-Quest."
                    )
                    response = (
                        "The world seems unstable. You should find a safe place to rest "
                        "before continuing your adventure."
                    )
                else:
                    continue

            # Display response
            ui.print_narrator_response(response)

            # v0.6: record a structured timeline entry from the just-applied StateChange.
            try:
                change = getattr(game_state.narrator, "last_change", None)
                if change is not None:
                    game_state.timeline.record_from_state_change(
                        turn=game_state.turn_number,
                        change=change,
                        player_input=player_input,
                        location=game_state.character.location or "",
                    )
            except Exception:
                pass  # Timeline is additive — never block the game loop.

            # v0.7: re-evaluate module gating — quest status may have changed.
            try:
                transitioned = game_state.world.module_registry.reevaluate(
                    game_state.quest_log
                )
                for module in transitioned:
                    if module.status == ModuleStatus.AVAILABLE:
                        ui.print_info(
                            f"[bold cyan]Module unlocked:[/bold cyan] {module.title}"
                        )
                    elif module.status == ModuleStatus.COMPLETED:
                        ui.print_success(f"Module completed: {module.title}")
            except Exception:
                pass  # Module gating is additive — never block the game loop.

            # Check for new achievements
            if game_state.achievements:
                new_achievements = game_state.achievements.check_achievements(
                    game_state.to_dict()
                )
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
        if save_path and Confirm.ask(
            "Save your progress before quitting?", default=True
        ):
            try:
                _save_game(game_state, save_path)
                console.print("[green]✓ Game saved![/green]")
            except Exception as e:
                console.print(f"[yellow]Could not save: {e}[/yellow]")
        console.print(
            "[cyan]Thanks for playing, adventurer. See you next time![/cyan]\n"
        )
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
        description = game_state.world_rag.query_world(context_query, param="hybrid")
        console.print(
            Panel(
                description or "You see nothing special here.",
                title=game_state.character.location,
            )
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
                    save_path.name, game_state.character.name, game_state.world.name
                )
            except Exception as e:
                ui.print_error(f"Could not save: {e}")
        else:
            ui.print_warning("No save location specified.")

    elif cmd == "/abilities":
        abilities_str = (
            "\n".join(game_state.character.get_abilities())
            or "No abilities unlocked yet"
        )
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
        console.print(
            Panel(
                game_state.party.get_party_status(),
                title="Party Status",
                border_style="magenta",
            )
        )

    elif cmd == "/relationships" or cmd == "/rel":
        console.print(
            Panel(
                game_state.relationships.relationship_summary(),
                title="Relationships",
                border_style="green",
            )
        )

    elif cmd == "/factions" or cmd == "/f":
        if not game_state.relationships.factions:
            console.print("[yellow]No factions discovered yet.[/yellow]")
        else:
            faction_text = "\n".join(
                [
                    f"[{faction.color}]{faction.name}[/{faction.color}]: {faction.description}"
                    for faction in game_state.relationships.factions.values()
                ]
            )
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
                backstory=f"Recruited from adventure",
            )
            if game_state.party.add_member(member):
                console.print(f"[green]{npc_name} has joined your party![/green]")
            else:
                console.print("[yellow]Your party is at maximum size.[/yellow]")
        else:
            console.print(
                f"[red]{npc_name} is not interested in joining your party.[/red]"
            )

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
            console.print(
                Panel(events_text, title="Active World Events", border_style="red")
            )
        else:
            console.print("[yellow]No active world events.[/yellow]")

    elif cmd == "/achievements":
        if game_state.achievements:
            unlocked = game_state.achievements.get_unlocked()
            if unlocked:
                ach_text = "\n".join(
                    [f"{a.icon} {a.name}: {a.description}" for a in unlocked]
                )
                console.print(
                    Panel(ach_text, title="Achievements", border_style="blue")
                )
            else:
                console.print("[yellow]No achievements unlocked yet.[/yellow]")
        else:
            console.print("[yellow]Achievements not enabled.[/yellow]")

    elif cmd == "/dungeon":
        # Start a procedural dungeon crawl
        dungeon = DungeonGenerator.generate(depth=5, difficulty="normal")
        room = dungeon.enter()
        console.print(
            Panel(dungeon.get_map_ascii(), title="Dungeon Map", border_style="red")
        )
        if room:
            console.print(
                f"\n[bold]You enter a {room.room_type.value}:[/bold] {room.description}"
            )
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
        if ui.get_yes_no_confirmation(
            "[yellow]Start a new game? Current progress will be saved.[/yellow]"
        ):
            ui.print_success(
                "Restart your game by quitting and running RAG-Quest again!"
            )
        return True

    elif cmd == "/quit" or cmd == "/exit":
        if save_path:
            if ui.get_yes_no_confirmation("[yellow]Save before quitting?[/yellow]"):
                _save_game(game_state, save_path)
        return False

    # ------------------------------------------------------------------
    # v0.6 Campaign Memory commands: /timeline, /bookmark, /bookmarks,
    # /notes, /canonize, /lore
    # ------------------------------------------------------------------
    elif cmd == "/timeline" or cmd == "/t":
        _cmd_timeline(parts, game_state)

    elif cmd == "/bookmark" or cmd == "/bm":
        _cmd_bookmark(parts, game_state)

    elif cmd == "/bookmarks":
        _cmd_list_bookmarks(game_state)

    elif cmd == "/notes" or cmd == "/n":
        _cmd_notes(parts, game_state)

    elif cmd == "/canonize":
        _cmd_canonize(parts, game_state)

    elif cmd == "/lore" or cmd == "/l":
        _cmd_lore(parts, game_state)

    # ------------------------------------------------------------------
    # v0.7 Hub Bases: /base, /base claim [name]
    # ------------------------------------------------------------------
    elif cmd == "/base":
        _cmd_base(parts, game_state)

    elif cmd == "/modules":
        _cmd_modules(parts, game_state)

    else:
        ui.print_unknown_command(cmd)

    return True


# =====================================================================
# v0.6 Campaign Memory command handlers
# =====================================================================


def _cmd_timeline(parts: list, game_state: GameState) -> None:
    """Render the timeline log with optional type filter."""
    filter_type = parts[1].lower() if len(parts) > 1 else "all"
    events = game_state.timeline.get_events(filter_type=filter_type, limit=50)
    if not events:
        console.print(
            f"[yellow]No timeline events yet (filter: {filter_type}).[/yellow]"
        )
        return

    from rich.table import Table

    table = Table(
        title=f"Campaign Timeline ({filter_type})",
        border_style="blue",
        show_lines=False,
    )
    table.add_column("Turn", style="dim", width=5)
    table.add_column("Type", style="cyan", width=10)
    table.add_column("Summary", style="white")
    for ev in events:
        table.add_row(str(ev.turn), ev.type, ev.summary)
    console.print(table)


def _cmd_bookmark(parts: list, game_state: GameState) -> None:
    """Bookmark the current turn's full narrator prose."""
    from datetime import datetime as _dt

    note = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
    prose = getattr(game_state.narrator, "last_response", "") or ""
    if not prose:
        ui.print_warning("Nothing to bookmark yet — take at least one action first.")
        return
    bm = Bookmark(
        turn=game_state.turn_number,
        timestamp=_dt.now().isoformat(timespec="seconds"),
        note=note,
        player_input=getattr(game_state.narrator, "last_player_input", "") or "",
        narrator_prose=prose,
        location=game_state.character.location or "",
    )
    game_state.timeline.add_bookmark(bm)
    tag = f": {note}" if note else ""
    ui.print_success(f"★ Bookmarked turn {bm.turn}{tag}")


def _cmd_list_bookmarks(game_state: GameState) -> None:
    """List saved bookmarks."""
    bookmarks = game_state.timeline.bookmarks
    if not bookmarks:
        console.print(
            "[yellow]No bookmarks saved yet. Use /bookmark to save a highlight.[/yellow]"
        )
        return
    for bm in bookmarks[-10:]:
        header = f"[bold]Turn {bm.turn}[/bold] · {bm.location or 'unknown location'}"
        if bm.note:
            header += f" · [cyan]{bm.note}[/cyan]"
        console.print(Panel(bm.narrator_prose, title=header, border_style="magenta"))


def _cmd_notes(parts: list, game_state: GameState) -> None:
    """Show the notetaker summary or trigger a manual refresh."""
    if game_state.notetaker is None:
        ui.print_warning("Notetaker not available in this session.")
        return

    if len(parts) > 1 and parts[1].lower() in ("refresh", "now", "update"):
        ui.print_info("Refreshing notes…")
        entry = game_state.notetaker.refresh(
            current_turn=game_state.turn_number,
            conversation_history=game_state.narrator.get_conversation_history(),
            timeline_events=game_state.timeline.events,
        )
        if entry is None:
            ui.print_warning("Nothing new since last refresh.")
            return

    text = game_state.notetaker.format_latest(count=3)
    console.print(Panel(text, title="Campaign Notes", border_style="green"))


def _cmd_canonize(parts: list, game_state: GameState) -> None:
    """Promote pending notes into LightRAG."""
    if game_state.notetaker is None:
        ui.print_warning("Notetaker not available in this session.")
        return
    pending = game_state.notetaker.pending_for_canonization()
    if not pending:
        ui.print_info("No pending notes to canonize. Try /notes refresh first.")
        return

    from rich.table import Table

    table = Table(title="Pending Notes (not yet in world lore)", border_style="yellow")
    table.add_column("#", width=3)
    table.add_column("Turns", width=10)
    table.add_column("Summary")
    for i, entry in enumerate(pending, 1):
        table.add_row(str(i), entry.turn_range, entry.session_summary[:80])
    console.print(table)

    if len(parts) > 1:
        target = parts[1]
        if target.lower() == "all":
            promoted = 0
            for _ in range(len(pending)):
                if game_state.notetaker.canonize_entry(0, game_state.world_rag):
                    promoted += 1
            ui.print_success(f"Canonized {promoted} note(s) into world lore.")
            return
        try:
            idx = int(target) - 1
        except ValueError:
            ui.print_warning("Usage: /canonize [number|all]")
            return
        if game_state.notetaker.canonize_entry(idx, game_state.world_rag):
            ui.print_success(f"Canonized note #{target} into world lore.")
        else:
            ui.print_warning("Could not canonize that entry.")
    else:
        console.print("[dim]Use /canonize N to promote one, or /canonize all.[/dim]")


def _cmd_lore(parts: list, game_state: GameState) -> None:
    """Browse the lore encyclopedia."""
    if game_state.encyclopedia is None:
        game_state.encyclopedia = LoreEncyclopedia(game_state)

    enc = game_state.encyclopedia
    sub = parts[1].lower() if len(parts) > 1 else None

    if sub is None:
        # Overview
        from rich.table import Table

        table = Table(title="Lore Encyclopedia", border_style="cyan")
        table.add_column("Category")
        table.add_column("Count", justify="right")
        for cat, count in enc.categories_with_counts():
            table.add_row(cat, str(count))
        console.print(table)
        console.print(
            "[dim]Use /lore <category> to browse, or /lore <category> <name> for details.[/dim]"
        )
        return

    if sub not in LORE_CATEGORIES:
        ui.print_warning(
            f"Unknown category '{sub}'. Valid: {', '.join(LORE_CATEGORIES)}"
        )
        return

    if len(parts) >= 3:
        query_name = " ".join(parts[2:]).lower()
        entries = [e for e in enc.list_entries(sub) if query_name in e.name.lower()]
        if not entries:
            ui.print_warning(f"No {sub} entry matching '{query_name}'.")
            return
        entry = entries[0]
        with console.status("[bold green]Consulting world lore…[/bold green]"):
            detail = enc.detail(entry)
        console.print(
            Panel(detail, title=f"{entry.category}: {entry.name}", border_style="cyan")
        )
        return

    # Category listing
    entries = enc.list_entries(sub)
    if not entries:
        console.print(f"[yellow]No {sub} known yet.[/yellow]")
        return
    from rich.table import Table

    table = Table(title=f"Lore — {sub}", border_style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Summary")
    for entry in entries:
        table.add_row(entry.name, entry.summary or "")
    console.print(table)
    console.print(f"[dim]Use /lore {sub} <name> for a detailed RAG lookup.[/dim]")


def _cmd_base(parts: list, game_state: GameState) -> None:
    """Manage hub bases.

    Usage:
      /base                         — list all claimed bases
      /base claim [name]            — claim the current location as a base
      /base here                    — open the menu for the base at current location
      /base station <npc> [as <service>]
                                    — station an NPC (optionally as smith/healer/...)
      /base talk <npc> <message>    — one-shot scoped conversation with a stationed NPC
      /base deposit <item> [qty]    — move an item from player inventory to base storage
      /base withdraw <item> [qty]   — pull an item from base storage back to inventory
      /base storage                 — show base storage contents
    """
    sub = parts[1].lower() if len(parts) > 1 else None
    world = game_state.world
    current_location = (game_state.character.location or "").strip()

    if sub == "claim":
        supplied_name = " ".join(parts[2:]).strip() if len(parts) > 2 else ""
        base = world.claim_base_at(current_location, name=supplied_name)
        if base is not None:
            ui.print_success(
                f"Claimed {base.name} at {base.location_ref} as your base."
            )
        elif not current_location:
            ui.print_warning("You have no known location to claim yet.")
        else:
            ui.print_warning(f"A base already exists at {current_location}.")
        return

    # All remaining subcommands operate on the base at the current location.
    base_here = next(
        (b for b in world.bases if b.location_ref == current_location), None
    )

    if sub == "here":
        if base_here is None:
            ui.print_warning(
                f"No base at {current_location or 'your current location'}. "
                "Use /base claim [name] first."
            )
            return
        _render_base_menu(base_here)
        return

    if sub == "station":
        if base_here is None:
            ui.print_warning(
                "No base at your current location — nothing to station at."
            )
            return
        _cmd_base_station(parts[2:], base_here)
        return

    if sub == "talk":
        if base_here is None:
            ui.print_warning("No base at your current location.")
            return
        _cmd_base_talk(parts[2:], base_here, game_state)
        return

    if sub in ("deposit", "withdraw"):
        if base_here is None:
            ui.print_warning("No base at your current location.")
            return
        _cmd_base_storage_move(sub, parts[2:], base_here, game_state)
        return

    if sub == "storage":
        if base_here is None:
            ui.print_warning("No base at your current location.")
            return
        console.print(
            Panel(
                base_here.storage.list_items(),
                title=f"{base_here.name} — Storage",
                border_style="magenta",
            )
        )
        return

    # No subcommand: list all bases.
    if not world.bases:
        console.print(
            "[yellow]You have no bases yet. Use /base claim [name] at a location "
            "you'd like to make your own.[/yellow]"
        )
        return

    from rich.table import Table

    table = Table(title="Your Bases", border_style="magenta")
    table.add_column("Name", style="bold")
    table.add_column("Location")
    table.add_column("Services")
    table.add_column("Storage", justify="right")
    for base in world.bases:
        services = ", ".join(base.services) if base.services else "—"
        storage_count = len(base.storage.items)
        table.add_row(base.name, base.location_ref, services, str(storage_count))
    console.print(table)


def _render_base_menu(base) -> None:
    """Rich panel listing stationed NPCs grouped by service + storage summary."""
    from rich.table import Table

    grouped = base.npcs_by_service()
    if not grouped:
        roster_text = (
            "[dim]No NPCs stationed. Use /base station <npc> [as <service>].[/dim]"
        )
    else:
        lines = []
        for service in sorted(grouped.keys()):
            label = service or "unassigned"
            names = ", ".join(grouped[service])
            lines.append(f"[bold cyan]{label}[/bold cyan]: {names}")
        roster_text = "\n".join(lines)

    storage_count = len(base.storage.items)
    storage_weight = base.storage.get_total_weight()
    services_text = ", ".join(base.services) if base.services else "none"
    upgrades_text = (
        ", ".join(f"{k}={v}" for k, v in base.upgrades.items())
        if base.upgrades
        else "none"
    )

    body = (
        f"[bold]Location:[/bold] {base.location_ref}\n"
        f"[bold]Services:[/bold] {services_text}\n"
        f"[bold]Upgrades:[/bold] {upgrades_text}\n"
        f"[bold]Storage:[/bold] {storage_count} item(s), "
        f"{storage_weight:.1f} lbs\n\n"
        f"[bold]Stationed NPCs[/bold]\n{roster_text}"
    )
    console.print(Panel(body, title=base.name, border_style="magenta"))


def _cmd_base_station(args: list, base) -> None:
    """/base station <npc> [as <service>]."""
    if not args:
        ui.print_warning("Usage: /base station <npc> [as <service>]")
        return
    if "as" in args:
        idx = args.index("as")
        npc_name = " ".join(args[:idx]).strip()
        service = " ".join(args[idx + 1 :]).strip()
    else:
        npc_name = " ".join(args).strip()
        service = ""
    if not npc_name:
        ui.print_warning("Usage: /base station <npc> [as <service>]")
        return

    added = base.station_npc(npc_name, service=service)
    role = f" as {service}" if service else ""
    if added:
        ui.print_success(f"{npc_name} is now stationed at {base.name}{role}.")
    elif service:
        ui.print_success(f"{npc_name}'s role updated to {service}.")
    else:
        ui.print_warning(f"{npc_name} is already stationed at {base.name}.")


def _cmd_base_talk(args: list, base, game_state: GameState) -> None:
    """/base talk <npc> <message> — one-shot scoped conversation.

    Sets `narrator.service_context` to the build_service_prompt_addendum()
    string, runs a single `process_action`, then clears the addendum.
    Responses feed back through the state_parser as usual.
    """
    from .bases import build_service_prompt_addendum

    if len(args) < 2:
        ui.print_warning("Usage: /base talk <npc> <message>")
        return

    # Find the longest prefix of args that matches a stationed NPC name.
    npc_name = None
    message = ""
    for i in range(len(args), 0, -1):
        candidate = " ".join(args[:i])
        if candidate in base.stationed_npcs:
            npc_name = candidate
            message = " ".join(args[i:]).strip()
            break
    if npc_name is None:
        # Fall back to single-token match.
        npc_name = args[0]
        if npc_name not in base.stationed_npcs:
            ui.print_warning(
                f"{npc_name} is not stationed at {base.name}. "
                f"Try /base here to see who is."
            )
            return
        message = " ".join(args[1:]).strip()

    if not message:
        ui.print_warning("Usage: /base talk <npc> <message>")
        return

    addendum = build_service_prompt_addendum(base, npc_name, message)
    narrator = game_state.narrator
    previous = getattr(narrator, "service_context", "")
    narrator.service_context = addendum
    try:
        response = narrator.process_action(message)
    finally:
        narrator.service_context = previous
    ui.print_narrator_response(response)


def _cmd_base_storage_move(
    direction: str, args: list, base, game_state: GameState
) -> None:
    """/base deposit <item> [qty] and /base withdraw <item> [qty]."""
    if not args:
        ui.print_warning(f"Usage: /base {direction} <item> [quantity]")
        return
    # Trailing integer is quantity; otherwise default to 1.
    qty = 1
    if args[-1].isdigit():
        qty = int(args[-1])
        item_name = " ".join(args[:-1]).strip()
    else:
        item_name = " ".join(args).strip()
    if not item_name:
        ui.print_warning(f"Usage: /base {direction} <item> [quantity]")
        return

    src, dst = (
        (game_state.inventory, base.storage)
        if direction == "deposit"
        else (base.storage, game_state.inventory)
    )

    item = src.get_item(item_name)
    if item is None:
        ui.print_warning(
            f"{item_name} not found in {'your inventory' if direction == 'deposit' else base.name + ' storage'}."
        )
        return
    qty = min(qty, item.quantity)

    ok = dst.add_item(
        name=item.name,
        description=item.description,
        quantity=qty,
        weight=item.weight,
        rarity=item.rarity,
    )
    if not ok:
        ui.print_warning(f"Destination is full — {item_name} didn't fit.")
        return
    src.remove_item(item.name, quantity=qty)
    verb = "deposited" if direction == "deposit" else "withdrew"
    ui.print_success(f"{verb.capitalize()} {qty}x {item.name}.")


def _cmd_modules(parts: list, game_state: GameState) -> None:
    """List modules declared for this world, grouped by lifecycle status."""
    registry = game_state.world.module_registry
    if len(registry) == 0:
        console.print(
            "[yellow]This world has no modules.yaml manifest. Create one "
            "at the world directory root to declare adventure modules.[/yellow]"
        )
        return

    from rich.table import Table

    table = Table(title="Adventure Modules", border_style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Entry Location")
    table.add_column("Unlocks On")

    status_rank = {
        ModuleStatus.ACTIVE: 0,
        ModuleStatus.AVAILABLE: 1,
        ModuleStatus.LOCKED: 2,
        ModuleStatus.COMPLETED: 3,
    }
    for module in sorted(registry.all(), key=lambda m: status_rank[m.status]):
        unlock_display = (
            ", ".join(module.unlock_when_quests_completed)
            if module.unlock_when_quests_completed
            else "—"
        )
        table.add_row(
            module.status.value,
            module.id,
            module.title,
            module.entry_location,
            unlock_display,
        )
    console.print(table)


def _print_banner(world: World) -> None:
    """Print game banner."""
    banner = f"""
██████╗   █████╗  ██████╗       ██████╗ ██╗   ██╗███████╗███████╗████████╗
██╔══██╗ ██╔══██╗██╔════╝       ██╔═══██╗██║   ██║██╔════╝██╔════╝╚══██╔══╝
██████╔╝ ███████║██║  ███╗█████╗██║   ██║██║   ██║█████╗  ███████╗   ██║
██╔══██╗ ██╔══██║██║   ██║╚════╝██║▄▄ ██║██║   ██║██╔══╝  ╚════██║   ██║
██║  ██║ ██║  ██║╚██████╔╝      ╚██████╔╝╚██████╔╝███████╗███████║   ██║
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝        ╚══▀▀═══╝ ╚═════╝ ╚══════╝╚══════╝   ╚═╝
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
    """Save game state to file.

    v0.6: triggers an incremental Notetaker refresh (if enabled) before writing,
    so the JSON sidecar stays close to the save file the player just created.
    """
    # Auto-refresh notetaker summary on save events (unless disabled via config).
    try:
        if game_state.notetaker is not None:
            from ..config import ConfigManager

            auto_summary = True
            try:
                cfg = ConfigManager()
                auto_summary = bool(cfg.get("notetaker.auto_summary", True))
            except Exception:
                pass
            if auto_summary and game_state.notetaker.needs_refresh(
                game_state.turn_number
            ):
                game_state.notetaker.refresh(
                    current_turn=game_state.turn_number,
                    conversation_history=game_state.narrator.get_conversation_history(),
                    timeline_events=game_state.timeline.events,
                )
    except Exception:
        pass  # Notetaker failures never block a save.

    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w") as f:
        json.dump(game_state.to_dict(), f, indent=2)
