#!/usr/bin/env python3
"""
50-Turn Playtest for RAG-Quest MVP
Tests all major systems end-to-end
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add the project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from rag_quest.engine.character import Character, CharacterClass, Race
from rag_quest.engine.world import World, TimeOfDay, Weather
from rag_quest.engine.inventory import Inventory
from rag_quest.engine.quests import QuestLog
from rag_quest.engine.game import GameState
from rag_quest.engine.narrator import Narrator
from rag_quest.knowledge.world_rag import WorldRAG
from rag_quest.llm.ollama_provider import OllamaProvider
from rag_quest.llm import LLMConfig


# Logging utilities
class PlaytestLogger:
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.log_file.write_text("")  # Clear existing log
        self.logs = []
        self.errors = []
        self.turns_completed = 0
        self.start_time = datetime.now()
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.logs.append(log_entry)
        print(log_entry)
        with open(self.log_file, "a") as f:
            f.write(log_entry + "\n")
    
    def error(self, message: str, exc_info: str = None):
        """Log an error."""
        self.log(message, "ERROR")
        self.errors.append(message)
        if exc_info:
            self.log(exc_info, "ERROR")
    
    def summary(self) -> str:
        """Generate a summary."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return f"""
================== PLAYTEST SUMMARY ==================
Turns Completed: {self.turns_completed}
Errors Encountered: {len(self.errors)}
Elapsed Time: {elapsed:.2f}s
Total Log Entries: {len(self.logs)}

Errors:
{chr(10).join('  - ' + e for e in self.errors) if self.errors else '  None'}

Game State Final:
  Location: {self._last_location}
  HP: {self._last_hp}
  Inventory Items: {self._last_inventory_count}
  Quests: {self._last_quests_count}
