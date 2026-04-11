#!/usr/bin/env python3
"""
Fast 30+ turn playthrough test for RAG-Quest with Gemma 4.
Skips full LightRAG processing and uses direct LLM with Blue Rose context.
Tests game functionality and LLM response quality.
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
log_file = Path(__file__).parent / "playthrough_log_fast.txt"
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


def extract_pdf_text(pdf_path: str, max_pages: int = 20) -> str:
    """Extract text from first N pages of PDF for context."""
    from pathlib import Path
    import fitz  # pymupdf

    text_parts = []
    path = Path(pdf_path)
    
    if not path.exists():
        logger.warning(f"PDF not found: {pdf_path}")
        return ""
    
    try:
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        for page_num in range(min(max_pages, num_pages)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                text_parts.append(f"[Page {page_num + 1}]\n{text}")
        doc.close()
        
        logger.info(f"Extracted text from {min(max_pages, num_pages)} pages")
        return "\n\n".join(text_parts)
    except Exception as e:
        logger.error(f"Error extracting PDF: {e}", exc_info=True)
        return ""


def test_playthrough():
    """Run comprehensive playthrough test."""
    logger.info("=" * 80)
    logger.info("RAG-QUEST FAST PLAYTHROUGH TEST (30+ turns)")
    logger.info(f"Started: {datetime.now()}")
    logger.info("=" * 80)

    try:
        # Import after env setup
        from rag_quest import config
        from rag_quest.llm import LLMConfig, OllamaProvider
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
                "starting_location": "The Tavern of Whispered Secrets in Aldis",
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

        logger.info("\n[PHASE 4] Loading Blue Rose Lore Context...")
        pdf_path = game_config["world"]["lore_path"]
        blue_rose_context = ""
        if Path(pdf_path).exists():
            try:
                logger.info(f"Extracting text from PDF: {pdf_path}")
                blue_rose_context = extract_pdf_text(pdf_path, max_pages=15)
                logger.info(f"Loaded {len(blue_rose_context)} characters of Blue Rose lore")
            except Exception as e:
                logger.error(f"Error loading PDF: {e}")
                logger.warning("Continuing without lore - responses may be generic")
        else:
            logger.error(f"PDF not found: {pdf_path}")

        logger.info("\n[PHASE 5] Creating Game Objects...")
        inventory = Inventory()
        quest_log = QuestLog()
        
        # Create a simple narrator that uses manual context
        class SimpleNarrator:
            def __init__(self, llm, character, world, context=""):
                self.llm = llm
                self.character = character
                self.world = world
                self.context = context
                self.conversation_history = []
            
            def process_action(self, player_input: str) -> str:
                """Process action with Blue Rose context."""
                system_prompt = f"""You are the narrator of a dark fantasy adventure in the world of Blue Rose.
                
Character: {self.character.name} ({self.character.race.value} {self.character.character_class.value})
Location: {self.character.location}
HP: {self.character.current_hp}/{self.character.max_hp}
Tone: Mysterious, dark, with intricate politics and hidden dangers

Relevant lore from the Blue Rose world:
{self.context[:2000]}

Respond to the player's action with a short, immersive narrative response (1-3 sentences).
Include sensory details and maintain the dark tone of Blue Rose."""

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Action: {player_input}"}
                ]
                
                if self.conversation_history:
                    messages = [{"role": "system", "content": system_prompt}] + self.conversation_history + messages
                
                response = self.llm.complete(messages)
                self.conversation_history.append({"role": "user", "content": player_input})
                self.conversation_history.append({"role": "assistant", "content": response})
                
                # Keep history manageable
                if len(self.conversation_history) > 20:
                    self.conversation_history = self.conversation_history[-20:]
                
                return response
        
        narrator = SimpleNarrator(llm_provider, character, world, blue_rose_context)
        logger.info("Game objects created")

        logger.info("\n[PHASE 6] Starting 30+ Turn Playthrough...")
        logger.info("=" * 80)

        # Test script with 35+ turns covering all gameplay aspects
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
            
            # Turns 11-15: Exploration and NPCs
            (11, "Head toward the capital city of Aldis"),
            (12, "Ask a traveler about the Silence faction"),
            (13, "Investigate an abandoned structure"),
            (14, "Meet someone who claims to have seen the Blue Rose"),
            (15, "Learn about a mysterious prophecy"),
            
            # Turns 16-20: Lore and factions
            (16, "Ask about the Sovereign's Finest and their goals"),
            (17, "Inquire about the Shadow Barrens and dangers there"),
            (18, "Learn about the Blue Rose itself - what is it?"),
            (19, "Discuss the politics between Aldis and other regions"),
            (20, "Listen to a tale of a previous adventurer"),
            
            # Turns 21-26: Challenge and inventory
            (21, "Encounter a dangerous creature"),
            (22, "Prepare for combat and ready your weapon"),
            (23, "Attempt something reckless and probably foolish"),
            (24, "Ask about something that definitely isn't in the lore"),
            (25, "Make a complex moral choice"),
            (26, "Spend gold on something interesting"),
            
            # Turns 27-30+: Advanced gameplay
            (27, "Search for a hidden path or secret"),
            (28, "Negotiate with multiple NPCs about a tense situation"),
            (29, "Make a decision that could affect your reputation"),
            (30, "Reflect on what you've learned about the Blue Rose"),
            (31, "Attempt a daring escape or infiltration"),
            (32, "Ask for guidance from an oracle or wise NPC"),
            (33, "Pursue a rumor about treasure or artifacts"),
            (34, "Face off against an enemy in combat"),
            (35, "Use a special ability related to your Fighter class"),
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
        results_file = Path(__file__).parent / "playthrough_results_fast.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"\nDetailed results saved to: {results_file}")

        # Final statistics
        logger.info(f"\nGame State at End:")
        logger.info(f"Character: {character.name}")
        logger.info(f"Location: {character.location}")
        logger.info(f"HP: {character.current_hp}/{character.max_hp}")
        logger.info(f"Conversation turns: {len(narrator.conversation_history)}")

        # Cleanup
        logger.info("\nCleaning up resources...")
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
