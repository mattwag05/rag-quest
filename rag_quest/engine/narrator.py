"""AI narrator for the game."""

import re
import time
import random
from typing import Optional

from ..llm import BaseLLMProvider
from ..knowledge import WorldRAG
from ..prompts import ACTION_PARSER, NARRATOR_SYSTEM
from .character import Character
from .world import World
from .state_parser import StateParser
from .inventory import Inventory
from .quests import QuestLog


class Narrator:
    """Manages AI narration and response generation."""

    def __init__(
        self,
        llm: BaseLLMProvider,
        world_rag: WorldRAG,
        character: Character,
        world: World,
        inventory: Optional["Inventory"] = None,
        quest_log: Optional["QuestLog"] = None,
    ):
        self.llm = llm
        self.world_rag = world_rag
        self.character = character
        self.world = world
        self.inventory = inventory
        self.quest_log = quest_log
        self.conversation_history: list[dict] = []
        self.state_parser = StateParser()

    def process_action(self, player_input: str) -> str:
        """
        Process a player action and generate a narrative response with error recovery.
        """
        try:
            # Generate response
            response = self._generate_response(player_input)

            # Parse response for state changes
            self._parse_and_apply_changes(response, player_input)

            # Record the interaction
            self.conversation_history.append(
                {"role": "user", "content": player_input}
            )
            self.conversation_history.append({"role": "assistant", "content": response})

            return response

        except Exception as e:
            # Last resort: return a fallback response
            return self._get_fallback_response(str(e))

    def _generate_response(self, player_input: str) -> str:
        """Generate a narrative response to player action."""
        # For now, use pre-written responses to make the game playable
        # This avoids Ollama hanging issues
        
        action_lower = player_input.lower()
        
        # Combat-related actions
        if any(word in action_lower for word in ['attack', 'fight', 'strike', 'hit', 'slash', 'punch', 'shoot']):
            responses = [
                f"You prepare your stance and attack! Your blow connects, dealing 3 damage to your opponent.",
                f"You swing your weapon at the creature. It dodges! You take a step back, ready for the next strike.",
                f"With a fierce cry, you charge forward. Your attack finds its mark, and the enemy recoils!",
            ]
            return random.choice(responses)
        
        # Movement actions
        elif any(word in action_lower for word in ['go', 'move', 'walk', 'run', 'travel', 'enter', 'explore']):
            locations = ['the dark forest', 'a mysterious cave', 'an ancient ruin', 'a bustling marketplace', 'a quiet shrine']
            location = random.choice(locations)
            responses = [
                f"You venture forth into {location}. The air changes around you as you explore this new place.",
                f"After a journey, you arrive at {location}. It's more impressive than you imagined.",
                f"You find yourself in {location}. Strange energies seem to emanate from this place.",
            ]
            return random.choice(responses)
        
        # Dialogue actions
        elif any(word in action_lower for word in ['talk', 'speak', 'ask', 'greet', 'chat']):
            responses = [
                "A figure approaches you and speaks in a mysterious tone. 'I have a task that requires someone of your talents...'",
                "'Welcome, adventurer. I've been expecting someone like you. There's much to do in this realm.'",
                "The person eyes you carefully. 'You look capable. Perhaps you'd be interested in a lucrative opportunity?'",
            ]
            return random.choice(responses)
        
        # Item/examination actions
        elif any(word in action_lower for word in ['take', 'grab', 'pick', 'examine', 'look', 'inspect', 'search']):
            items = ['a curious amulet', 'an old scroll', 'some glowing gems', 'a mysterious key', 'a healing potion']
            item = random.choice(items)
            responses = [
                f"You search the area and find {item}. You add it to your inventory.",
                f"Something catches your eye - {item}! You carefully retrieve it.",
                f"Hidden among the shadows, you discover {item}. This could prove useful.",
            ]
            return random.choice(responses)
        
        # Rest/interact actions
        elif any(word in action_lower for word in ['rest', 'sleep', 'meditate', 'sit', 'wait']):
            responses = [
                f"You take a moment to rest. Your wounds feel better. You recover 5 HP!",
                f"You find a safe place to meditate. The world fades away as you center yourself. HP restored by 3.",
                f"You settle down and take a well-deserved break. Your body feels refreshed.",
            ]
            return random.choice(responses)
        
        # Default action
        else:
            responses = [
                "The world seems to respond to your action in mysterious ways.",
                "Your action ripples through the fabric of reality.",
                "Something shifts in the world around you.",
                "The dungeon master nods as your action unfolds.",
                "Your deed echoes through the halls.",
            ]
            return random.choice(responses)

    def _get_fallback_response(self, error_msg: str = "") -> str:
        """Return a fallback response when generation fails."""
        fallback_responses = [
            f"The dungeon master pauses for a moment, gathering their thoughts... Your action succeeds.",
            f"There's a moment of silence as reality seems to shimmer around you... and then it continues.",
            f"The world seems to fade for an instant, then refocuses... You continue on.",
            f"You feel a strange presence, as if the very fabric of reality is thinking... The moment passes.",
        ]
        
        base = random.choice(fallback_responses)
        
        # Try to construct something meaningful about current state
        if self.character.current_hp < self.character.max_hp // 2:
            return f"{base} You're battered and worn, but still standing."
        elif self.character.location:
            return f"{base} Around you is {self.character.location}."
        else:
            return base

    def _parse_and_apply_changes(self, response: str, player_input: str) -> None:
        """Parse response for state changes and apply them."""
        # Parse the narrator response for mechanical changes
        change = self.state_parser.parse_narrator_response(response, player_input)
        
        # 1. Apply location change (only if it looks like a real location, not an item)
        if change.location and not any(word in change.location.lower() for word in ['potion', 'scroll', 'amulet', 'key', 'gold', 'gem', 'sword', 'shield', 'armor', 'ring', 'wand', 'staff', 'book', 'map']):
            self.character.location = change.location
            self.world.add_visited_location(change.location)
            self.world.add_event(f"Moved to {change.location}")
        
        # 2. Apply combat damage
        if change.damage_taken > 0:
            self.character.take_damage(change.damage_taken)
            self.world.add_event(f"Took {change.damage_taken} damage")
        
        # 3. Apply healing
        if change.hp_healed > 0:
            self.character.heal(change.hp_healed)
            self.world.add_event(f"Healed {change.hp_healed} HP")
        
        # 4. Apply inventory changes (items gained)
        for item_name in change.items_gained:
            # Filter out non-item extractions (fragments, locations, etc.)
            if not self._is_valid_item(item_name):
                continue
            
            # Try to detect item properties from narrator response
            rarity = self._detect_item_rarity(response, item_name)
            description = self._extract_item_description(response, item_name)
            
            # Add to inventory
            if self.inventory:
                self.inventory.add_item(
                    name=item_name,
                    description=description,
                    quantity=1,
                    weight=1.0,
                    rarity=rarity
                )
            
            self.world.add_event(f"Obtained {item_name}")
            self.world.discovered_items.append(item_name)
        
        # 5. Apply inventory changes (items lost/used)
        for item_name in change.items_lost:
            if self.inventory:
                self.inventory.remove_item(item_name)
            self.world.add_event(f"Lost {item_name}")
        
        # 6. Apply quest offers
        if change.quest_offered:
            if self.quest_log:
                self.quest_log.add_quest(
                    title=change.quest_offered,
                    description=f"Quest started: {change.quest_offered}",
                    objectives=[change.quest_offered],
                    reward_xp=100,
                    reward_description="Experience and loot"
                )
            self.world.add_event(f"Quest offered: {change.quest_offered}")
        
        # 7. Apply quest completions
        if change.quest_completed:
            if self.quest_log:
                self.quest_log.complete_quest(change.quest_completed)
            self.world.add_event(f"Quest completed: {change.quest_completed}")
        
        # 8. Record NPC meeting
        if change.npc_met:
            self.world.add_met_npc(change.npc_met)
            self.world.add_event(f"Met {change.npc_met}")
        
        # Always add general event
        self.world.add_event(player_input[:50])

    def _detect_item_rarity(self, response: str, item_name: str) -> str:
        """Detect item rarity from narrator response."""
        response_lower = response.lower()
        
        if any(word in response_lower for word in ['legendary', 'mythical', 'ancient', 'divine']):
            return "legendary"
        elif any(word in response_lower for word in ['rare', 'precious', 'valuable', 'unique']):
            return "rare"
        elif any(word in response_lower for word in ['uncommon', 'special', 'remarkable', 'fine']):
            return "uncommon"
        
        return "common"

    def _extract_item_description(self, response: str, item_name: str) -> str:
        """Extract item description from narrator response."""
        # Simple approach: find the sentence containing the item
        sentences = response.split('.')
        for sentence in sentences:
            if item_name.lower() in sentence.lower():
                return sentence.strip()[:200]
        return f"A {item_name}."

    def _is_valid_item(self, item_name: str) -> bool:
        """Check if extracted text is actually a valid item."""
        # Filter out fragments, non-items, and location descriptors
        invalid_words = [
            'yourself', 'you', 'quiet shrine', 'bustling marketplace',
            'dark forest', 'step back', 'ready', 'the creature',
            'your', 'their', 'its', 'action', 'deed', 'world',
            'world around you', 'fabric of reality', 'the world',
            'something', 'everything', 'nothing'
        ]
        
        item_lower = item_name.lower().strip()
        
        # Check against invalid words
        for invalid in invalid_words:
            if invalid in item_lower:
                return False
        
        # Must contain at least one noun-like word
        if len(item_lower.split()) > 6:
            return False
        
        # Should not be too generic or too long
        if len(item_name) > 50:
            return False
        
        return True

    def get_conversation_history(self) -> list[dict]:
        """Get conversation history."""
        return self.conversation_history.copy()

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
