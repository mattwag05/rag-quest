#!/usr/bin/env python3
"""
Comprehensive playtest script for RAG-Quest
Tests 30+ turns with various actions and logs all interactions
"""

import sys
import os
import json
import time
import traceback
from datetime import datetime
from pathlib import Path

# Add the project to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Load .env file before importing rag_quest
from dotenv import load_dotenv
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    load_dotenv(env_file)
    print(f"✓ Loaded .env from {env_file}")
else:
    print(f"✗ .env not found at {env_file}")

from rag_quest.config import get_config, load_llm_provider, create_world_from_config, create_character_from_config
from rag_quest.engine.game import GameState, run_game
from rag_quest.knowledge.ingest import ingest_file
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestReport:
    def __init__(self, output_file):
        self.output_file = output_file
        self.turns = []
        self.errors = []
        self.start_time = None
        self.end_time = None
        self.config = {}
        
    def add_turn(self, turn_num, action, response, error=None, response_time=0):
        """Record a turn"""
        self.turns.append({
            'turn': turn_num,
            'action': action,
            'response': response if response else str(error),
            'error': error is not None,
            'response_time_seconds': response_time,
            'timestamp': datetime.now().isoformat()
        })
        
    def add_error(self, error_text, traceback_text=None):
        """Record an error"""
        self.errors.append({
            'error': error_text,
            'traceback': traceback_text,
            'timestamp': datetime.now().isoformat()
        })
        
    def set_config(self, config_dict):
        """Set the configuration details"""
        self.config = config_dict
        
    def save(self):
        """Save the report to file"""
        report = {
            'test_metadata': {
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': self.end_time.isoformat() if self.end_time else None,
                'duration_seconds': (self.end_time - self.start_time).total_seconds() if (self.start_time and self.end_time) else None,
                'total_turns': len(self.turns),
                'errors_count': len(self.errors),
            },
            'config': self.config,
            'turns': self.turns,
            'errors': self.errors,
        }
        
        with open(self.output_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Test report saved to {self.output_file}")
        print(f"\n✓ Test report saved to {self.output_file}")


def run_playtest():
    """Run the comprehensive playtest"""
    
    # Initialize report
    report = TestReport("/tmp/rag_quest_test_report.json")
    report.start_time = datetime.now()
    
    logger.info("=" * 80)
    logger.info("RAG-QUEST PLAYTEST STARTING")
    logger.info("=" * 80)
    
    try:
        # Load config
        logger.info("Loading configuration...")
        cfg = get_config()
        
        report.set_config({
            'llm_provider': cfg.get('llm_provider', 'Unknown'),
            'ollama_model': cfg.get('ollama_model', 'Unknown'),
            'use_rag': True,
            'pdf_path': '/Users/matthewwagner/Desktop/The Blue Rose Adventurer\'s Guide 5E.pdf',
        })
        
        logger.info(f"Config: {cfg}")
        
        # Create world
        logger.info("Creating world...")
        world = create_world_from_config(cfg)
        
        # Ingest PDF
        pdf_path = '/Users/matthewwagner/Desktop/The Blue Rose Adventurer\'s Guide 5E.pdf'
        if os.path.exists(pdf_path):
            logger.info(f"Ingesting PDF lore from {pdf_path}...")
            try:
                start_ingest = time.time()
                # Check if the world has RAG capability
                if hasattr(world, 'rag'):
                    ingest_file(world.rag, pdf_path)
                    ingest_time = time.time() - start_ingest
                    logger.info(f"PDF ingested successfully in {ingest_time:.2f} seconds")
                    report.add_turn(0, "ingest_pdf", f"Successfully ingested Blue Rose PDF in {ingest_time:.2f}s", 
                                  error=False, response_time=ingest_time)
                else:
                    logger.warning("World does not have RAG capability")
                    report.add_error("World does not have RAG capability")
            except Exception as e:
                logger.error(f"Failed to ingest PDF: {e}")
                report.add_error(f"PDF ingestion failed: {e}", traceback.format_exc())
        else:
            logger.warning(f"PDF not found at {pdf_path}")
            report.add_error(f"PDF not found at {pdf_path}")
        
        # Create character
        logger.info("Creating character...")
        character = create_character_from_config(cfg)
        
        # Initialize game state
        logger.info("Initializing game state...")
        game_state = GameState(world=world, character=character)
        
        # Test actions - a diverse set of 30+ turns
        test_actions = [
            # 1. Basic exploration
            "look around",
            "examine surroundings",
            "where am I?",
            
            # 2. Inventory management
            "check inventory",
            "what do I have?",
            "show items",
            
            # 3. Movement
            "go north",
            "explore",
            "move forward",
            
            # 4. Lore/knowledge questions (testing RAG retrieval)
            "tell me about the Blue Rose",
            "what factions are in this world?",
            "who are the major powers around here?",
            "what's the history of this realm?",
            "are there any legends about this place?",
            
            # 5. Interaction with world
            "look for clues",
            "listen carefully",
            "touch nearby objects",
            
            # 6. NPC interaction
            "talk to the nearest person",
            "ask about adventures",
            "request a quest",
            
            # 7. Character actions
            "cast a spell",
            "draw my weapon",
            "hide in shadows",
            
            # 8. Edge cases and special queries
            "what can I do here?",
            "help",
            "status",
            
            # 9. Longer/complex inputs
            "I want to go to the nearest town and ask the tavern keeper about rumors of treasure",
            "Tell me everything you know about the major cities mentioned in the lore",
            
            # 10. Empty/minimal input
            "",
            "um",
            
            # 11. Very long input
            "a" * 500,
            
            # 12. Special characters
            "What's < happening > here & now?",
            
            # 13. Contradictory/complex requests
            "I'm simultaneously in two places at once and want to do two conflicting things",
            
            # 14. Meta questions
            "Are you using RAG to answer questions?",
            "How does this game work?",
            
            # 15. More lore queries
            "What religions are practiced here?",
            "What kind of magic exists?",
            "Are there any powerful artifacts?",
        ]
        
        logger.info(f"Running {len(test_actions)} test turns...")
        print(f"\n{'='*80}")
        print(f"STARTING PLAYTEST: {len(test_actions)} ACTIONS")
        print(f"{'='*80}\n")
        
        # Try to get narrator
        narrator = None
        if hasattr(world, 'narrator'):
            narrator = world.narrator
            logger.info("Using world narrator")
        
        for turn_num, action in enumerate(test_actions, 1):
            try:
                logger.info(f"Turn {turn_num}: {repr(action[:100])}")
                
                start_turn = time.time()
                response = None
                error_occurred = False
                
                try:
                    # Try using narrator if available
                    if narrator and hasattr(narrator, 'process_action'):
                        response = narrator.process_action(action, game_state)
                    elif hasattr(game_state, 'process_action'):
                        response = game_state.process_action(action)
                    else:
                        response = f"[Game interface note] No process_action method available"
                        
                except TypeError as e:
                    logger.warning(f"Method call error on turn {turn_num}: {e}")
                    response = f"[Method error] {str(e)}"
                    
                response_time = time.time() - start_turn
                
                # Log the turn
                report.add_turn(turn_num, action, response, error=error_occurred, 
                               response_time=response_time)
                
                print(f"[Turn {turn_num}] Action: {action[:60]}{'...' if len(action) > 60 else ''}")
                print(f"  Response time: {response_time:.2f}s")
                if response:
                    print(f"  Response: {response[:200]}..." if len(str(response)) > 200 else f"  Response: {response}")
                print()
                    
            except Exception as e:
                response_time = time.time() - start_turn
                logger.error(f"Turn {turn_num} failed: {e}")
                logger.error(traceback.format_exc())
                
                report.add_turn(turn_num, action, None, error=True, 
                               response_time=response_time)
                report.add_error(f"Turn {turn_num} error: {e}", traceback.format_exc())
                
                print(f"[Turn {turn_num}] ✗ ERROR: {e}\n")
        
        logger.info(f"Completed {len(test_actions)} turns")
        
    except Exception as e:
        logger.error(f"Fatal error during playtest: {e}")
        logger.error(traceback.format_exc())
        report.add_error(f"Fatal playtest error: {e}", traceback.format_exc())
        print(f"\n✗ FATAL ERROR: {e}")
        print(traceback.format_exc())
        
    finally:
        report.end_time = datetime.now()
        report.save()
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"PLAYTEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total turns: {len(report.turns)}")
        print(f"Successful turns: {sum(1 for t in report.turns if not t['error'])}")
        print(f"Failed turns: {sum(1 for t in report.turns if t['error'])}")
        print(f"Total errors: {len(report.errors)}")
        if report.end_time and report.start_time:
            print(f"Duration: {(report.end_time - report.start_time).total_seconds():.2f} seconds")
        print(f"Report saved to: /tmp/rag_quest_test_report.json")
        print(f"{'='*80}\n")


if __name__ == '__main__':
    run_playtest()
