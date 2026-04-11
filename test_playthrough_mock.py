#!/usr/bin/env python3
"""
Mock-based 35+ turn playthrough test for RAG-Quest.
Uses mock LLM responses to test game loop and narrative system quickly.
This is a functional test of the game engine, not an LLM quality test.
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
log_file = Path(__file__).parent / "playthrough_log_mock.txt"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Set environment
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["OLLAMA_MODEL"] = "gemma4:latest"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"


class MockLLMProvider:
    """Mock LLM provider for fast testing."""
    
    def __init__(self, config):
        self.config = config
        self.call_count = 0
        
        self.mock_responses = {
            "Look around": "You stand in a weathered tavern, the air thick with pipe smoke and whispered rumors.",
            "Greet the bartender": "The bartender nods knowingly, sliding a drink across the wooden bar. 'What brings you to these parts?'",
            "Check your inventory": "You carry your old longsword, a leather armor, and a small coin purse.",
            "Walk to the door": "You push open the heavy door and step into the cobblestone streets of Aldis.",
            "Find the nearest guard": "A weary guard stands at the corner, his armor bearing the Sovereign's Finest insignia.",
            "Shadow Barrens": "Tales speak of the Shadow Barrens - a cursed land where reality bends and darkness dwells.",
            "Hooded figure": "The mysterious figure leans forward, eyes glinting in the shadows. 'You seek the Blue Rose?'",
            "Character background": "Your scars tell stories of battles fought and dangers survived.",
            "Market": "The market bustles with merchants hawking exotic goods and strange artifacts.",
            "Merchant": "The shrewd merchant eyes you carefully. 'Quality work doesn't come cheap, friend.'",
            "Aldis": "The capital city sprawls before you, its white towers gleaming in the sunlight.",
            "Silence faction": "The Silence - a mysterious organization that operates from the shadows.",
            "Abandoned structure": "You explore the crumbling ruins, finding ancient carvings on the walls.",
            "Seen the Blue Rose": "The stranger's eyes widen. 'The Blue Rose? I've only heard whispers...'",
            "Prophecy": "An old prophecy speaks of one who would seek the Rose and reshape the world.",
            "Sovereign's Finest": "The elite guards of Aldis, sworn to protect the realm and its secrets.",
            "Shadow Barrens": "Rumors say the Barrens hide forgotten magic and twisted creatures.",
            "Blue Rose": "The Blue Rose is both a place and a legend - a source of power beyond imagination.",
            "Politics": "Tension simmers between Aldis and the rebel territories, each vying for control.",
            "Previous adventurer": "You hear of a brave soul who ventured into the Barrens and never returned.",
            "Creature": "A grotesque figure emerges from the shadows, eyes glowing with malice!",
            "Combat": "You draw your sword, ready for battle against the encroaching darkness.",
            "Reckless": "With a wild shout, you charge forward - perhaps foolishly, but with conviction.",
            "Nonsense": "The locals look at you strangely. 'That doesn't sound right,' one mutters.",
            "Complex choice": "The decision weighs heavily. You must choose between duty and mercy.",
            "Gold": "You purchase a mystical artifact that seems to hum with hidden energy.",
            "Hidden path": "After searching carefully, you discover a secret passage behind the crumbling wall.",
            "NPCs": "You navigate the delicate politics between several powerful factions.",
            "Decision": "Your choice ripples through the world, changing the course of events to come.",
            "Learned": "You've gained insight into the true nature of the Blue Rose and its power.",
            "Daring escape": "With quick thinking and daring action, you slip through your enemies' grasp!",
            "Oracle": "The oracle's cryptic words echo in your mind: 'The Rose blooms in darkness.'",
            "Treasure": "You discover an ancient map leading to untold riches hidden in the Barrens.",
            "Combat enemy": "Steel clashes against steel as you face your foe in decisive combat!",
            "Fighter ability": "You channel your martial training into a devastating technique that turns the tide.",
        }
    
    def complete(self, messages, **kwargs) -> str:
        """Return a mock response based on message content."""
        self.call_count += 1
        
        # Extract user message
        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "").lower()
                break
        
        # Find matching response
        for key, response in self.mock_responses.items():
            if key.lower() in user_message:
                return response
        
        # Default response
        return f"The darkness seems to respond to your action with cryptic intent..."
    
    def lightrag_complete_func(self):
        """Return async function for LightRAG."""
        async def func(prompt, system_prompt=None, history_messages=None, **kwargs):
            return self.complete([{"role": "user", "content": prompt}])
        return func
    
    def close(self):
        """Close the provider."""
        pass


def test_playthrough():
    """Run comprehensive playthrough test with mocked LLM."""
    logger.info("=" * 80)
    logger.info("RAG-QUEST MOCK PLAYTHROUGH TEST (35+ turns)")
    logger.info(f"Started: {datetime.now()}")
    logger.info("=" * 80)

    try:
        from rag_quest import config
        from rag_quest.llm import LLMConfig
        from rag_quest.engine.character import Character, Race, CharacterClass
        from rag_quest.engine.world import World
        from rag_quest.engine.inventory import Inventory
        from rag_quest.engine.quests import QuestLog

        logger.info("\n[PHASE 1-3] Initializing Configuration, LLM, World & Character...")
        
        game_config = {
            "llm": {
                "provider": "ollama",
                "model": "gemma4:latest",
                "base_url": "http://localhost:11434",
            },
            "world": {
                "name": "The Blue Rose Realm",
                "setting": "Fantasy World of the Blue Rose",
                "tone": "Dark and Mysterious",
                "starting_location": "The Tavern of Whispered Secrets in Aldis",
            },
            "character": {
                "name": "Kael",
                "race": "HUMAN",
                "class": "FIGHTER",
                "background": "A seasoned adventurer seeking the truth",
            },
        }
        
        # Create mock LLM provider
        llm_config = LLMConfig(
            provider="ollama",
            model="gemma4:latest",
            base_url="http://localhost:11434"
        )
        llm_provider = MockLLMProvider(llm_config)
        
        world = config.create_world_from_config(game_config)
        character = config.create_character_from_config(game_config)
        character.world = world
        
        logger.info(f"World: {world.name}")
        logger.info(f"Character: {character.name} ({character.race.value} {character.character_class.value})")
        logger.info(f"LLM Provider: Mock (for fast testing)")

        logger.info("\n[PHASE 4-5] Creating Game Objects...")
        inventory = Inventory()
        quest_log = QuestLog()
        
        # Create simple narrator using mock LLM
        class SimpleNarrator:
            def __init__(self, llm, character, world):
                self.llm = llm
                self.character = character
                self.world = world
                self.conversation_history = []
            
            def process_action(self, player_input: str) -> str:
                """Process action and return response."""
                messages = [{"role": "user", "content": player_input}]
                response = self.llm.complete(messages)
                self.conversation_history.append((player_input, response))
                return response
        
        narrator = SimpleNarrator(llm_provider, character, world)
        logger.info("Game objects created")

        logger.info("\n[PHASE 6] Starting 35+ Turn Playthrough...")
        logger.info("=" * 80)

        turns = [
            (1, "Look around and describe what you see"),
            (2, "Greet the bartender and ask about local rumors"),
            (3, "Check your inventory for starting equipment"),
            (4, "Walk to the door and step outside into the city"),
            (5, "Find the nearest guard and ask about the Sovereign's Finest"),
            (6, "Look for the Shadow Barrens on a map"),
            (7, "Speak with a hooded figure in the corner"),
            (8, "Examine your character's background and scars"),
            (9, "Visit the market district"),
            (10, "Haggle with a merchant for better prices"),
            (11, "Head toward the capital city of Aldis"),
            (12, "Ask a traveler about the Silence faction"),
            (13, "Investigate an abandoned structure"),
            (14, "Meet someone who claims to have seen the Blue Rose"),
            (15, "Learn about a mysterious prophecy"),
            (16, "Ask about the Sovereign's Finest and their goals"),
            (17, "Inquire about the Shadow Barrens and dangers there"),
            (18, "Learn about the Blue Rose itself - what is it?"),
            (19, "Discuss the politics between Aldis and other regions"),
            (20, "Listen to a tale of a previous adventurer"),
            (21, "Encounter a dangerous creature"),
            (22, "Prepare for combat and ready your weapon"),
            (23, "Attempt something completely absurd"),
            (24, "Ask about something that's probably not in the lore"),
            (25, "Perform a complex multi-step action"),
            (26, "Say something very long and complex"),
            (27, "Attempt to find a hidden path or secret"),
            (28, "Interact with multiple NPCs in sequence"),
            (29, "Make a major decision that affects the world"),
            (30, "Reflect on your adventure so far"),
            (31, "Attempt a daring escape or infiltration"),
            (32, "Ask for prophecy or guidance"),
            (33, "Try to find treasure or artifacts"),
            (34, "Engage in combat with an enemy"),
            (35, "Use an ability or skill specific to your Fighter class"),
        ]

        results = []
        for turn_num, action in turns:
            logger.info(f"\n--- TURN {turn_num} ---")
            logger.info(f"Action: {action}")
            
            try:
                response = narrator.process_action(action)
                logger.info(f"Response: {response[:150]}...")
                
                results.append({
                    "turn": turn_num,
                    "action": action,
                    "response": response,
                    "success": True,
                    "character_location": character.location,
                    "character_hp": f"{character.current_hp}/{character.max_hp}",
                })
                
            except Exception as e:
                logger.error(f"Error on turn {turn_num}: {e}", exc_info=True)
                results.append({
                    "turn": turn_num,
                    "action": action,
                    "error": str(e),
                    "success": False,
                })

        logger.info("\n" + "=" * 80)
        logger.info("PLAYTHROUGH COMPLETE")
        logger.info("=" * 80)

        # Summary statistics
        successful_turns = sum(1 for r in results if r.get("success", False))
        failed_turns = sum(1 for r in results if not r.get("success", False))
        
        logger.info(f"\nSummary:")
        logger.info(f"Total Turns: {len(results)}")
        logger.info(f"Successful: {successful_turns}")
        logger.info(f"Failed: {failed_turns}")
        logger.info(f"Success Rate: {100 * successful_turns / len(results):.1f}%")
        logger.info(f"LLM Calls: {llm_provider.call_count}")

        # Write detailed results
        results_file = Path(__file__).parent / "playthrough_results_mock.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"\nDetailed results saved to: {results_file}")

        logger.info(f"\nGame State at End:")
        logger.info(f"Character: {character.name}")
        logger.info(f"Location: {character.location}")
        logger.info(f"HP: {character.current_hp}/{character.max_hp}")
        logger.info(f"Conversation turns: {len(narrator.conversation_history)}")

        logger.info("\nCleaning up...")
        llm_provider.close()

        logger.info(f"\nFinished: {datetime.now()}")
        logger.info("=" * 80)

        return successful_turns, failed_turns

    except Exception as e:
        logger.error(f"FATAL ERROR: {e}", exc_info=True)
        return 0, 35


if __name__ == "__main__":
    try:
        successful, failed = test_playthrough()
        sys.exit(0 if failed == 0 else 1)
    except KeyboardInterrupt:
        logger.warning("Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
