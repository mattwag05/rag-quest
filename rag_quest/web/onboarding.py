"""Web onboarding — create a new game session from the browser.

Mirrors the CLI's ``__main__._create_character_with_descriptions`` and
``_show_start_menu`` flows, but returns data for the JS client to render
instead of printing Rich prompts. The heavy lifting (provider construction,
WorldRAG init, GameState assembly) reuses the same ``config`` helpers the
CLI calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine.game import GameState


class OnboardingError(Exception):
    """Raised when new-game creation fails."""


# ---- Static data for the character-creation screens ----

RACES = [
    {
        "id": "HUMAN",
        "name": "Human",
        "description": "Versatile and adaptable.",
        "bonuses": "+1 STR, +1 DEX",
    },
    {
        "id": "ELF",
        "name": "Elf",
        "description": "Graceful and perceptive.",
        "bonuses": "+2 DEX",
    },
    {
        "id": "DWARF",
        "name": "Dwarf",
        "description": "Tough and resilient.",
        "bonuses": "+2 CON",
    },
    {
        "id": "HALFLING",
        "name": "Halfling",
        "description": "Lucky and nimble.",
        "bonuses": "+2 DEX, +1 CHA",
    },
    {
        "id": "ORC",
        "name": "Orc",
        "description": "Powerful and fierce.",
        "bonuses": "+2 STR, +1 CON",
    },
]

CLASSES = [
    {
        "id": "FIGHTER",
        "name": "Fighter",
        "description": "Master of weapons and armor. High HP, strong attacks.",
        "abilities": "Power Strike (L1), Shield Wall (L3), Cleave (L6)",
        "hp": 30,
    },
    {
        "id": "MAGE",
        "name": "Mage",
        "description": "Wielder of arcane magic. Powerful spells, low HP.",
        "abilities": "Fireball (L1), Heal (L2), Arcane Shield (L4)",
        "hp": 15,
    },
    {
        "id": "ROGUE",
        "name": "Rogue",
        "description": "Stealthy and cunning. High damage from shadows.",
        "abilities": "Backstab (L1), Dodge (L3), Steal (L5)",
        "hp": 18,
    },
    {
        "id": "RANGER",
        "name": "Ranger",
        "description": "Wilderness expert. Balanced combat and tracking.",
        "abilities": "Arrow Volley (L1), Track (L3), Animal Companion (L6)",
        "hp": 22,
    },
    {
        "id": "CLERIC",
        "name": "Cleric",
        "description": "Divine servant. Healing and holy magic.",
        "abilities": "Divine Heal (L1), Smite (L2), Bless (L4)",
        "hp": 26,
    },
]

TEMPLATES = [
    {
        "id": "classic_dungeon",
        "name": "Classic Dungeon",
        "description": "Dark corridors, ancient traps, forgotten treasures.",
        "setting": "Ancient Dungeon",
        "tone": "Dark",
        "starting_location": "The entrance to a deep, dark dungeon",
        "difficulty": "medium",
    },
    {
        "id": "enchanted_forest",
        "name": "Enchanted Forest",
        "description": "Mystical creatures, fey courts, ancient magic.",
        "setting": "Mystical Forest",
        "tone": "Whimsical",
        "starting_location": "A clearing in an ancient forest",
        "difficulty": "medium",
    },
    {
        "id": "port_city",
        "name": "Port City",
        "description": "Maritime intrigue, merchant guilds, pirate threats.",
        "setting": "Bustling Port City",
        "tone": "Heroic",
        "starting_location": "The docks of a busy trading port",
        "difficulty": "medium",
    },
    {
        "id": "war_torn_kingdom",
        "name": "War-Torn Kingdom",
        "description": "Political conflict, siege warfare, divided loyalties.",
        "setting": "Divided Kingdom",
        "tone": "Dark",
        "starting_location": "A war-scarred village",
        "difficulty": "hard",
    },
]


def create_new_session(
    *,
    character_name: str,
    race: str,
    character_class: str,
    template_id: str | None = None,
    world_name: str | None = None,
    world_setting: str | None = None,
    world_tone: str | None = None,
) -> "GameState":
    """Create a brand-new GameState, ready to play.

    Mirrors ``__main__._main`` new-game path but without Rich prompts.
    Raises ``OnboardingError`` on any failure.
    """
    from .. import config as _config
    from ..engine.achievements import AchievementManager
    from ..engine.character import Character, CharacterClass, Race
    from ..engine.encyclopedia import LoreEncyclopedia
    from ..engine.events import EventManager
    from ..engine.game import GameState
    from ..engine.inventory import Inventory
    from ..engine.narrator import Narrator
    from ..engine.notetaker import Notetaker
    from ..engine.party import Party
    from ..engine.quests import QuestLog
    from ..engine.relationships import RelationshipManager
    from ..engine.timeline import Timeline
    from ..knowledge import WorldRAG

    # --- Validate character params ---
    character_name = (character_name or "").strip()
    if not character_name:
        raise OnboardingError("Character name cannot be empty")
    if len(character_name) > 50:
        raise OnboardingError("Character name too long (max 50 characters)")

    try:
        race_enum = Race[race.upper()]
    except KeyError:
        raise OnboardingError(f"Unknown race: {race!r}")

    try:
        class_enum = CharacterClass[character_class.upper()]
    except KeyError:
        raise OnboardingError(f"Unknown class: {character_class!r}")

    # --- Build world config ---
    if template_id:
        tpl = next((t for t in TEMPLATES if t["id"] == template_id), None)
        if tpl is None:
            raise OnboardingError(f"Unknown template: {template_id!r}")
        w_name = tpl["name"]
        w_setting = tpl["setting"]
        w_tone = tpl["tone"]
        starting_location = tpl["starting_location"]
    else:
        w_name = world_name or "Generated World"
        w_setting = world_setting or "Fantasy"
        w_tone = world_tone or "Heroic"
        starting_location = "A quaint tavern"

    # --- Load LLM provider from config ---
    if not _config.CONFIG_FILE.exists():
        raise OnboardingError(
            "No RAG-Quest config found. Run the CLI once to set up your "
            "LLM provider, or create ~/.config/rag-quest/config.json."
        )
    game_config = _config.ConfigManager().config

    try:
        llm_provider, llm_config = _config.load_llm_provider(game_config)
    except (KeyError, ValueError) as exc:
        raise OnboardingError(f"Invalid LLM config: {exc}") from exc

    rag_profile = game_config.get("rag", {}).get("profile", "balanced")

    # --- Build engine objects ---
    from ..engine.world import World

    character = Character(
        name=character_name,
        race=race_enum,
        character_class=class_enum,
        location=starting_location,
    )
    world = World(name=w_name, setting=w_setting, tone=w_tone)

    try:
        world_rag = WorldRAG(
            w_name, llm_config, llm_provider, rag_profile=rag_profile
        )
    except Exception as exc:
        raise OnboardingError(f"Could not initialize WorldRAG: {exc}") from exc

    inventory = Inventory()
    quest_log = QuestLog()
    party = Party()
    relationships = RelationshipManager()
    events = EventManager()
    achievements = AchievementManager()
    narrator = Narrator(llm_provider, world_rag, character, world, inventory, quest_log)
    timeline = Timeline()

    try:
        notetaker = Notetaker(world_name=world.name, llm=llm_provider)
    except Exception:
        notetaker = None

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

    # --- Persist initial save ---
    save_dir = Path.home() / ".local/share/rag-quest/saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{w_name}.json"
    save_path.write_text(json.dumps(game_state.to_dict(), indent=2))

    return game_state
