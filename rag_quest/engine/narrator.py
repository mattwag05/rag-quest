"""AI narrator for the game."""

import re
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
            # Query RAG for relevant world context
            location_context = self._query_location_context()
            character_context = self._query_character_context()
            action_context = self._query_action_context(player_input)
            recent_events_context = self._get_recent_events_context()

            # Combine multiple context sources for richer narrative
            world_context = self._combine_contexts(
                location_context,
                character_context,
                action_context,
                recent_events_context
            )

            # Build messages for LLM
            messages = self._build_messages(player_input, world_context)

            # Generate response with retry logic
            response = self._generate_response_with_retry(messages)

            # Parse response for state changes
            self._parse_and_apply_changes(response, player_input)

            # Record the interaction
            self.conversation_history.append(
                {"role": "user", "content": player_input}
            )
            self.conversation_history.append({"role": "assistant", "content": response})

            # Record new facts to RAG asynchronously (don't fail on this)
            try:
                self.world_rag.record_event(
                    f"{self.character.name} {player_input}"
                )
            except Exception as e:
                # Log but don't crash if RAG recording fails
                pass

            return response

        except Exception as e:
            # Last resort: return a fallback response
            return self._get_fallback_response(str(e))

    def _query_location_context(self) -> str:
        """Query detailed context about current location."""
        try:
            query = f"What is {self.character.location}? What do you see, smell, hear?"
            return self.world_rag.query_world(query) or ""
        except Exception as e:
            return ""

    def _query_character_context(self) -> str:
        """Query context about character, class, and recent interactions."""
        try:
            query = (
                f"Character {self.character.name} is a {self.character.race.value} "
                f"{self.character.character_class.value}. "
                f"What do we know about this character type?"
            )
            return self.world_rag.query_world(query) or ""
        except Exception as e:
            return ""

    def _query_action_context(self, action: str) -> str:
        """Query context relevant to the player's action."""
        try:
            # Extract key nouns/verbs from action
            query = f"In this world, how would someone {action}?"
            return self.world_rag.query_world(query) or ""
        except Exception as e:
            return ""

    def _get_recent_events_context(self) -> str:
        """Get formatted context of recent events."""
        if not self.world.recent_events:
            return ""
        return "Recent events: " + " > ".join(self.world.recent_events[-5:])

    def _combine_contexts(
        self,
        location: str,
        character: str,
        action: str,
        recent: str
    ) -> str:
        """Combine multiple context sources into a coherent narrative context."""
        parts = []
        
        if location:
            parts.append(f"Location Context:\n{location}")
        
        if character:
            parts.append(f"Character Knowledge:\n{character}")
        
        if action:
            parts.append(f"Action Context:\n{action}")
        
        if recent:
            parts.append(recent)
        
        return "\n\n".join(parts) if parts else ""

    def _generate_response_with_retry(
        self, messages: list[dict], max_retries: int = 3
    ) -> str:
        """Generate response with retry logic and exponential backoff."""
        import time
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = self.llm.complete(
                    messages,
                    temperature=0.85,
                    max_tokens=1024,
                )
                
                # Validate response is not empty
                if response and response.strip():
                    return response
                
                raise ValueError("Empty response from LLM")
                
            except Exception as e:
                last_error = e
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = (2 ** attempt) * 0.5
                    time.sleep(wait_time)
                    continue
        
        # All retries failed
        raise last_error or Exception("Failed to generate response after retries")

    def _get_fallback_response(self, error_msg: str = "") -> str:
        """Return a fallback response when LLM fails."""
        fallback_responses = [
            f"The dungeon master pauses for a moment, gathering their thoughts...",
            f"There's a moment of silence as reality seems to shimmer around you...",
            f"The world seems to fade for an instant, then refocuses...",
            f"You feel a strange presence, as if the very fabric of reality is thinking...",
        ]
        
        import random
        base = random.choice(fallback_responses)
        
        # Try to construct something meaningful about current state
        if self.character.current_hp < self.character.max_hp // 2:
            return f"{base} You're battered and worn, but still standing."
        elif self.character.location:
            return f"{base} Around you is {self.character.location}."
        else:
            return base

    def _build_messages(self, player_input: str, world_context: str) -> list[dict]:
        """Build message list for the LLM."""
        messages = [
            {
                "role": "system",
                "content": NARRATOR_SYSTEM,
            }
        ]

        # Add context from RAG
        if world_context:
            messages.append(
                {
                    "role": "system",
                    "content": f"World Knowledge:\n{world_context}",
                }
            )

        # Add world state
        world_state = (
            f"Current World State:\n"
            f"- Setting: {self.world.setting}\n"
            f"- Tone: {self.world.tone}\n"
            f"- {self.world.get_context()}\n"
            f"- Character: {self.character.name} ({self.character.race.value} "
            f"{self.character.character_class.value})\n"
            f"- Location: {self.character.location}\n"
            f"- HP: {self.character.current_hp}/{self.character.max_hp}"
        )
        messages.append(
            {
                "role": "system",
                "content": world_state,
            }
        )

        # Add recent conversation history
        messages.extend(self.conversation_history[-6:])  # Last 3 exchanges

        # Add current input
        messages.append(
            {
                "role": "user",
                "content": f"Player action: {player_input}",
            }
        )

        return messages

    def _parse_and_apply_changes(self, response: str, player_input: str) -> None:
        """Parse response for state changes and apply them."""
        # Parse the narrator response for mechanical changes
        change = self.state_parser.parse_narrator_response(response, player_input)
        
        # 1. Apply location change
        if change.location:
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

    def get_conversation_history(self) -> list[dict]:
        """Get conversation history."""
        return self.conversation_history.copy()

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
