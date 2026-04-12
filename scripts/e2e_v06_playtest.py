"""v0.6 E2E playtest — drives 30 turns through the real stack and exercises
every Campaign Memory command. Writes a log to /tmp/rag_quest_v06_e2e.log so
we can inspect failures without drowning stdout.

Usage:
    .venv/bin/python scripts/e2e_v06_playtest.py
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

LOG_PATH = Path("/tmp/rag_quest_v06_e2e.log")


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def main() -> int:
    LOG_PATH.write_text("")  # Reset log.
    log("=== RAG-Quest v0.6 E2E playtest starting ===")

    import rag_quest

    log(f"version: {rag_quest.__version__}")

    from rag_quest.engine.achievements import AchievementManager
    from rag_quest.engine.character import Character, CharacterClass, Race
    from rag_quest.engine.encyclopedia import LoreEncyclopedia
    from rag_quest.engine.events import EventManager
    from rag_quest.engine.game import SAVE_FORMAT_VERSION, GameState, _save_game
    from rag_quest.engine.inventory import Inventory
    from rag_quest.engine.narrator import Narrator
    from rag_quest.engine.notetaker import Notetaker
    from rag_quest.engine.party import Party
    from rag_quest.engine.quests import QuestLog
    from rag_quest.engine.relationships import RelationshipManager
    from rag_quest.engine.timeline import Timeline
    from rag_quest.engine.world import TimeOfDay, Weather, World
    from rag_quest.knowledge import WorldRAG
    from rag_quest.llm import LLMConfig
    from rag_quest.llm.ollama_provider import OllamaProvider
    from rag_quest.saves import SaveManager

    # -----------------------------------------------------
    # Bootstrap: real Ollama provider + real LightRAG
    # -----------------------------------------------------
    log("booting LLM provider (Ollama / qwen3.5)…")
    llm_config = LLMConfig(
        provider="ollama", model="qwen3.5:latest", base_url="http://localhost:11434"
    )
    llm = OllamaProvider(llm_config)

    world_name = "E2E Testbed"
    log(f"creating WorldRAG for '{world_name}' (balanced profile)…")
    world_rag = WorldRAG(
        world_name=world_name,
        llm_config=llm_config,
        llm_provider=llm,
        rag_profile="balanced",
    )

    # Seed with tiny lore so the encyclopedia has something to chew on.
    log("seeding starter lore…")
    try:
        world_rag.ingest_text(
            "The village of Ashenford sits at the edge of the Greywood. "
            "Captain Mira commands the local guard. The merchant Tobin trades "
            "rare herbs from his stall near the market square. The Vermilion "
            "Circle is a secretive faction of scholars rumored to meddle in lost magics.",
            source="seed",
        )
    except Exception as e:
        log(f"WARN seed ingest failed: {e}")

    # -----------------------------------------------------
    # Build GameState
    # -----------------------------------------------------
    character = Character(
        name="Aldric",
        race=Race.HUMAN,
        character_class=CharacterClass.FIGHTER,
        location="Ashenford",
    )
    world = World(name=world_name, setting="Dark fantasy", tone="Grim but hopeful")
    inventory = Inventory()
    quest_log = QuestLog()
    party = Party()
    relationships = RelationshipManager()
    events = EventManager()
    achievements = AchievementManager()
    narrator = Narrator(llm, world_rag, character, world, inventory, quest_log)
    timeline = Timeline()
    notetaker = Notetaker(world_name=world_name, llm=llm)

    game_state = GameState(
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
        timeline=timeline,
        notetaker=notetaker,
    )
    game_state.encyclopedia = LoreEncyclopedia(game_state)

    # -----------------------------------------------------
    # 30-turn scripted playthrough
    # -----------------------------------------------------
    actions = [
        "look around the town square",
        "walk toward the market stalls",
        "greet the merchant Tobin and ask what he sells",
        "buy a healing potion from Tobin",
        "ask Tobin about any trouble in Ashenford",
        "head to the guard house to find Captain Mira",
        "introduce yourself to Captain Mira",
        "ask Mira about the Greywood rumors",
        "accept Mira's quest to investigate the Greywood",
        "leave town through the north gate",
        "travel along the forest path toward the Greywood",
        "examine the trees and listen for movement",
        "draw your sword as a shape rustles in the brush",
        "strike the goblin scout with your blade",
        "pursue the fleeing goblin deeper into the woods",
        "find the goblin camp in a small clearing",
        "sneak behind a fallen log to observe the camp",
        "hurl your torch into the goblin camp and charge",
        "defeat the goblin chieftain in single combat",
        "search the slain chieftain for loot",
        "pick up the strange rune-etched amulet",
        "return to the forest path with your prize",
        "travel back toward Ashenford",
        "report your success to Captain Mira",
        "hand the amulet over to Mira",
        "ask Mira about the Vermilion Circle",
        "visit Tobin again to share news",
        "rest for the night at the inn",
        "wake up refreshed and plan your next move",
        "set out at dawn toward the ruins Mira mentioned",
    ]

    save_dir = Path.home() / ".local/share/rag-quest/saves"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{world_name}_e2e.json"

    for idx, action in enumerate(actions, start=1):
        game_state.turn_number += 1
        log(f"--- turn {idx}: {action}")
        t0 = time.time()
        try:
            response = narrator.process_action(action)
        except Exception as e:
            log(f"  ERROR narrator.process_action: {e}")
            response = "(narrator error — continuing)"
        elapsed = time.time() - t0
        log(f"  response ({elapsed:.1f}s): {response[:200].replace(chr(10), ' ')}…")

        # Timeline update — same hook as the real game loop.
        try:
            change = getattr(narrator, "last_change", None)
            if change is not None:
                new_events = timeline.record_from_state_change(
                    turn=game_state.turn_number,
                    change=change,
                    player_input=action,
                    location=character.location or "",
                )
                if new_events:
                    log(
                        f"  timeline +{len(new_events)} event(s): {[e.type for e in new_events]}"
                    )
        except Exception as e:
            log(f"  ERROR timeline: {e}")

        # Every 10 turns, exercise save + notetaker auto-refresh.
        if idx % 10 == 0:
            log(f"  [checkpoint] saving + running notetaker at turn {idx}")
            try:
                _save_game(game_state, save_path)
                log(f"  notes entries after save: {len(notetaker.entries)}")
            except Exception as e:
                log(f"  ERROR save: {e}")

        # Bookmark the first big combat turn for realism.
        if idx == 14:
            from datetime import datetime as _dt

            from rag_quest.engine.timeline import Bookmark

            bm = Bookmark(
                turn=game_state.turn_number,
                timestamp=_dt.now().isoformat(timespec="seconds"),
                note="First goblin strike",
                player_input=action,
                narrator_prose=narrator.last_response,
                location=character.location or "",
            )
            timeline.add_bookmark(bm)
            log("  bookmarked turn 14")

    # -----------------------------------------------------
    # Post-run assertions + reporting
    # -----------------------------------------------------
    log("=== post-run summary ===")
    log(f"turns played: {game_state.turn_number}")
    log(f"timeline events: {len(timeline.events)}")
    log(f"bookmarks: {len(timeline.bookmarks)}")
    log(f"notes entries: {len(notetaker.entries)}")
    log(f"visited locations: {sorted(world.visited_locations)}")
    log(f"npcs met: {sorted(world.npcs_met)}")
    log(f"inventory: {list(inventory.items.keys())}")
    log(f"quests: {len(quest_log.get_active_quests())} active")
    log(
        f"character HP: {character.current_hp}/{character.max_hp}, level {character.level}"
    )

    # Encyclopedia smoke test
    enc = game_state.encyclopedia
    log("encyclopedia category counts:")
    for cat, count in enc.categories_with_counts():
        log(f"  {cat}: {count}")

    # Force a notetaker refresh + canonize one entry
    log("forcing notes refresh…")
    entry = notetaker.refresh(
        current_turn=game_state.turn_number,
        conversation_history=narrator.get_conversation_history(),
        timeline_events=timeline.events,
    )
    if entry:
        log(f"  new note: turns {entry.turn_range} — {entry.session_summary[:160]}")
    pending = notetaker.pending_for_canonization()
    log(f"pending for canonization: {len(pending)}")
    if pending:
        ok = notetaker.canonize_entry(0, world_rag)
        log(f"canonize result: {ok}")

    # Save/load round-trip
    log("save + reload round-trip…")
    _save_game(game_state, save_path)
    with open(save_path) as f:
        saved = json.load(f)
    assert saved.get("save_version") == SAVE_FORMAT_VERSION, "save_version missing"
    assert "timeline" in saved, "timeline missing from save"
    assert len(saved["timeline"]["events"]) > 0, "timeline events empty"
    assert len(saved["timeline"]["bookmarks"]) >= 1, "bookmark missing"
    log(f"save_version: {saved['save_version']}")
    log(f"reloaded timeline events: {len(saved['timeline']['events'])}")
    log(f"reloaded bookmarks: {len(saved['timeline']['bookmarks'])}")

    # Cleanup
    try:
        world_rag.close()
    except Exception:
        pass
    try:
        llm.close()
    except Exception:
        pass

    log("=== E2E playtest complete ===")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"FATAL: {e}")
        log(traceback.format_exc())
        sys.exit(1)