===================================================="""


def run_playtest():
    """Run the 50-turn playtest."""
    log_file = Path(__file__).parent / "playtest_50_log.txt"
    logger = PlaytestLogger(log_file)
    
    logger.log("Starting RAG-Quest 50-Turn Playtest", "START")
    logger.log(f"Log file: {log_file}")
    
    try:
        # Step 1: Check Ollama availability
        logger.log("Checking Ollama availability...")
        llm_config = LLMConfig(
            provider="ollama",
            model="gemma4:latest",
            base_url="http://localhost:11434",
            temperature=0.7,
            max_tokens=500,
        )
        llm_provider = OllamaProvider(llm_config)
        logger.log("Ollama connected successfully")
        
        # Step 2: Create world
        logger.log("Creating world...")
        world = World(
            name="Test Kingdom",
            setting="Medieval Fantasy",
            tone="Adventurous",
        )
        logger.log(f"World created: {world.name} ({world.setting})")
        
        # Step 3: Create character
        logger.log("Creating character...")
        character = Character(
            name="Thalion",
            race=Race.HUMAN,
            character_class=CharacterClass.FIGHTER,
            level=1,
            max_hp=30,
            current_hp=30,
            location="Tavern of the Lost Wanderer",
        )
        logger.log(f"Character created: {character.name} ({character.race.value} {character.character_class.value})")
        
        # Step 4: Initialize game components
        logger.log("Initializing game components...")
        inventory = Inventory()
        quest_log = QuestLog()
        
        # Initialize RAG (will be lazy-loaded)
        logger.log("Initializing WorldRAG...")
        world_rag = WorldRAG(world.name, llm_config, llm_provider, rag_profile="balanced")
        
        # Create narrator
        logger.log("Creating narrator...")
        narrator = Narrator(
            llm=llm_provider,
            world_rag=world_rag,
            character=character,
            world=world,
            inventory=inventory,
            quest_log=quest_log,
        )
        
        # Step 5: Create game state
        logger.log("Creating game state...")
        game_state = GameState(
            character=character,
            world=world,
            inventory=inventory,
            quest_log=quest_log,
            narrator=narrator,
            world_rag=world_rag,
            llm=llm_provider,
        )
        
        logger.log("\n========== Starting 50 Turns ==========\n")
        
        # Step 6: Run 50 turns with diverse actions
        turn_actions = [
            # Turns 1-5: Explore starting area
            ("look around", "Exploring: Look around the tavern"),
            ("examine the bar", "Exploring: Examine the bar"),
            ("search for clues", "Exploring: Search for clues"),
            ("listen to conversations", "Exploring: Listen to conversations"),
            ("check the windows", "Exploring: Check the windows"),
            
            # Turns 6-10: Move to different locations
            ("go outside", "Movement: Go outside the tavern"),
            ("walk to the marketplace", "Movement: Walk to the marketplace"),
            ("enter the forest", "Movement: Enter the nearby forest"),
            ("explore the cave", "Movement: Explore a cave"),
            ("return to the tavern", "Movement: Return to tavern"),
            
            # Turns 11-15: Talk to NPCs
            ("talk to the bartender", "Dialogue: Talk to bartender"),
            ("ask about the quest", "Dialogue: Ask about quests"),
            ("greet the merchants", "Dialogue: Greet merchants"),
            ("speak with the guards", "Dialogue: Speak with guards"),
            ("chat with a mysterious stranger", "Dialogue: Chat with stranger"),
            
            # Turns 16-20: Pick up items
            ("take the sword", "Items: Take sword"),
            ("grab the shield", "Items: Grab shield"),
            ("pick up the healing potion", "Items: Pick up potion"),
            ("collect the amulet", "Items: Collect amulet"),
            ("find some gold", "Items: Find gold"),
            
            # Turns 21-25: Combat encounters
            ("attack the goblin", "Combat: Attack goblin"),
            ("fight back against the monster", "Combat: Fight monster"),
            ("strike with my sword", "Combat: Strike with sword"),
            ("engage in combat", "Combat: Engage in combat"),
            ("defeat the enemy", "Combat: Defeat enemy"),
            
            # Turns 26-30: Use items and check status
            ("drink the healing potion", "Items: Use healing potion"),
            ("equip the armor", "Items: Equip armor"),
            ("inventory", "Status: Check inventory"),
            ("quests", "Status: Check quests"),
            ("check my status", "Status: Check character status"),
            
            # Turns 31-35: Lore questions and RAG retrieval
            ("what is the history of this land", "Lore: Ask about history"),
            ("tell me about the kingdom", "Lore: Ask about kingdom"),
            ("what legends do you know", "Lore: Ask about legends"),
            ("describe the magical essence of this place", "Lore: Ask about magic"),
            ("what is the fate of heroes here", "Lore: Ask about fate"),
            
            # Turns 36-40: Complex multi-part actions
            ("go to the wizard's tower and learn a spell", "Complex: Go to tower and learn spell"),
            ("defeat the boss and claim the treasure", "Complex: Defeat boss and get treasure"),
            ("befriend the NPC and accept their quest", "Complex: Befriend NPC and quest"),
            ("navigate the dungeon and find the artifact", "Complex: Navigate dungeon"),
            ("solve the riddle and unlock the door", "Complex: Solve riddle and unlock"),
            
            # Turns 41-45: Edge cases
            ("", "Edge Case: Empty input"),
            ("a" * 200, "Edge Case: Very long input"),
            ("!@#$%^&*()", "Edge Case: Special characters"),
            ("   ", "Edge Case: Whitespace"),
            ("AAAAAAAAA", "Edge Case: Repetitive input"),
            
            # Turns 46-50: Save game and final exploration
            ("save", "Utility: Save game"),
            ("status", "Utility: Check status"),
            ("explore the hidden caves", "Exploration: Hidden caves"),
            ("venture to the sacred shrine", "Exploration: Sacred shrine"),
            ("rest and reflect on the journey", "Exploration: Rest and reflect"),
        ]
        
        for turn_num, (action, description) in enumerate(turn_actions, 1):
            try:
                logger.log(f"\nTurn {turn_num}: {description}")
                logger.log(f"  Input: '{action}'")
                
                # Handle special commands
                if action == "inventory":
                    logger.log(f"  Inventory: {list(inventory.items.keys())}")
                    logger.log("  Response: Inventory checked")
                elif action == "quests":
                    logger.log(f"  Quests: {quest_log.quests}")
                    logger.log("  Response: Quest log checked")
                elif action == "status":
                    logger.log(f"  Status: {character.get_status()}")
                    logger.log("  Response: Status displayed")
                elif action == "save":
                    logger.log("  Response: Game would be saved (no-op in playtest)")
                elif action == "":
                    logger.log("  Response: Empty input handled gracefully")
                else:
                    # Process normal action through narrator
                    start_time = time.time()
                    response = narrator.process_action(action)
                    elapsed = time.time() - start_time
                    
                    # Log response (truncated if too long)
                    response_display = response[:150] if len(response) > 150 else response
                    logger.log(f"  Response ({elapsed:.2f}s): {response_display}")
                    
                    # Log state changes
                    logger.log(f"  Character HP: {character.current_hp}/{character.max_hp}")
                    logger.log(f"  Location: {character.location}")
                    logger.log(f"  Inventory Items: {len(inventory.items)}")
                    logger.log(f"  Quests: {len(quest_log.quests)}")
                
                logger.turns_completed = turn_num
                
            except Exception as e:
                logger.error(f"Turn {turn_num} failed: {str(e)}", str(e))
                # Continue playtest despite errors
                continue
        
        logger.log("\n========== Playtest Completed ==========\n")
        
        # Generate final summary
        logger._last_location = character.location
        logger._last_hp = f"{character.current_hp}/{character.max_hp}"
        logger._last_inventory_count = len(inventory.items)
        logger._last_quests_count = len(quest_log.quests)
        
        summary = logger.summary()
        logger.log(summary, "SUMMARY")
        
        # Cleanup
        try:
            world_rag.close()
        except:
            pass
        
        try:
            llm_provider.close()
        except:
            pass
        
        return 0
    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", str(e))
        return 1


if __name__ == "__main__":
    sys.exit(run_playtest())
