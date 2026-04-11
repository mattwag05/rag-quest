#!/usr/bin/env python3
"""
Comprehensive 30+ turn playthrough test for RAG-Quest with Gemma 4 and Blue Rose lore.
Tests game functionality, RAG integration, and LLM response quality.
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
log_file = Path(__file__).parent / "playthrough_log.txt"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Set environment for non-interactive mode
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["OLLAMA_MODEL"] = "gemma4:latest"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

def test_playthrough():
    """Run comprehensive playthrough test."""
    logger.info("=" * 80)
    logger.info("RAG-QUEST COMPREHENSIVE PLAYTHROUGH TEST")
    logger.info(f"Started: {datetime.now()}")
    logger.info("=" * 80)

    try:
        # Import after env setup
        from rag_quest import config
        from rag_quest.llm import LLMConfig
        from rag_quest.engine.character import Character, Race, CharacterClass
        from rag_quest.engine.world import World
        from rag_quest.engine.inventory import Inventory
        from rag_quest.engine.quests import QuestLog
        from rag_quest.engine.narrator import Narrator
        from rag_quest.knowledge import WorldRAG

        logger.info("\n[PHASE 1] Initializing Configuration...")
        
        # Create minimal config
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
                "starting_location": "A quaint tavern near the Blue Rose",
                "lore_path": "/Users/matthewwagner/Desktop/The Blue Rose Adventurer's Guide 5E.pdf",
            },
            "character": {
                "name": "Kael",
                "race": "HUMAN",
                "class": "FIGHTER",
                "background": "A seasoned adventurer seeking the truth about the Blue Rose",
            },
        }
        
        logger.info("Config loaded successfully")

        logger.info("\n[PHASE 2] Loading LLM Provider...")
        llm_provider, llm_config = config.load_llm_provider(game_config)
        logger.info(f"LLM Provider: {llm_config.provider}")
        logger.info(f"Model: {llm_config.model}")

        logger.info("\n[PHASE 3] Creating World and Character...")
        world = config.create_world_from_config(game_config)
        character = config.create_character_from_config(game_config)
        logger.info(f"World: {world.name} ({world.setting})")
        logger.info(f"Character: {character.name} ({character.race.value} {character.character_class.value})")
        
        # Store reference to character's world
        character.world = world

        logger.info("\n[PHASE 4] Initializing RAG System...")
        world_rag = WorldRAG(world.name, llm_config, llm_provider)
        world_rag.initialize()
        logger.info("RAG system initialized")

        logger.info("\n[PHASE 5] Ingesting Blue Rose PDF Lore...")
        pdf_path = game_config["world"]["lore_path"]
        if Path(pdf_path).exists():
            try:
                logger.info(f"Starting PDF ingestion: {pdf_path}")
                world_rag.ingest_file(pdf_path)
                logger.info("PDF ingested successfully!")
            except Exception as e:
                logger.error(f"Error ingesting PDF: {e}")
                logger.warning("Continuing without lore - RAG queries may be limited")
        else:
            logger.error(f"PDF not found: {pdf_path}")

        logger.info("\n[PHASE 6] Creating Game Objects...")
        inventory = Inventory()
        quest_log = QuestLog()
        narrator = Narrator(llm_provider, world_rag, character, world)
        logger.info("Game objects created")

        logger.info("\n[PHASE 7] Starting 30+ Turn Playthrough...")
        logger.info("=" * 80)

        # Test script with 35+ turns covering all gameplay aspects  
        turns = []
        turns = [
            # Turns 1-3: Character introduction and world discovery
            (1, "Look around and get your bearings"),
            (2, "Ask the tavern keeper about what's happening in this realm"),
            (3, "Check what supplies you're carrying"),
            
            # Turns 4-8: Explore locations and NPCs
            (4, "Leave the tavern and explore the nearby streets"),
            (5, "Try to find someone who might know about the Blue Rose"),
            (6, "Listen to rumors and gossip from locals"),
            (7, "Ask about any recent strange occurrences or mysteries"),
            (8, "Find a map or information about nearby locations"),
            
            # Turns 9-13: Talk to NPCs and gather information
            (9, "Talk to an old sage about ancient lore"),
            (10, "Ask about the history of the Blue Rose"),
            (11, "Inquire about magical artifacts in this world"),
            (12, "Ask if anyone has seen unusual travelers"),
            (13, "Try to learn about factions or organizations"),
            
            # Turns 14-17: Items and inventory
            (14, "Search for useful items in the area"),
            (15, "Check your current inventory carefully"),
            (16, "Try to purchase supplies from a merchant"),
            (17, "Examine any mysterious objects you find"),
            
            # Turns 18-22: Specific lore questions to test RAG
            (18, "Tell me everything you know about the Blue Rose lore"),
            (19, "What are the most important factions in this world?"),
            (20, "Describe the geography and major locations"),
            (21, "What kinds of magic are prominent here?"),
            (22, "Who are the legendary heroes of this realm?"),
            
            # Turns 23-26: Edge cases and interesting scenarios
            (23, "Try to do something completely absurd"),
            (24, "Ask about something that's probably not in the lore"),
            (25, "Perform a complex multi-step action"),
            (26, "Say something very long and complex"),
            
            # Turns 27-30+: Advanced gameplay
            (27, "Attempt to find a hidden path or secret"),
            (28, "Interact with multiple NPCs in sequence"),
            (29, "Make a major decision that affects the world"),
            (30, "Reflect on your adventure so far"),
            (31, "Attempt a dangerous action"),
            (32, "Ask for prophecy or guidance"),
            (33, "Try to find treasure or artifacts"),
            (34, "Engage in combat with an enemy"),
            (35, "Use an ability or skill specific to your class"),
        ]

        results = []
        for turn_num, action in turns:
            logger.info(f"\n--- TURN {turn_num} ---")
            logger.info(f"Action: {action}")
            
            try:
                response = narrator.process_action(action)
                logger.info(f"Response (first 200 chars): {response[:200]}...")
                
                results.append({
                    "turn": turn_num,
                    "action": action,
                    "response": response,
                    "success": True,
                    "character_location": character.location,
                    "character_hp": f"{character.current_hp}/{character.max_hp}",
                })
                
            except Exception as e:
                logger.error(f"Error on turn {turn_num}: {e}")
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

        # Write detailed results
        results_file = Path(__file__).parent / "playthrough_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"\nDetailed results saved to: {results_file}")

        # Final statistics
        logger.info(f"\nGame State at End:")
        logger.info(f"Character: {character.name}")
        logger.info(f"Location: {character.location}")
        logger.info(f"HP: {character.current_hp}/{character.max_hp}")
        logger.info(f"Visited Locations: {len(character.world.visited_locations)}")
        logger.info(f"NPCs Met: {len(character.world.npcs_met)}")
        logger.info(f"Items Discovered: {len(character.world.discovered_items)}")

        # Cleanup
        logger.info("\nCleaning up resources...")
        world_rag.close()
        llm_provider.close()
        logger.info("Resources cleaned up")

        logger.info(f"\nFinished: {datetime.now()}")
        logger.info("=" * 80)

        return successful_turns, failed_turns

    except Exception as e:
        logger.error(f"FATAL ERROR: {e}", exc_info=True)
        return 0, len(turns)


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
