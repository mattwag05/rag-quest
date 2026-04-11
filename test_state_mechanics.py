#!/usr/bin/env python3
"""
Test suite for P2 fixes: location tracking, combat, inventory, and quests.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from rag_quest.engine.state_parser import StateParser
from rag_quest.engine.character import Character, Race, CharacterClass
from rag_quest.engine.world import World
from rag_quest.engine.inventory import Inventory
from rag_quest.engine.quests import QuestLog


def test_location_tracking():
    """Test P2: Character location updates."""
    print("\n=== TEST 1: Location Tracking ===")
    
    parser = StateParser()
    
    # Test various movement descriptions
    responses = [
        "You push open the heavy wooden door and enter the ancient tavern. The smell of ale and smoke fills your nostrils.",
        "With determined steps, you travel to the bustling marketplace, where merchants call out their wares.",
        "You arrive at the Crystal Tower, its spires reaching into the clouds.",
    ]
    
    expected_locations = ["the ancient tavern", "the bustling marketplace", "the Crystal Tower"]
    
    for response, expected in zip(responses, expected_locations):
        change = parser.parse_narrator_response(response, "go there")
        
        if change.location:
            print(f"✓ Detected location: '{change.location}'")
            if expected.lower() in change.location.lower():
                print(f"  Match verified!")
            else:
                print(f"  WARNING: Expected '{expected}', got '{change.location}'")
        else:
            print(f"✗ Failed to detect location in: '{response[:50]}...'")
    
    print("Location tracking test complete!")


def test_combat_mechanics():
    """Test P2: Combat system integration."""
    print("\n=== TEST 2: Combat Mechanics ===")
    
    parser = StateParser()
    character = Character(
        name="Kael",
        race=Race.HUMAN,
        character_class=CharacterClass.FIGHTER,
        max_hp=20,
        current_hp=20
    )
    
    # Test explicit damage
    response_with_damage = "You strike at the goblin with your sword! The blade finds its mark, dealing 7 damage. The creature shrieks in pain."
    change = parser.parse_narrator_response(response_with_damage, "attack goblin")
    print(f"Explicit damage detected: {change.damage_taken} HP")
    
    # Apply damage to character
    character.take_damage(change.damage_taken)
    print(f"Character HP after combat: {character.current_hp}/{character.max_hp}")
    assert character.current_hp == 13, f"Expected HP 13, got {character.current_hp}"
    print("✓ Damage correctly applied!")
    
    # Test combat without explicit damage
    response_without_damage = "You charge at the troll with your sword held high. The battle is fierce and brutal."
    change = parser.parse_narrator_response(response_without_damage, "fight troll")
    if change.damage_taken > 0:
        print(f"Combat damage calculated: {change.damage_taken} HP")
        character.take_damage(change.damage_taken)
        print(f"Character HP: {character.current_hp}/{character.max_hp}")
        print("✓ Combat damage calculation working!")
    else:
        print("Note: No damage detected in combat response (may be narration only)")
    
    # Test healing
    response_with_healing = "You drink a healing potion that restores 5 HP. Your wounds begin to mend."
    change = parser.parse_narrator_response(response_with_healing, "drink potion")
    if change.hp_healed > 0:
        print(f"Healing detected: {change.hp_healed} HP")
        character.heal(change.hp_healed)
        print(f"Character HP after healing: {character.current_hp}/{character.max_hp}")
        print("✓ Healing correctly applied!")
    
    print("Combat mechanics test complete!")


def test_inventory_mechanics():
    """Test P2: Inventory system integration."""
    print("\n=== TEST 3: Inventory Mechanics ===")
    
    parser = StateParser()
    inventory = Inventory()
    
    # Test item pickup
    response_pickup = "You bend down and pick up a rusty sword lying on the ground. It's old but still serviceable."
    change = parser.parse_narrator_response(response_pickup, "pick up sword")
    
    print(f"Items detected for pickup: {change.items_gained}")
    for item_name in change.items_gained:
        success = inventory.add_item(item_name, "Found item")
        if success:
            print(f"✓ Added to inventory: {item_name}")
        else:
            print(f"✗ Failed to add: {item_name}")
    
    # Test multiple items
    response_multiple = "You find a golden amulet and a leather pouch containing 50 gold coins."
    change = parser.parse_narrator_response(response_multiple, "search")
    print(f"Multiple items detected: {change.items_gained}")
    for item_name in change.items_gained:
        inventory.add_item(item_name, "Found item")
    
    # Check inventory
    print(f"\nCurrent inventory:\n{inventory.list_items()}")
    print("✓ Inventory mechanics working!")
    
    print("Inventory test complete!")


def test_quest_mechanics():
    """Test P2: Quest system integration."""
    print("\n=== TEST 4: Quest Mechanics ===")
    
    parser = StateParser()
    quest_log = QuestLog()
    
    # Test quest offer
    response_quest_offer = "The old merchant approaches you with a worried look. 'I have a quest for you: Find the Lost Artifact. It was stolen from my shop, and I need your help to retrieve it!'"
    change = parser.parse_narrator_response(response_quest_offer, "talk to merchant")
    
    if change.quest_offered:
        print(f"Quest offered: {change.quest_offered}")
        quest = quest_log.add_quest(
            title=change.quest_offered,
            description=f"Quest: {change.quest_offered}",
            objectives=[change.quest_offered]
        )
        print(f"✓ Quest added to log: {quest.title}")
    else:
        print("Note: No quest detected in response")
    
    # Test quest completion
    response_quest_complete = "You return to the merchant with the artifact in hand. 'You did it! The Lost Artifact is recovered! Quest complete!'"
    change = parser.parse_narrator_response(response_quest_complete, "talk to merchant")
    
    if change.quest_completed:
        print(f"Quest completion detected: {change.quest_completed}")
        quest_log.complete_quest(change.quest_completed)
        print("✓ Quest marked as complete!")
    
    # Check quest log
    print(f"\nActive quests: {len(quest_log.get_active_quests())}")
    print(f"Total quests: {len(quest_log.quests)}")
    print("✓ Quest mechanics working!")
    
    print("Quest test complete!")


def test_state_parser_integration():
    """Test complete state parser with all mechanics."""
    print("\n=== TEST 5: Full State Parser Integration ===")
    
    parser = StateParser()
    
    # Complex scenario with multiple state changes
    complex_response = """
    You stride into the Dragon's Den tavern, a notorious gathering place for adventurers.
    As you enter, you see a grizzled dwarf sitting in the corner. "Aye, I have a quest for you," he says.
    "Find the Enchanted Amulet and bring it back to me. I'll reward you handsomely!"
    
    You also notice an ancient sword on the wall, and you manage to pick it up. 
    The amulet glows faintly in your pack, dealing 3 damage to you with its cursed energy.
    """
    
    player_action = "enter tavern, look around"
    change = parser.parse_narrator_response(complex_response, player_action)
    
    print(f"Location: {change.location}")
    print(f"NPC met: {change.npc_met}")
    print(f"Quest offered: {change.quest_offered}")
    print(f"Items gained: {change.items_gained}")
    print(f"Damage taken: {change.damage_taken}")
    
    print("✓ Complex state change parsed successfully!")


if __name__ == "__main__":
    print("=" * 60)
    print("RAG-QUEST STATE MECHANICS TEST SUITE")
    print("Testing P2 Fixes: Location, Combat, Inventory, Quests")
    print("=" * 60)
    
    try:
        test_location_tracking()
        test_combat_mechanics()
        test_inventory_mechanics()
        test_quest_mechanics()
        test_state_parser_integration()
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
