"""Session hydration — build a live ``GameState`` from a save slot.

The CLI's ``run_game`` constructs its ``GameState`` fresh from a config
wizard. The web layer needs the same triple (``GameState`` + ``Narrator``
+ ``WorldRAG``) starting from an existing save file, so this module
encapsulates the "read save dict from disk → build provider → build
world_rag → build narrator → hydrate GameState" chain.

``load_session_from_slot(slot_id)`` is the single entry point. It raises
``SessionLoadError`` on any failure (missing slot, malformed config,
unknown provider) so callers get a clean error surface instead of
having to worry about five independent failure modes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine.game import GameState


class SessionLoadError(Exception):
    """Raised when a save slot cannot be hydrated into a live session."""


def list_save_slots() -> list[dict]:
    """Return every save slot as a plain dict, sorted newest-first."""
    from ..saves.manager import SaveManager

    return [slot.to_dict() for slot in SaveManager().list_saves()]


def _load_config_dict() -> dict:
    from .. import config as _config

    if not _config.CONFIG_FILE.exists():
        raise SessionLoadError(
            "No RAG-Quest config found. Run the CLI once to set up your LLM "
            "provider before loading sessions over the web API."
        )
    return _config.ConfigManager().config


def load_session_from_slot(slot_id: str) -> "GameState":
    """Load a save slot, returning a fully-wired ``GameState``.

    Reads the save dict via ``SaveManager``, pulls LLM provider config
    from ``~/.config/rag-quest/config.json``, constructs a
    ``WorldRAG`` for the save's world name, builds a ``Narrator``,
    and hands everything to ``GameState.from_dict``. On any failure
    raises ``SessionLoadError`` with a user-facing message.
    """
    from .. import config as _config
    from ..engine.character import Character
    from ..engine.game import GameState
    from ..engine.inventory import Inventory
    from ..engine.narrator import Narrator
    from ..engine.quests import QuestLog
    from ..engine.world import World
    from ..knowledge import WorldRAG
    from ..knowledge.world_db import WorldDB
    from ..saves.manager import SaveManager

    save_manager = SaveManager()
    save_dict = save_manager.load_game(slot_id)
    if save_dict is None:
        raise SessionLoadError(f"No save slot with id {slot_id!r}")

    game_config = _load_config_dict()
    try:
        llm_provider, llm_config = _config.load_llm_provider(game_config)
    except (KeyError, ValueError) as exc:
        raise SessionLoadError(f"Invalid LLM config: {exc}") from exc

    rag_profile = game_config.get("rag", {}).get("profile", "balanced")

    world_name = save_dict.get("world", {}).get("name")
    if not world_name:
        raise SessionLoadError("Save does not contain a world name")

    try:
        world_rag = WorldRAG(
            world_name, llm_config, llm_provider, rag_profile=rag_profile
        )
    except Exception as exc:
        raise SessionLoadError(f"Could not initialize WorldRAG: {exc}") from exc

    # Narrator needs character/world/inventory/quest_log to bind to, but
    # GameState.from_dict re-hydrates them internally and those hydrated
    # instances are the authoritative ones — callers mutate state via
    # narrator.character and expect that to be visible through
    # game_state.character. Build preliminary instances here to satisfy
    # Narrator's constructor, then rebind the four attributes to the
    # hydrated instances below so narrator and GameState share references.
    character = Character.from_dict(save_dict.get("character", {}))
    world = World.from_dict(save_dict.get("world", {"name": "Unknown"}))
    inventory = Inventory.from_dict(save_dict.get("inventory", {"items": {}}))
    quest_log = QuestLog.from_dict(
        save_dict.get("quest_log", {"quests": [], "quest_chains": {}})
    )
    narrator = Narrator(llm_provider, world_rag, character, world, inventory, quest_log)

    # v0.9 Phase 1: open the WorldDB alongside the JSON save. SaveManager
    # keeps each slot in its own directory, so the DB is colocated with
    # `state.json`. A fresh v3 save triggers the one-time migration inside
    # `GameState.from_dict`.
    try:
        slot_dir = save_manager.save_dir / slot_id
        world_db: WorldDB | None = WorldDB(slot_dir / "world.db")
    except Exception as exc:
        world_db = None
        # Non-fatal: the game still runs with JSON saves, just without the
        # memory architecture features. Log via the debug channel so
        # RAG_QUEST_DEBUG=1 surfaces the failure.
        from .._debug import log_swallowed_exc

        log_swallowed_exc(f"web.sessions.world_db_open: {exc}")

    try:
        game_state = GameState.from_dict(
            save_dict, narrator, world_rag, llm_provider, world_db=world_db
        )
    except Exception as exc:
        raise SessionLoadError(f"Could not hydrate GameState: {exc}") from exc

    narrator.character = game_state.character
    narrator.world = game_state.world
    narrator.inventory = game_state.inventory
    narrator.quest_log = game_state.quest_log
    return game_state
