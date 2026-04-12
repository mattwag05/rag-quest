#!/usr/bin/env python3
"""
Comprehensive integration test for RAG-Quest v0.4.1 bug fixes.

Tests all 6 fixed systems:
1. Inventory list_items and iteration
2. Party constructor with leader argument
3. RelationshipManager add_npc method
4. QuestLog add_quest method signature
5. EventType enum with CONFLICT
6. Character get_available_abilities method
"""

import sys
import traceback
from typing import List

# Add project to path
sys.path.insert(0, '/Users/matthewwagner/Desktop/Projects/rag-quest')

from rag_quest.engine.inventory import Inventory, Item
from rag_quest.engine.party import Party, PartyMember
from rag_quest.engine.relationships import RelationshipManager
from rag_quest.engine.quests import QuestLog, Quest, QuestObjective, QuestReward, ObjectiveType, QuestStatus
from rag_quest.engine.events import EventManager, EventType
from rag_quest.engine.character import Character, Race, CharacterClass
from rag_quest.engine.game import GameState
from rag_quest.engine.world import World

class TestRunner:
    """Simple test runner."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def run_test(self, name: str, test_func) -> bool:
        """Run a single test."""
        try:
            test_func()
            self.passed += 1
            print(f"✓ {name}")
            return True
        except AssertionError as e:
            self.failed += 1
            self.errors.append(f"✗ {name}: {e}")
            print(f"✗ {name}: {e}")
            return False
        except Exception as e:
            self.failed += 1
            self.errors.append(f"✗ {name}: {type(e).__name__}: {e}")
            print(f"✗ {name}: {type(e).__name__}: {e}")
            traceback.print_exc()
            return False
    
    def summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Test Results: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"{'='*60}")
            for error in self.errors:
                print(error)
        print(f"{'='*60}")
        return self.failed == 0

runner = TestRunner()

# ==============================================================================
# TEST 1: Inventory - list_items() returns string, items dict works
# ==============================================================================

def test_inventory_list_items():
    """Test Inventory.list_items() returns a string."""
    inv = Inventory(max_weight=100.0)
    
    # Empty inventory
    result = inv.list_items()
    assert isinstance(result, str), f"list_items() should return str, got {type(result)}"
    assert "empty" in result.lower(), f"Empty inventory should say 'empty', got: {result}"
    
    # Add items
    inv.add_item("Sword", "A sharp blade", quantity=1, weight=5.0)
    inv.add_item("Shield", "A protective shield", quantity=1, weight=8.0)
    inv.add_item("Potion", "Health potion", quantity=3, weight=0.5)
    
    result = inv.list_items()
    assert isinstance(result, str), "list_items() should return str"
    assert "Sword" in result, "Sword should be in inventory list"
    assert "Shield" in result, "Shield should be in inventory list"
    assert "Potion" in result, "Potion should be in inventory list"
    assert "x3" in result, "Potion quantity should show as x3"

def test_inventory_dict_iteration():
    """Test that inventory items dict can be iterated."""
    inv = Inventory()
    inv.add_item("Item1", "Desc1")
    inv.add_item("Item2", "Desc2")
    inv.add_item("Item3", "Desc3")
    
    # Test dict iteration
    assert isinstance(inv.items, dict), "items should be a dict"
    assert len(inv.items) == 3, f"Should have 3 items, got {len(inv.items)}"
    
    # Test iteration
    count = 0
    for name, item in inv.items.items():
        assert isinstance(name, str), "Item name should be string"
        assert isinstance(item, Item), "Item value should be Item object"
        count += 1
    
    assert count == 3, f"Should iterate 3 items, got {count}"

runner.run_test("Inventory.list_items() returns string", test_inventory_list_items)
runner.run_test("Inventory.items dict iteration works", test_inventory_dict_iteration)

# ==============================================================================
# TEST 2: Party - Constructor accepts leader argument
# ==============================================================================

def test_party_constructor_with_leader():
    """Test Party constructor accepts leader keyword argument."""
    member = PartyMember(
        name="Hero",
        race="Human",
        character_class="Fighter"
    )
    
    # Should not raise TypeError
    party = Party(max_size=4, leader=member)
    
    assert party.leader == member, "Leader should be set"
    assert party.max_size == 4, "Max size should be set"

def test_party_constructor_without_leader():
    """Test Party constructor works without leader."""
    party = Party(max_size=4)
    
    assert party.leader is None, "Leader should be None by default"
    assert party.max_size == 4, "Max size should be set"

def test_party_serialization_with_leader():
    """Test Party serialization preserves leader."""
    member = PartyMember(
        name="Hero",
        race="Human",
        character_class="Fighter",
        loyalty=75
    )
    
    party = Party(max_size=4, leader=member)
    data = party.to_dict()
    
    assert "leader" in data, "Serialized party should have leader key"
    assert data["leader"] is not None, "Leader should be serialized"
    assert data["leader"]["name"] == "Hero", "Leader name should be preserved"
    
    # Deserialize
    party2 = Party.from_dict(data)
    assert party2.leader is not None, "Deserialized party should have leader"
    assert party2.leader.name == "Hero", "Leader name should be preserved"

runner.run_test("Party.__init__ accepts leader argument", test_party_constructor_with_leader)
runner.run_test("Party.__init__ works without leader", test_party_constructor_without_leader)
runner.run_test("Party serialization preserves leader", test_party_serialization_with_leader)

# ==============================================================================
# TEST 3: RelationshipManager - add_npc() method exists and works
# ==============================================================================

def test_relationship_manager_add_npc():
    """Test RelationshipManager.add_npc() method."""
    rel_mgr = RelationshipManager()
    
    # Should not raise AttributeError
    npc = rel_mgr.add_npc("Barkeep", "Tavern owner")
    
    assert npc is not None, "add_npc should return NPC object"
    assert npc.name == "Barkeep", "NPC name should be set"
    assert npc.role == "Tavern owner", "NPC role should be set"
    assert "Barkeep" in rel_mgr.npcs, "NPC should be added to npcs dict"

def test_relationship_manager_npcs_dict():
    """Test RelationshipManager has npcs dict."""
    rel_mgr = RelationshipManager()
    
    rel_mgr.add_npc("Barkeep", "Tavern owner")
    rel_mgr.add_npc("Elara", "Ranger")
    rel_mgr.add_npc("Thorne", "Guard Captain")
    
    assert hasattr(rel_mgr, 'npcs'), "RelationshipManager should have npcs attribute"
    assert isinstance(rel_mgr.npcs, dict), "npcs should be a dict"
    assert len(rel_mgr.npcs) == 3, f"Should have 3 NPCs, got {len(rel_mgr.npcs)}"
    
    # Check iteration works
    count = 0
    for npc_name, npc in rel_mgr.npcs.items():
        assert isinstance(npc_name, str), "NPC name should be string"
        assert hasattr(npc, 'disposition'), "NPC should have disposition"
        count += 1
    
    assert count == 3, f"Should iterate 3 NPCs, got {count}"

def test_relationship_manager_npc_serialization():
    """Test RelationshipManager NPCs are serialized."""
    rel_mgr = RelationshipManager()
    rel_mgr.add_npc("Barkeep", "Tavern owner")
    rel_mgr.add_npc("Elara", "Ranger")
    
    data = rel_mgr.to_dict()
    
    assert "npcs" in data, "Serialized data should have npcs key"
    assert len(data["npcs"]) == 2, "Should have 2 NPCs in serialized data"
    
    # Deserialize
    rel_mgr2 = RelationshipManager.from_dict(data)
    assert len(rel_mgr2.npcs) == 2, "Deserialized manager should have 2 NPCs"
    assert "Barkeep" in rel_mgr2.npcs, "Barkeep should be in deserialized NPCs"
    assert "Elara" in rel_mgr2.npcs, "Elara should be in deserialized NPCs"

runner.run_test("RelationshipManager.add_npc() method works", test_relationship_manager_add_npc)
runner.run_test("RelationshipManager has npcs dict", test_relationship_manager_npcs_dict)
runner.run_test("RelationshipManager NPCs serialization works", test_relationship_manager_npc_serialization)

# ==============================================================================
# TEST 4: QuestLog - add_quest() accepts Quest objects
# ==============================================================================

def test_questlog_add_quest_with_object():
    """Test QuestLog.add_quest() accepts Quest objects."""
    quest_log = QuestLog()
    
    quest = Quest(
        title="Slay the Dragon",
        description="A dragon has been terrorizing the village",
        objectives=[
            QuestObjective(
                description="Defeat dragon",
                objective_type=ObjectiveType.KILL,
                target="Dragon",
                required_count=1
            )
        ],
        reward=QuestReward(xp=500, gold=1000),
        giver_npc="Mayor"
    )
    
    # Should not raise TypeError
    result = quest_log.add_quest(quest)
    
    assert result is quest, "Should return the quest object"
    assert len(quest_log.quests) == 1, "Quest should be added to log"

def test_questlog_add_quest_with_fields():
    """Test QuestLog.add_quest() still works with individual fields."""
    quest_log = QuestLog()
    
    result = quest_log.add_quest(
        title="Find the Crystal",
        description="A magical crystal is hidden in the cave",
        reward=QuestReward(xp=300, gold=500),
        giver_npc="Wizard"
    )
    
    assert result is not None, "Should return Quest object"
    assert result.title == "Find the Crystal", "Title should be set"
    assert result.giver_npc == "Wizard", "giver_npc should be set"
    assert len(quest_log.quests) == 1, "Quest should be added to log"

def test_questlog_add_quest_with_reward_fields():
    """Test QuestLog.add_quest() works with reward_xp/reward_description."""
    quest_log = QuestLog()
    
    # This is how narrator.py calls it
    result = quest_log.add_quest(
        title="Test Quest",
        description="Test Description",
        objectives=["Objective 1"],
        reward_xp=100,
        reward_description="Experience and loot"
    )
    
    assert result is not None, "Should return Quest object"
    assert result.reward.xp == 100, "Reward XP should be set"
    assert len(quest_log.quests) == 1, "Quest should be added to log"

runner.run_test("QuestLog.add_quest() accepts Quest objects", test_questlog_add_quest_with_object)
runner.run_test("QuestLog.add_quest() works with individual fields", test_questlog_add_quest_with_fields)
runner.run_test("QuestLog.add_quest() works with reward_xp parameter", test_questlog_add_quest_with_reward_fields)

# ==============================================================================
# TEST 5: EventType enum - CONFLICT value exists
# ==============================================================================

def test_event_type_conflict():
    """Test EventType.CONFLICT exists."""
    # Should not raise AttributeError
    conflict = EventType.CONFLICT
    
    assert conflict is not None, "CONFLICT should exist"
    assert conflict.value == "Conflict", "CONFLICT value should be 'Conflict'"

def test_event_type_all_values():
    """Test all EventType enum values."""
    expected_types = [
        "WEATHER", "POLITICAL", "ECONOMIC", "MAGICAL",
        "NATURAL_DISASTER", "SOCIAL", "COMBAT", "SUPERNATURAL", "CONFLICT"
    ]
    
    for type_name in expected_types:
        assert hasattr(EventType, type_name), f"EventType should have {type_name}"
        event_type = getattr(EventType, type_name)
        assert isinstance(event_type, EventType), f"{type_name} should be EventType"

def test_event_manager_with_conflict():
    """Test EventManager can create events with CONFLICT type."""
    from rag_quest.engine.events import WorldEvent, EventSeverity
    
    event = WorldEvent(
        name="Faction War",
        description="War breaks out between factions",
        event_type=EventType.CONFLICT,
        severity=EventSeverity.MAJOR,
        duration_turns=10
    )
    
    assert event.event_type == EventType.CONFLICT, "Event type should be CONFLICT"

runner.run_test("EventType.CONFLICT exists", test_event_type_conflict)
runner.run_test("EventType has all expected values", test_event_type_all_values)
runner.run_test("EventManager can create CONFLICT events", test_event_manager_with_conflict)

# ==============================================================================
# TEST 6: Character - get_available_abilities() method exists
# ==============================================================================

def test_character_get_available_abilities():
    """Test Character.get_available_abilities() method."""
    char = Character(
        name="Aragorn",
        race=Race.HUMAN,
        character_class=CharacterClass.FIGHTER
    )
    
    # Should not raise AttributeError
    abilities = char.get_available_abilities()
    
    assert abilities is not None, "get_available_abilities should return list"
    assert isinstance(abilities, list), "Should return a list"

def test_character_available_abilities_content():
    """Test Character.get_available_abilities() returns correct abilities."""
    char = Character(
        name="Mage",
        race=Race.ELF,
        character_class=CharacterClass.MAGE
    )
    
    abilities = char.get_available_abilities()
    
    # At level 1, Mage should have Fireball
    assert len(abilities) > 0, "Mage should have some abilities"
    assert "Fireball" in abilities, "Mage should have Fireball at level 1"

def test_character_abilities_after_levelup():
    """Test Character.get_available_abilities() changes with level."""
    char = Character(
        name="Cleric",
        race=Race.HUMAN,
        character_class=CharacterClass.CLERIC
    )
    
    abilities_lvl1 = char.get_available_abilities()
    assert "Divine Heal" in abilities_lvl1, "Cleric should have Divine Heal at level 1"
    
    # Simulate level up
    char.level = 2
    char._unlock_new_abilities()
    
    abilities_lvl2 = char.get_available_abilities()
    assert "Smite" in abilities_lvl2, "Cleric should have Smite at level 2"

runner.run_test("Character.get_available_abilities() method exists", test_character_get_available_abilities)
runner.run_test("Character.get_available_abilities() returns correct abilities", test_character_available_abilities_content)
runner.run_test("Character abilities change with level", test_character_abilities_after_levelup)

# ==============================================================================
# INTEGRATION TEST: Full GameState with all systems
# ==============================================================================

def test_full_game_state_integration():
    """Test all fixed systems working together independently."""
    # Create character
    player = Character(
        name="Hero",
        race=Race.HUMAN,
        character_class=CharacterClass.FIGHTER
    )
    
    # Create world
    world = World(
        name="Forgotten Realms",
        setting="Medieval Fantasy",
        tone="Adventurous"
    )
    
    # Test inventory
    inventory = Inventory(max_weight=100.0)
    inventory.add_item("Sword", "Iron sword", quantity=1)
    inv_text = inventory.list_items()
    assert isinstance(inv_text, str), "Inventory text should be string"
    assert "Sword" in inv_text, "Sword should appear in inventory"
    
    # Test party with leader
    party_member = PartyMember(
        name="Companion",
        race="Elf",
        character_class="Ranger"
    )
    party = Party(max_size=4, leader=player)
    party.add_member(party_member)
    assert party.leader.name == "Hero", "Party leader should be set"
    
    # Test relationships with NPCs
    relationships = RelationshipManager()
    relationships.add_npc("Barkeep", "Tavern owner")
    relationships.add_npc("Merchant", "Trader")
    assert len(relationships.npcs) == 2, "Should have 2 NPCs"
    
    # Test quests
    quest_log = QuestLog()
    quest = Quest(
        title="Main Quest",
        description="The main storyline",
        giver_npc="King"
    )
    quest_log.add_quest(quest)
    active_quests = quest_log.get_active_quests()
    assert len(active_quests) == 1, "Should have 1 active quest"
    
    # Test events with CONFLICT type
    from rag_quest.engine.events import WorldEvent, EventSeverity
    event_manager = EventManager()
    event = WorldEvent(
        name="Conflict",
        description="War breaks out",
        event_type=EventType.CONFLICT,
        severity=EventSeverity.MAJOR,
        duration_turns=5
    )
    event_manager.active_events.append(event)
    assert len(event_manager.active_events) == 1, "Should have 1 active event"
    
    # Test character abilities
    char_abilities = player.get_available_abilities()
    assert len(char_abilities) > 0, "Character should have abilities"
    assert "Power Strike" in char_abilities, "Fighter should have Power Strike"

runner.run_test("Full GameState integration with all systems", test_full_game_state_integration)

# ==============================================================================
# ADVANCED INTEGRATION: 30 simulation turns
# ==============================================================================

def test_30_turn_simulation():
    """Run 30 simulated game turns exercising all systems."""
    # Create character
    player = Character(
        name="Adventurer",
        race=Race.HUMAN,
        character_class=CharacterClass.RANGER
    )
    
    # Create world
    world = World(
        name="Test World",
        setting="Fantasy",
        tone="Epic"
    )
    
    # Setup: Create all systems independently
    inventory = Inventory(max_weight=150.0)
    relationships = RelationshipManager()
    quest_log = QuestLog()
    party = Party(max_size=4, leader=player)
    event_manager = EventManager()
    
    relationships.add_npc("Mentor", "Wise guide")
    relationships.add_npc("Enemy", "Rival")
    
    quest1 = Quest(title="Quest 1", description="First task", giver_npc="Mentor")
    quest2 = Quest(title="Quest 2", description="Second task", giver_npc="Mentor")
    quest_log.add_quest(quest1)
    quest_log.add_quest(quest2)
    
    companion = PartyMember(
        name="Sidekick",
        race="Halfling",
        character_class="Rogue"
    )
    party.add_member(companion)
    
    # Simulate 30 turns
    for turn in range(1, 31):
        # Turn action: Add inventory items
        if turn % 5 == 0:
            inventory.add_item(f"Potion {turn}", f"Health potion", quantity=1)
        
        # Turn action: Modify relationships
        if turn % 3 == 0:
            relationships.modify_relationship("Mentor", 5, "Helped with task")
        
        # Turn action: Advance time
        world.advance_time()
        
        # Turn action: Check abilities
        abilities = player.get_available_abilities()
        assert len(abilities) > 0, f"Should have abilities at turn {turn}"
        
        # Turn action: Potentially trigger events
        if turn % 7 == 0:
            event = event_manager.check_for_events(turn, event_chance=0.3)
            if event:
                assert event.event_type in EventType, f"Invalid event type at turn {turn}"
    
    # Verify final state
    assert world.day_number > 0, "Time should have advanced"
    assert len(inventory.items) > 0, "Should have inventory items"
    assert len(relationships.npcs) == 2, "Should have 2 NPCs"
    assert len(quest_log.quests) == 2, "Should have 2 quests"
    assert len(party.members) == 1, "Should have 1 companion"

runner.run_test("30-turn simulation of all systems", test_30_turn_simulation)

# ==============================================================================
# PRINT SUMMARY
# ==============================================================================

success = runner.summary()
sys.exit(0 if success else 1)
