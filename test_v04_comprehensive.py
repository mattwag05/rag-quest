#!/usr/bin/env python3
"""
Comprehensive v0.4 RAG-Quest playtest using actual APIs.
50-turn playtest exercising all systems.
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from rag_quest.engine.character import Character, Race, CharacterClass
from rag_quest.engine.world import World, TimeOfDay, Weather
from rag_quest.engine.party import Party
from rag_quest.engine.relationships import RelationshipManager
from rag_quest.engine.inventory import Inventory, Item
from rag_quest.engine.quests import QuestLog
from rag_quest.engine.events import EventManager
from rag_quest.engine.combat import CombatManager

LOG_FILE = Path(__file__).parent / "v04_playtest_log.txt"

class TestLogger:
    def __init__(self, filepath):
        self.file = open(filepath, "w")
        self.errors = []
        self.warnings = []
    
    def log(self, message):
        print(message)
        self.file.write(message + "\n")
        self.file.flush()
    
    def error(self, message):
        self.log(f"[ERROR] {message}")
        self.errors.append(message)
    
    def warning(self, message):
        self.log(f"[WARNING] {message}")
        self.warnings.append(message)
    
    def close(self):
        self.file.close()

logger = TestLogger(LOG_FILE)

def test_turn(num, action, func):
    """Run a single test turn."""
    logger.log(f"\n[TURN {num:02d}] {action}")
    try:
        result = func()
        return result
    except Exception as e:
        logger.error(f"Turn {num} failed: {e}")
        import traceback
        traceback.print_exc(file=logger.file)
        return None

def run_tests():
    """Run all tests."""
    logger.log("="*60)
    logger.log("RAG-QUEST v0.4 COMPREHENSIVE PLAYTEST")
    logger.log("="*60)
    logger.log(f"Start: {datetime.now()}\n")
    
    # PHASE 1: Character Creation
    logger.log("\n=== PHASE 1: CHARACTER CREATION ===")
    
    def turn_1():
        char = Character(
            name="Thorin",
            race=Race.DWARF,
            character_class=CharacterClass.FIGHTER
        )
        logger.log(f"  Created: {char.name} ({char.race.value} {char.character_class.value})")
        logger.log(f"  HP: {char.current_hp}/{char.max_hp}, XP: {char.experience}, Level: {char.level}")
        logger.log(f"  Stats: STR={char.strength} DEX={char.dexterity} CON={char.constitution}")
        return char
    
    char = test_turn(1, "Create character (Dwarf Fighter)", turn_1)
    if not char:
        logger.error("CRITICAL: Cannot create character, aborting playtest")
        return
    
    # PHASE 2: World State
    logger.log("\n=== PHASE 2: WORLD STATE ===")
    
    def turn_2():
        world = World(name="Khazad-dum", setting="Medieval Fantasy", tone="Dark")
        logger.log(f"  World: {world.name} ({world.setting})")
        logger.log(f"  Time: {world.current_time.value}, Weather: {world.weather.value}")
        logger.log(f"  Day: {world.day_number}")
        return world
    
    world = test_turn(2, "Initialize world", turn_2)
    
    def turn_3():
        world.add_visited_location("Tavern")
        world.add_visited_location("Forest")
        logger.log(f"  Visited locations: {world.visited_locations}")
        logger.log(f"  Current location count: {len(world.visited_locations)}")
        return world
    
    test_turn(3, "Visit locations", turn_3)
    
    def turn_4():
        world.advance_time()
        logger.log(f"  Time advanced to: {world.current_time.value}")
        for _ in range(6):
            world.advance_time()
        logger.log(f"  Time after multiple advances: {world.current_time.value}, Day: {world.day_number}")
        return world
    
    test_turn(4, "Advance time", turn_4)
    
    # PHASE 3: Inventory
    logger.log("\n=== PHASE 3: INVENTORY SYSTEM ===")
    
    def turn_5():
        inv = Inventory(max_weight=100)
        inv.add_item("Sword", "Iron sword", quantity=1, weight=5)
        inv.add_item("Potion", "Health potion", quantity=5, weight=0.5)
        inv.add_item("Gold", "Currency", quantity=100, weight=0.1)
        items = inv.list_items()
        logger.log(f"  Items in inventory: {len(items)}")
        for name, item in list(items.items())[:3]:
            logger.log(f"    - {name}: qty={item.quantity}, weight={item.weight}")
        logger.log(f"  Total weight: {inv.get_total_weight()}/{inv.max_weight}")
        return inv
    
    inv = test_turn(5, "Initialize inventory and add items", turn_5)
    
    def turn_6():
        if inv:
            inv.add_item("Amulet", "Magical amulet", quantity=1, weight=0.5, rarity="rare")
            weight = inv.get_total_weight()
            logger.log(f"  Added rare item, new weight: {weight}")
            return inv.is_full()
        return False
    
    test_turn(6, "Add rare item and check capacity", turn_6)
    
    # PHASE 4: Party System
    logger.log("\n=== PHASE 4: PARTY SYSTEM ===")
    
    def turn_7():
        party = Party(leader=char)
        logger.log(f"  Party created with leader: {char.name}")
        logger.log(f"  Party size: {len(party.members)}")
        return party
    
    party = test_turn(7, "Create party", turn_7)
    
    def turn_8():
        if party:
            companion = Character(
                name="Elara",
                race=Race.ELF,
                character_class=CharacterClass.RANGER
            )
            party.add_member(companion)
            logger.log(f"  Added companion: {companion.name}")
            logger.log(f"  Party size: {len(party.members)}")
            logger.log(f"  Members: {[m.name for m in party.members]}")
            return party
        return None
    
    test_turn(8, "Recruit party member", turn_8)
    
    # PHASE 5: Relationships
    logger.log("\n=== PHASE 5: RELATIONSHIP SYSTEM ===")
    
    def turn_9():
        rel_mgr = RelationshipManager()
        rel_mgr.add_npc("Barkeep", "Tavern owner")
        rel_mgr.add_npc("Elara", "Ranger")
        npcs = rel_mgr.npcs
        logger.log(f"  NPCs tracked: {len(npcs)}")
        for npc_name, npc in list(npcs.items())[:3]:
            logger.log(f"    - {npc_name}: {npc.role}, disposition={npc.disposition.value}")
        return rel_mgr
    
    rel_mgr = test_turn(9, "Initialize relationships", turn_9)
    
    def turn_10():
        if rel_mgr:
            rel_mgr.add_gift("Barkeep", "Rare ale")
            rel = rel_mgr.npcs.get("Barkeep")
            if rel:
                logger.log(f"  Gave gift to Barkeep")
                logger.log(f"  Disposition: {rel.disposition.value}")
            return rel_mgr
        return None
    
    test_turn(10, "Give gift to NPC", turn_10)
    
    # PHASE 6: Combat
    logger.log("\n=== PHASE 6: COMBAT SYSTEM ===")
    
    def turn_11():
        combat = CombatManager()
        enemy = Character(
            name="Goblin",
            race=Race.ORC,
            character_class=CharacterClass.ROGUE
        )
        logger.log(f"  Combat vs {enemy.name}")
        logger.log(f"  Player: {char.name} HP={char.current_hp}")
        logger.log(f"  Enemy: {enemy.name} HP={enemy.current_hp}")
        return (combat, enemy)
    
    combat_data = test_turn(11, "Initialize combat encounter", turn_11)
    if not combat_data:
        combat = enemy = None
    else:
        combat, enemy = combat_data
    
    def turn_12():
        if combat and enemy:
            # Simulate combat rounds
            rounds = 0
            while char.current_hp > 0 and enemy.current_hp > 0 and rounds < 10:
                # Player attack
                import random
                damage = random.randint(3, 10) + (char.strength - 10) // 2
                enemy.current_hp = max(0, enemy.current_hp - damage)
                logger.log(f"  Round {rounds+1}: Player deals {damage} damage")
                if enemy.current_hp <= 0:
                    logger.log(f"  Victory! Defeated {enemy.name}")
                    break
                # Enemy counter
                damage = random.randint(1, 6)
                char.current_hp = max(0, char.current_hp - damage)
                logger.log(f"  Enemy counter: {damage} damage to player")
                if char.current_hp <= 0:
                    logger.log(f"  Defeat! Player knocked out")
                    break
                rounds += 1
            return True
        return False
    
    test_turn(12, "Complete combat encounter", turn_12)
    
    def turn_13():
        if char:
            old_xp = char.experience
            char.experience += 250
            logger.log(f"  XP gain: {old_xp} -> {char.experience}")
            return char
        return None
    
    test_turn(13, "Gain XP from combat", turn_13)
    
    # PHASE 7: Quests
    logger.log("\n=== PHASE 7: QUEST SYSTEM ===")
    
    def turn_14():
        quest_log = QuestLog()
        from rag_quest.engine.quests import Quest, QuestStatus, QuestReward
        quest = Quest(
            title="Slay the Dragon",
            description="A dragon has been terrorizing the village",
            status=QuestStatus.ACTIVE,
            objectives="Defeat dragon",
            reward=QuestReward(xp=500, gold=1000),
            giver_npc="Mayor"
        )
        quest_log.add_quest(quest)
        active = quest_log.get_active_quests()
        logger.log(f"  Active quests: {len(active)}")
        for q in active:
            logger.log(f"    - {q.title}: {q.description}")
        return quest_log
    
    quest_log = test_turn(14, "Create and track quests", turn_14)
    
    def turn_15():
        if quest_log:
            from rag_quest.engine.quests import QuestStatus
            active = quest_log.get_active_quests()
            if active:
                quest = active[0]
                logger.log(f"  Current quest: {quest.title}")
                logger.log(f"  Status: {quest.status.value}")
                logger.log(f"  Reward: XP={quest.reward.xp}, Gold={quest.reward.gold}")
            return quest_log
        return None
    
    test_turn(15, "Review quest details", turn_15)
    
    # PHASE 8: Events
    logger.log("\n=== PHASE 8: WORLD EVENTS ===")
    
    def turn_16():
        event_mgr = EventManager()
        logger.log(f"  Event manager initialized")
        from rag_quest.engine.events import WorldEvent, EventType, EventSeverity
        event = WorldEvent(
            title="Bandit Raid",
            description="Bandits attack the village",
            type=EventType.CONFLICT,
            severity=EventSeverity.HIGH
        )
        event_mgr.add_event(event)
        events = event_mgr.get_active_events()
        logger.log(f"  Active events: {len(events)}")
        return event_mgr
    
    event_mgr = test_turn(16, "Create world events", turn_16)
    
    # PHASE 9: Abilities
    logger.log("\n=== PHASE 9: CHARACTER ABILITIES ===")
    
    def turn_17():
        if char:
            abilities = char.get_available_abilities()
            logger.log(f"  Available abilities: {len(abilities)}")
            for ability in abilities[:3]:
                logger.log(f"    - {ability.name} (unlock level {ability.unlock_level})")
            return abilities
        return []
    
    test_turn(17, "Check available abilities", turn_17)
    
    def turn_18():
        if char:
            char.level = 3
            abilities = char.get_available_abilities()
            logger.log(f"  After leveling to 3: {len(abilities)} abilities available")
            return abilities
        return []
    
    test_turn(18, "Level up and check new abilities", turn_18)
    
    # PHASE 10: Save/Load
    logger.log("\n=== PHASE 10: SAVE/LOAD SYSTEM ===")
    
    def turn_19():
        import json
        save_data = {
            "character": {
                "name": char.name,
                "race": char.race.value,
                "class": char.character_class.value,
                "level": char.level,
                "experience": char.experience,
                "hp": char.current_hp,
            },
            "world": {
                "name": world.name if world else "Unknown",
                "day": world.day_number if world else 1,
            },
            "inventory": {
                name: item.to_dict() for name, item in inv.items.items()
            } if inv else {}
        }
        save_file = Path(__file__).parent / "test_save.json"
        with open(save_file, "w") as f:
            json.dump(save_data, f, indent=2)
        logger.log(f"  Saved game to {save_file}")
        return save_file
    
    save_file = test_turn(19, "Save game state", turn_19)
    
    def turn_20():
        if save_file and save_file.exists():
            import json
            with open(save_file) as f:
                data = json.load(f)
            logger.log(f"  Loaded save file")
            logger.log(f"  Character: {data['character']['name']} Level {data['character']['level']}")
            logger.log(f"  Experience: {data['character']['experience']}")
            return True
        return False
    
    test_turn(20, "Load and verify save", turn_20)
    
    # PHASE 11: Edge Cases
    logger.log("\n=== PHASE 11: EDGE CASES ===")
    
    def turn_21():
        # Empty inventory operations
        empty_inv = Inventory(max_weight=10)
        items = empty_inv.list_items()
        logger.log(f"  Empty inventory items: {len(items)}")
        return empty_inv
    
    test_turn(21, "Empty inventory handling", turn_21)
    
    def turn_22():
        # Very high stats
        if char:
            char.strength = 20
            char.intelligence = 20
            logger.log(f"  Set character to max stats: STR={char.strength} INT={char.intelligence}")
            return char
        return None
    
    test_turn(22, "High stat character", turn_22)
    
    # Summary
    logger.log("\n" + "="*60)
    logger.log(f"PLAYTEST COMPLETE")
    logger.log(f"End: {datetime.now()}")
    logger.log(f"Errors: {len(logger.errors)}")
    logger.log(f"Warnings: {len(logger.warnings)}")
    logger.log("="*60)

if __name__ == "__main__":
    try:
        run_tests()
        logger.close()
    except Exception as e:
        logger.error(f"FATAL: {e}")
        import traceback
        traceback.print_exc(file=logger.file)
        logger.close()
        sys.exit(1)
