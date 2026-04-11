"""AI narrator for the game."""

import re
from typing import Optional

from ..llm import BaseLLMProvider
from ..knowledge import WorldRAG
from ..prompts import ACTION_PARSER, NARRATOR_SYSTEM
from .character import Character
from .world import World


class Narrator:
    """Manages AI narration and response generation."""

    def __init__(
        self,
        llm: BaseLLMProvider,
        world_rag: WorldRAG,
        character: Character,
        world: World,
    ):
        self.llm = llm
        self.world_rag = world_rag
        self.character = character
        self.world = world
        self.conversation_history: list[dict] = []

    async def process_action(self, player_input: str) -> str:
        """
        Process a player action and generate a narrative response.
        """
        # Query RAG for relevant world context
        context_query = (
            f"Player: {self.character.name} ({self.character.race.value} "
            f"{character_class})\n"
            f"Location: {self.character.location}\n"
            f"Action: {player_input}\n"
            f"Recent context: {' | '.join(self.world.recent_events[-3:] if self.world.recent_events else ['None'])}"
        )

        world_context = await self.world_rag.query_world(
            context_query,
            param="hybrid",
        )

        # Build messages for LLM
        messages = self._build_messages(player_input, world_context)

        # Generate response
        response = await self.llm.complete(
            messages,
            temperature=0.85,
            max_tokens=1024,
        )

        # Parse response for state changes
        self._parse_and_apply_changes(response, player_input)

        # Record the interaction
        self.conversation_history.append(
            {"role": "user", "content": player_input}
        )
        self.conversation_history.append({"role": "assistant", "content": response})

        # Record new facts to RAG
        await self.world_rag.record_event(
            f"{self.character.name} {player_input}"
        )

        return response

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
        # Check for location changes
        location_match = re.search(
            r"you (?:arrive|enter|move|travel|walk|run|sail) (?:to|at|in|into) (.+?)(?:\.|,|\n)",
            response,
            re.IGNORECASE,
        )
        if location_match:
            new_location = location_match.group(1).strip()
            self.character.location = new_location
            self.world.add_visited_location(new_location)
            self.world.add_event(
                f"Moved to {new_location}"
            )

        # Check for NPC meetings
        npc_match = re.search(
            r"you (?:meet|encounter|see|find) (.+?)(?:,| the| a |\.|$)",
            response,
            re.IGNORECASE,
        )
        if npc_match:
            npc_name = npc_match.group(1).strip()
            # Filter out common words that aren't NPC names
            if len(npc_name.split()) <= 3 and not any(
                word in npc_name.lower()
                for word in ["your", "yourself", "own", "the"]
            ):
                self.world.add_met_npc(npc_name)
                self.world.add_event(f"Met {npc_name}")

        # Check for item discoveries
        item_match = re.search(
            r"you (?:find|obtain|receive|discover|gain|pick up) (.+?)(?:,| the| a|\.|$)",
            response,
            re.IGNORECASE,
        )
        if item_match:
            item_name = item_match.group(1).strip()
            if len(item_name.split()) <= 4:
                self.world.discovered_items.append(item_name)
                self.world.add_event(f"Discovered {item_name}")

        # Always add general event
        self.world.add_event(player_input[:50])

    def get_conversation_history(self) -> list[dict]:
        """Get conversation history."""
        return self.conversation_history.copy()

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
