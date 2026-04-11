#!/usr/bin/env python3
"""
Simplified RAG-Quest test - tests basic game components
"""

import sys
import os
import json
import time
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("RAG-QUEST SIMPLIFIED TEST")
print("=" * 80)

# Test 1: Character system
print("\n[TEST 1] Character System")
try:
    from rag_quest.engine.character import Character, Race, CharacterClass
    
    char = Character(
        name="Test Hero",
        race=Race.HUMAN,
        character_class=CharacterClass.FIGHTER,
        level=1,
        max_hp=20,
        current_hp=20,
        location="Village Square"
    )
    print(f"✓ Character created: {char.name} (Level {char.level} {char.race.value} {char.character_class.value})")
except Exception as e:
    print(f"✗ Character test failed: {e}")
    traceback.print_exc()

# Test 2: World system
print("\n[TEST 2] World System")
try:
    from rag_quest.engine.world import World
    
    world = World(name="Test World", setting="Fantasy RPG", tone="Epic Adventure")
    print(f"✓ World created: {world.name}")
    print(f"  - Current time: {world.current_time}")
    print(f"  - Weather: {world.weather.value if hasattr(world.weather, 'value') else world.weather}")
    print(f"  - Description: {world.description[:100]}..." if len(world.description) > 100 else f"  - Description: {world.description}")
except Exception as e:
    print(f"✗ World test failed: {e}")
    traceback.print_exc()

# Test 3: RAG system (if available)
print("\n[TEST 3] RAG/Knowledge System")
try:
    from rag_quest.knowledge.world_rag import WorldRAG
    from rag_quest.llm.base import LLMConfig
    from rag_quest.llm.ollama_provider import OllamaProvider
    
    # Create LLM provider first
    llm_config = LLMConfig(provider="ollama", model="gemma4", temperature=0.7)
    provider = OllamaProvider(llm_config)
    print(f"✓ LLM provider created")
    
    # Create RAG
    rag = WorldRAG(world_name="Blue Rose World", llm_config=llm_config, llm_provider=provider)
    print(f"✓ RAG system initialized")
    
    # Try ingesting the PDF
    pdf_path = '/Users/matthewwagner/Desktop/The Blue Rose Adventurer\'s Guide 5E.pdf'
    if os.path.exists(pdf_path):
        from rag_quest.knowledge.ingest import ingest_file
        print(f"  Ingesting PDF (this may take a moment)...")
        start = time.time()
        try:
            ingest_file(rag, pdf_path)
            elapsed = time.time() - start
            print(f"✓ PDF ingested in {elapsed:.2f}s")
        except Exception as e:
            print(f"✗ PDF ingestion failed: {e}")
    else:
        print(f"⚠ PDF not found at {pdf_path}")
        
except Exception as e:
    print(f"✗ RAG test failed: {e}")
    traceback.print_exc()

# Test 4: LLM Provider
print("\n[TEST 4] LLM Provider (Ollama)")
try:
    from rag_quest.llm.ollama_provider import OllamaProvider
    from rag_quest.llm.base import LLMConfig
    
    llm_config = LLMConfig(provider="ollama", model="gemma4", temperature=0.7)
    provider = OllamaProvider(llm_config)
    print(f"✓ Ollama provider created")
    
    # Test a simple completion
    print("  Testing simple text generation...")
    start = time.time()
    response = provider.complete("What is the color of the sky?")
    elapsed = time.time() - start
    print(f"✓ Generated in {elapsed:.2f}s")
    print(f"  Response: {response[:100]}..." if len(str(response)) > 100 else f"  Response: {response}")
    
except Exception as e:
    print(f"✗ LLM provider test failed: {e}")
    traceback.print_exc()

# Test 5: Game loop / Narrator
print("\n[TEST 5] Narrator System")
try:
    from rag_quest.engine.narrator import Narrator
    from rag_quest.engine.game import GameState
    from rag_quest.engine.world import World
    from rag_quest.engine.character import Character, Race, CharacterClass
    from rag_quest.llm.ollama_provider import OllamaProvider
    from rag_quest.llm.base import LLMConfig
    
    # Set up components
    world = World(name="Test World", setting="Fantasy", tone="Adventure")
    char = Character(
        name="Test Hero",
        race=Race.HUMAN,
        character_class=CharacterClass.FIGHTER,
        level=1,
        max_hp=20,
        current_hp=20,
        location="Village Square"
    )
    llm_config = LLMConfig(provider="ollama", model="gemma4", temperature=0.7)
    provider = OllamaProvider(llm_config)
    
    # Create narrator
    narrator = Narrator(character=char, world=world, llm_provider=provider)
    print(f"✓ Narrator created")
    
    # Test narrator's get_world_state
    if hasattr(narrator, 'get_world_state'):
        state = narrator.get_world_state()
        print(f"✓ World state generated ({len(state)} chars)")
        print(f"  {state[:100]}...")
    
except Exception as e:
    print(f"✗ Narrator test failed: {e}")
    traceback.print_exc()

print("\n" + "=" * 80)
print("TEST SUITE COMPLETE")
print("=" * 80)
