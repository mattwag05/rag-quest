#!/usr/bin/env python3
"""Comprehensive test suite for all 12 RAG-Quest v0.5 systems."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

# Import all systems
from rag_quest.engine.character import Character, Race, CharacterClass
from rag_quest.engine.world import World
from rag_quest.engine.inventory import Inventory, Item
from rag_quest.engine.quests import QuestLog, Quest, QuestObjective, QuestReward, ObjectiveType, QuestStatus
from rag_quest.engine.party import Party, PartyMember
from rag_quest.engine.relationships import RelationshipManager
from rag_quest.engine.events import EventManager, WorldEvent, EventType, EventSeverity
from rag_quest.engine.achievements import AchievementManager
from rag_quest.engine.combat import Enemy, CombatEncounter, DiceRoll
from rag_quest.engine.encounters import EncounterGenerator
from rag_quest.engine.dungeon import DungeonGenerator, DifficultyLevel
from rag_quest.saves.manager import SaveManager
from rag_quest.worlds.exporter import WorldExporter
from rag_quest.worlds.importer import WorldImporter
from rag_quest.multiplayer.session import MultiplayerSession
from rag_quest.engine.game import GameState
from rag_quest.engine.narrator import Narrator
from rag_quest.knowledge import WorldRAG
from rag_quest.llm import OllamaProvider

# Test logging
test_results = []
passed = 0
failed = 0


def test(system: str, name: str, result: bool, detail: str = ""):
    """Log a test result."""
    global passed, failed
    status = "✓ PASS" if result else "✗ FAIL"
    detail_str = f" - {detail}" if detail else ""
    print(f"  [{system:12}] {name:40} {status}{detail_str}")
    test_results.append((system, name, result))
    if result:
        passed += 1
    else:
        failed += 1


print("=" * 80)
print("RAG-QUEST V0.5 COMPREHENSIVE BUG FIX VERIFICATION")
print("=" * 80)

# Create temporary directory for saves/exports
with TemporaryDirectory() as tmpdir:
    tmppath = Path(tmpdir)

    # ============================================================================
    # SYSTEM 1: INVENTORY SERIALIZATION (FIXED IN v0.5.1)
    # ============================================================================
    print("\nSYSTEM 1: INVENTORY SERIALIZATION")
    print("-" * 80)
    
    try:
        inv = Inventory()
        inv.add_item("Sword", "A sharp blade", 1, 5, "rare")
        inv.add_item("Shield", "A sturdy shield", 1, 8, "uncommon")
        inv.add_item("Potion", "Heals 20 HP", 3, 0.5, "common")
        
        # Serialize
        inv_dict = inv.to_dict()
        test("Inventory", "to_dict() has 'items' key", 'items' in inv_dict)
        test("Inventory", "to_dict() preserves max_weight", 'max_weight' in inv_dict)
        
        # Deserialize
        inv2 = Inventory.from_dict(inv_dict)
        test("Inventory", "from_dict() restores items", len(inv2.items) == 3)
        test("Inventory", "Roundtrip preserves state", inv.get_total_weight() == inv2.get_total_weight())
    except Exception as e:
        test("Inventory", "System works", False, str(e))

    # ============================================================================
    # SYSTEM 2: DIFFICULTY LEVEL ENUM (FIXED IN v0.5.1)
    # ============================================================================
    print("\nSYSTEM 2: DIFFICULTY LEVEL ENUM")
    print("-" * 80)
    
    try:
        test("Difficulty", "EASY exists", hasattr(DifficultyLevel, 'EASY'))
        test("Difficulty", "NORMAL exists", hasattr(DifficultyLevel, 'NORMAL'))
        test("Difficulty", "MEDIUM exists", hasattr(DifficultyLevel, 'MEDIUM'))
        test("Difficulty", "HARD exists", hasattr(DifficultyLevel, 'HARD'))
        test("Difficulty", "MEDIUM aliases NORMAL", DifficultyLevel.MEDIUM == DifficultyLevel.NORMAL)
    except Exception as e:
        test("Difficulty", "Enum values", False, str(e))

    # ============================================================================
    # SYSTEM 3: COMBAT - ENEMY ATTRIBUTES
    # ============================================================================
    print("\nSYSTEM 3: COMBAT - ENEMY ATTRIBUTES")
    print("-" * 80)
    
    try:
        enemy = Enemy(name="Goblin", level=2, hp=25, attack=4, defense=11, dexterity=12)
        test("Enemy", ".hp attribute exists", hasattr(enemy, 'hp') and enemy.hp == 25)
        test("Enemy", ".attack attribute exists", hasattr(enemy, 'attack') and enemy.attack == 4)
        test("Enemy", ".defense attribute exists", hasattr(enemy, 'defense') and enemy.defense == 11)
        test("Enemy", "Internal attributes preserved", enemy.max_hp == 25 and enemy.attack_bonus == 4)
    except Exception as e:
        test("Enemy", "Attributes", False, str(e))

    # ============================================================================
    # SYSTEM 4: COMBAT - COMBAT ENCOUNTER
    # ============================================================================
    print("\nSYSTEM 4: COMBAT - COMBAT ENCOUNTER")
    print("-" * 80)
    
    try:
        player = Character(name="Hero", race=Race.HUMAN, character_class=CharacterClass.FIGHTER)
        player.defense_ac = 15
        enemies = [Enemy(name="Goblin", level=1, hp=15, attack=3, defense=10)]
        
        enc = CombatEncounter(player_character=player, enemies=enemies)
        test("Combat", "CombatEncounter creates", enc is not None)
        test("Combat", "Can access player", enc.player == player)
        test("Combat", "Can access enemies", len(enc.enemies) == 1)
        
        # Check for roll_initiative method
        if hasattr(enc, 'roll_initiative'):
            try:
                enc.roll_initiative()
                test("Combat", "roll_initiative() exists", True)
            except Exception as e:
                test("Combat", "roll_initiative() works", False, str(e))
        else:
            test("Combat", "roll_initiative() exists", False, "Method not found")
            
    except Exception as e:
        test("Combat", "CombatEncounter", False, str(e))

    # ============================================================================
    # SYSTEM 5: QUEST SYSTEM - QUEST REWARDS
    # ============================================================================
    print("\nSYSTEM 5: QUEST SYSTEM - QUEST REWARDS")
    print("-" * 80)
    
    try:
        # QuestReward should accept 'xp' parameter
        reward = QuestReward(xp=100, gold=50)
        test("Quest", "QuestReward(xp=)", reward.xp == 100)
        
        # Also test backwards compatibility with 'experience'
        try:
            reward2 = QuestReward(experience=100)  # Should work or fail gracefully
            test("Quest", "QuestReward(experience=)", True)
        except TypeError:
            test("Quest", "QuestReward(experience=) compat", False, "Not supported")
        
        # Create a full quest
        quest = Quest(
            title="Test Quest",
            description="A test quest",
            reward=QuestReward(xp=200, gold=100),
            giver_npc="Elder"
        )
        test("Quest", "Quest with reward creates", quest.reward.xp == 200)
        
    except Exception as e:
        test("Quest", "Rewards", False, str(e))

    # ============================================================================
    # SYSTEM 6: WORLD EVENTS
    # ============================================================================
    print("\nSYSTEM 6: WORLD EVENTS")
    print("-" * 80)
    
    try:
        # Create events with correct constructor
        event = WorldEvent(
            name="Goblin Raid",
            description="Goblins attack the town",
            event_type=EventType.COMBAT,
            severity=EventSeverity.MODERATE,
            duration_turns=3
        )
        test("Event", "WorldEvent creates with 'name'", event.name == "Goblin Raid")
        
        # Test backwards compat: 'title' parameter
        try:
            event2 = WorldEvent(
                title="Storm",  # Old parameter name
                description="A dark storm",
                event_type=EventType.WEATHER,
                severity=EventSeverity.MAJOR,
                duration_turns=5
            )
            test("Event", "WorldEvent(title=) compat", True)
        except TypeError:
            test("Event", "WorldEvent(title=) compat", False, "Not supported")
        
        # EventManager.get_active_events should exist
        mgr = EventManager()
        if hasattr(mgr, 'get_active_events'):
            test("Event", "EventManager.get_active_events() exists", True)
        else:
            test("Event", "EventManager.get_active_events() exists", False)
            
    except Exception as e:
        test("Event", "System", False, str(e))

    # ============================================================================
    # SYSTEM 7: SAVE/LOAD SYSTEM
    # ============================================================================
    print("\nSYSTEM 7: SAVE/LOAD SYSTEM")
    print("-" * 80)
    
    try:
        sm = SaveManager(save_dir=tmppath / "saves")
        
        # Create minimal game state
        state = {
            "character": {
                "name": "Kael",
                "level": 5,
                "current_hp": 20,
                "max_hp": 30,
                "experience": 500
            },
            "world": {"name": "Test World", "setting": "Fantasy"},
            "inventory": {},
            "quest_log": {},
            "party": {},
            "relationships": {},
            "events": {},
            "turn_number": 10,
            "playtime_seconds": 120.5
        }
        
        # Test save with new API (game_state, slot_name)
        try:
            slot = sm.save_game(state, slot_name="Slot 1")
            test("Save", "save_game(state, slot_name=)", slot is not None)
        except TypeError as e:
            test("Save", "save_game(state, slot_name=)", False, str(e))
        
        # Test old calling style compatibility  
        try:
            sm.save_game("Test World", 0, state, "Kael")  # Old style
            test("Save", "save_game() old style compat", True)
        except Exception as e:
            test("Save", "save_game() old style compat", False, "Not supported")
        
        # Test list_saves with no parameters
        try:
            saves = sm.list_saves()
            test("Save", "list_saves() no params", isinstance(saves, list))
        except Exception as e:
            test("Save", "list_saves() no params", False, str(e))
        
        # Test old style list_saves
        try:
            saves = sm.list_saves("Test World")  # Old style
            test("Save", "list_saves(world_name) compat", True)
        except Exception as e:
            test("Save", "list_saves(world_name) compat", False, "Not supported")
        
        # Test load_game with slot_id
        if saves or (hasattr(sm, '_get_first_slot_id')):
            try:
                slot_id = saves[0].slot_id if saves else list(sm.save_dir.glob("*/"))[0].name
                loaded = sm.load_game(slot_id)
                test("Save", "load_game(slot_id)", loaded is not None)
            except Exception as e:
                test("Save", "load_game(slot_id)", False, str(e))
                
    except Exception as e:
        test("Save", "System init", False, str(e))

    # ============================================================================
    # SYSTEM 8: WORLD EXPORTER
    # ============================================================================
    print("\nSYSTEM 8: WORLD EXPORTER")
    print("-" * 80)
    
    try:
        world_state = {
            "name": "Test World",
            "setting": "Fantasy",
            "tone": "Epic",
            "day_number": 15,
            "visited_locations": ["Town", "Forest", "Castle"],
            "npcs_met": ["Elder", "Guard"],
            "weather": "clear"
        }
        
        export_path = tmppath / "world.rqworld"
        
        # Test new API: export_world(game_state, output_path, author, description)
        try:
            result = WorldExporter.export_world(
                game_state={"world": world_state, "quest_log": {}, "events": {}, "relationships": {}},
                output_path=export_path,
                author="Test",
                description="A test world"
            )
            test("Export", "export_world(game_state=, ...)", result is not None and export_path.exists())
        except TypeError as e:
            test("Export", "export_world(game_state=, ...)", False, str(e))
        
        # Test old API compatibility: export_world(world=, character_name=, output_path=)
        try:
            result = WorldExporter.export_world(
                world=world_state,
                character_name="Kael",
                output_path=tmppath / "world2.rqworld"
            )
            test("Export", "export_world(world=, ...) compat", True)
        except Exception as e:
            test("Export", "export_world(world=, ...) compat", False, "Not supported")
            
    except Exception as e:
        test("Export", "System", False, str(e))

    # ============================================================================
    # SYSTEM 9: MULTIPLAYER SESSION
    # ============================================================================
    print("\nSYSTEM 9: MULTIPLAYER SESSION")
    print("-" * 80)
    
    try:
        # Test new API: MultiplayerSession(session_id, host_player)
        try:
            session = MultiplayerSession(session_id="test-session-1", host_player="Host Player")
            test("Multiplayer", "MultiplayerSession(session_id=, host_player=)", session is not None)
        except Exception as e:
            test("Multiplayer", "MultiplayerSession(session_id=, host_player=)", False, str(e))
        
        # Test old API: MultiplayerSession(world_name, max_players)
        try:
            session2 = MultiplayerSession(world_name="Test World", max_players=4)
            test("Multiplayer", "MultiplayerSession(world_name=, max_players=) compat", True)
        except Exception as e:
            test("Multiplayer", "MultiplayerSession(world_name=, max_players=) compat", False, "Not supported")
            
    except Exception as e:
        test("Multiplayer", "System", False, str(e))

    # ============================================================================
    # SYSTEM 10: RELATIONSHIPS
    # ============================================================================
    print("\nSYSTEM 10: RELATIONSHIPS")
    print("-" * 80)
    
    try:
        rel_mgr = RelationshipManager()
        
        # Add NPC
        npc = rel_mgr.add_npc("Gandalf", "Wizard")
        test("Relationship", "add_npc() works", npc is not None)
        
        # Modify relationship (current method name)
        rel_mgr.modify_relationship("Gandalf", 10, "Helped with quest")
        test("Relationship", "modify_relationship() works", True)
        
        # Test old method name compatibility
        try:
            rel_mgr.change_disposition("Gandalf", "friendly")  # Old style
            test("Relationship", "change_disposition() compat", True)
        except AttributeError:
            test("Relationship", "change_disposition() compat", False, "Not supported")
        
        # Add faction
        faction = rel_mgr.add_faction("Mages", "An order of mages", values=["wisdom", "knowledge"])
        test("Relationship", "add_faction() works", faction is not None)
        
        # Test old method name
        try:
            faction2 = rel_mgr.create_faction("Warriors", "An order of warriors")
            test("Relationship", "create_faction() compat", True)
        except AttributeError:
            test("Relationship", "create_faction() compat", False, "Not supported")
            
    except Exception as e:
        test("Relationship", "System", False, str(e))

    # ============================================================================
    # SYSTEM 11: ACHIEVEMENTS
    # ============================================================================
    print("\nSYSTEM 11: ACHIEVEMENTS")
    print("-" * 80)
    
    try:
        ach_mgr = AchievementManager()
        
        # Create game state for checking
        game_state = {
            "character": {"level": 5, "current_hp": 20, "name": "Hero"},
            "world": {"visited_locations": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"], "npcs_met": ["A", "B", "C", "D", "E"]},
            "inventory": {"items": ["a"] * 20},
            "party": {"members": ["A", "B", "C"]},
            "quest_log": {"quests": [{"status": "Completed"} for _ in range(5)]},
            "turn_number": 1
        }
        
        # Test new API: check_achievements(game_state)
        try:
            new_achievements = ach_mgr.check_achievements(game_state)
            test("Achievement", "check_achievements(game_state)", isinstance(new_achievements, list))
        except Exception as e:
            test("Achievement", "check_achievements(game_state)", False, str(e))
        
        # Test old API: check_achievements(player=...)
        try:
            player_obj = game_state["character"]
            new_achievements = ach_mgr.check_achievements(player=player_obj)
            test("Achievement", "check_achievements(player=) compat", True)
        except TypeError:
            test("Achievement", "check_achievements(player=) compat", False, "Not supported")
            
    except Exception as e:
        test("Achievement", "System", False, str(e))

    # ============================================================================
    # SYSTEM 12: DUNGEON GENERATION
    # ============================================================================
    print("\nSYSTEM 12: DUNGEON GENERATION")
    print("-" * 80)
    
    try:
        gen = DungeonGenerator()
        
        # Test generate method
        if hasattr(gen, 'generate'):
            try:
                dungeon = gen.generate(depth=5, difficulty="normal")
                test("Dungeon", "generate(depth, difficulty)", dungeon is not None)
            except Exception as e:
                test("Dungeon", "generate(depth, difficulty)", False, str(e))
        
        # Test old generate_level method
        try:
            level = gen.generate_level(1, "easy")
            test("Dungeon", "generate_level() old style", True)
        except AttributeError:
            test("Dungeon", "generate_level() old style", False, "Not supported")
        except Exception as e:
            test("Dungeon", "generate_level() old style", False, str(e))
            
    except Exception as e:
        test("Dungeon", "System init", False, str(e))

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Total:  {passed + failed}")
print(f"Success Rate: {100 * passed // (passed + failed)}%")

if failed == 0:
    print("\n✓ ALL TESTS PASSED - v0.5.0 fully verified!")
    exit(0)
else:
    print(f"\n✗ {failed} tests failed - fixes needed")
    exit(1)
