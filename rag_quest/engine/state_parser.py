"""State parser - extracts mechanical changes from narrator responses and player actions."""

import re
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class StateChange:
    """Represents a game state change."""
    
    location: Optional[str] = None
    damage_taken: int = 0
    hp_healed: int = 0
    items_gained: List[str] = None
    items_lost: List[str] = None
    quest_offered: Optional[str] = None
    quest_completed: Optional[str] = None
    npc_met: Optional[str] = None
    npc_recruited: Optional[str] = None
    npc_relationship_change: Dict[str, int] = None
    world_event_triggered: Optional[str] = None
    
    def __post_init__(self):
        if self.items_gained is None:
            self.items_gained = []
        if self.items_lost is None:
            self.items_lost = []
        if self.npc_relationship_change is None:
            self.npc_relationship_change = {}


class StateParser:
    """Parses player actions and narrator responses to extract state changes."""

    def __init__(self):
        # Common location keywords
        self.location_patterns = [
            r"(?:arrive|enter|move|travel|walk|run|sail|journey|trek|head)\s+(?:to|at|in|into)\s+(.+?)(?:\.|,|!|\?|\n|$)",
            r"(?:find|discover|stumble upon)\s+(?:a|the)?\s*(.+?)(?:\s+(?:location|place|area))?(?:\.|,|!|\?|\n|$)",
            r"you\s+(?:are\s+)?(?:in|at|inside)\s+(?:a|the)?\s*(.+?)(?:\.|,|!|\?|\n|$)",
            r"stride\s+into\s+(.+?)(?:,|\.|\n|$)",
            r"step(?:s)?\s+into\s+(.+?)(?:,|\.|\n|$)",
        ]
        
        # Combat-related keywords
        self.combat_keywords = {
            'attack', 'fight', 'strike', 'hit', 'punch', 'slash', 'stab', 'shoot',
            'cast', 'spell', 'magic', 'battle', 'combat', 'duel', 'clash',
            'swing', 'thrust', 'smite', 'charge', 'assault', 'skirmish'
        }
        
        # Damage keywords and patterns
        self.damage_patterns = [
            r"(\d+)\s*(?:damage|hp|health|hit points)",
            r"take[s]?\s+(\d+)\s*(?:damage|hp|health|hit points)",
            r"(?:deal|inflict)[s]?\s+(\d+)\s*(?:damage|hp|health|hit points)",
            r"(?:lose|lost)\s+(\d+)\s"
        ]
        
        # Relationship and social keywords
        self.relationship_keywords = {
            'trust': 15, 'grateful': 20, 'ally': 25, 'friend': 20, 'help': 10,
            'betray': -30, 'angry': -25, 'hostile': -20, 'insult': -15, 'refuse': -10,
            'gift': 20, 'favor': 15, 'quest_complete': 15, 'recruit': 30,
        }
        
        # Party recruitment patterns
        self.recruitment_patterns = [
            r"(\w+\s+\w+)?\s*joins?\s+(?:your\s+)?party",
            r"(\w+\s+\w+)?\s*(?:agrees?|volunteers?)\s+to\s+join",
            r"you\s+recruit\s+(\w+\s+\w+)?",
        ]
        
        # Healing patterns
        self.healing_patterns = [
            r"(?:heal|restore)[s]?\s+(\d+)\s*(?:hp|health|hit points)",
            r"(?:recover|regain)\s+(\d+)\s*(?:health|hp|hit points)",
            r"potion\s+(?:heal[s]?|restore[s]?)\s+(\d+)",
        ]
        
        # Inventory patterns
        self.pickup_patterns = [
            r"(?:pick\s+up|grab|take|obtain|find|receive|gain|discover)\s+(?:a\s+)?(.+?)(?:\.|,|!|\?|\n|$)",
            r"(?:you\s+)?(?:acquire|gain)\s+(?:a\s+)?(.+?)(?:\.|,|!|\?|\n|$)",
            r"you\s+(?:also\s+)?(?:notice|see)\s+(?:a\s+)?(.+?)(?:\s+(?:on|in|at)|\sand\s|,|\.)",
        ]
        
        self.drop_patterns = [
            r"(?:drop|discard|leave|abandon)\s+(?:the\s+)?(.+?)(?:\.|,|!|\?|\n)",
        ]
        
        self.use_patterns = [
            r"(?:use|consume|drink|eat|activate|wield|equip)\s+(?:the\s+)?(.+?)(?:\.|,|!|\?|\n)",
        ]
        
        # Quest patterns
        self.quest_offer_patterns = [
            r"(?:quest|mission|task|request)\s+(?:offered|given|started|begun):\s*(.+?)(?:\.|,|!|\?|\n|$)",
            r"(?:a\s+)?(?:quest|mission|task)\s+for\s+you:\s*(.+?)(?:\"|\.|\?|,|\n|$)",
            r"(.+?)\s+(?:ask|asks|request[s]?|offer[s]?)\s+(?:you|your\s+help|a\s+quest)(?:\.|\?|,|!|$)",
            r"new\s+(?:quest|mission|objective):\s*(.+?)(?:\.|,|!|\?|\n|$)",
            r"i\s+have\s+a\s+(?:quest|mission|task)\s+for\s+you:\s*(.+?)(?:\"|\.|\?|,|\n|$)",
        ]
        
        self.quest_complete_patterns = [
            r"(?:quest|mission|task)\s+(?:complete|finished|accomplished|succeeded):\s*(.+?)(?:\.|,|!|\?|\n)",
            r"(?:you\s+)?(?:complete|finish|accomplish)\s+(?:the\s+)?(.+?)(?:\s+quest)?(?:\.|,|!|\?|\n)",
        ]
        
        # NPC meeting patterns
        self.npc_patterns = [
            r"(?:you\s+)?(?:meet|encounter|find|see)\s+(.+?)(?:,|\s+the|!|\?|\.|\n)",
            r"(?:a|the)\s+(.+?)\s+(?:approach|greet)[s]?\s+you",
        ]

    def parse_action_intent(self, player_input: str) -> Dict[str, bool]:
        """Detect what the player is trying to do based on their input."""
        input_lower = player_input.lower()
        
        return {
            'is_movement': any(word in input_lower for word in 
                ['go', 'move', 'travel', 'walk', 'run', 'explore', 'enter', 'exit', 'head', 'journey']),
            'is_combat': any(word in input_lower for word in self.combat_keywords),
            'is_pickup': any(word in input_lower for word in ['pick', 'take', 'grab', 'obtain', 'find']),
            'is_drop': any(word in input_lower for word in ['drop', 'leave', 'discard', 'abandon']),
            'is_use': any(word in input_lower for word in ['use', 'consume', 'drink', 'eat', 'activate', 'wield', 'equip']),
            'is_quest': any(word in input_lower for word in ['quest', 'mission', 'task', 'accept', 'complete']),
        }

    def parse_narrator_response(self, response: str, player_input: str) -> StateChange:
        """Parse narrator response and extract state changes."""
        change = StateChange()
        response_lower = response.lower()
        
        # 1. Parse location changes
        location = self._extract_location(response)
        if location:
            change.location = location
        
        # 2. Parse combat and damage
        if any(word in response_lower for word in self.combat_keywords):
            damage = self._extract_damage(response)
            if damage > 0:
                change.damage_taken = damage
            else:
                # If combat but no explicit damage, roll dice based on difficulty
                change.damage_taken = self._calculate_combat_damage(player_input, response)
        
        # 3. Parse healing
        healing = self._extract_healing(response)
        if healing > 0:
            change.hp_healed = healing
        
        # 4. Parse inventory changes
        change.items_gained = self._extract_items_gained(response)
        change.items_lost = self._extract_items_lost(response)
        
        # 5. Parse quest offers and completions
        change.quest_offered = self._extract_quest_offered(response)
        change.quest_completed = self._extract_quest_completed(response)
        
        # 6. Parse NPC meetings
        change.npc_met = self._extract_npc(response)
        
        return change

    def _extract_location(self, response: str) -> Optional[str]:
        """Extract location from response."""
        for pattern in self.location_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                # Clean up the location name
                location = re.sub(r'[.,!?;]*$', '', location)
                # Filter out overly long extractions
                if len(location) < 50 and len(location.split()) <= 5:
                    return location
        return None

    def _extract_damage(self, response: str) -> int:
        """Extract explicit damage values from response."""
        for pattern in self.damage_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        return 0

    def _calculate_combat_damage(self, player_input: str, response: str) -> int:
        """Calculate combat damage when none is explicitly mentioned."""
        # Base damage: 1d6 (1-6)
        base_damage = random.randint(1, 6)
        
        # Modifiers based on keywords
        aggressive_words = ['attack', 'strike', 'smash', 'destroy', 'annihilate', 'brutal']
        defensive_words = ['defend', 'protect', 'shield', 'dodge', 'evade']
        
        input_lower = player_input.lower()
        response_lower = response.lower()
        
        # If player is aggressive and narrator confirms damage
        if any(word in input_lower for word in aggressive_words):
            if any(word in response_lower for word in ['hit', 'struck', 'damage', 'wound', 'fall', 'defeated']):
                base_damage = random.randint(3, 8)
        
        # If narrator mentions critical hit or massive damage
        if any(word in response_lower for word in ['critical', 'crushing', 'devastating', 'massive']):
            base_damage = random.randint(5, 10)
        
        # If narrator mentions enemy counterattack
        if any(word in response_lower for word in ['counterattack', 'counter', 'retaliation', 'strike back']):
            base_damage = random.randint(1, 5)
        
        return base_damage

    def _extract_healing(self, response: str) -> int:
        """Extract healing values from response."""
        for pattern in self.healing_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        return 0

    def _extract_items_gained(self, response: str) -> List[str]:
        """Extract items the player gained."""
        items = []
        
        # Use the pickup patterns
        for pattern in self.pickup_patterns:
            for match in re.finditer(pattern, response, re.IGNORECASE):
                try:
                    item = match.group(1).strip()
                    # Clean up
                    item = re.sub(r'^(?:a|an|the)\s+', '', item, flags=re.IGNORECASE)
                    item = re.sub(r'[.,!?;]*$', '', item)
                    
                    # Avoid junk matches (too long or too vague)
                    if len(item) < 60 and len(item.split()) <= 6 and item not in ['yourself', 'your', 'nothing']:
                        items.append(item)
                except IndexError:
                    continue
        
        return items

    def _extract_items_lost(self, response: str) -> List[str]:
        """Extract items the player lost or dropped."""
        items = []
        
        for pattern in self.drop_patterns:
            for match in re.finditer(pattern, response, re.IGNORECASE):
                try:
                    item = match.group(1).strip()
                    # Clean up
                    item = re.sub(r'^(?:a|an|the)\s+', '', item, flags=re.IGNORECASE)
                    item = re.sub(r'[.,!?;]*$', '', item)
                    
                    if len(item) < 60 and len(item.split()) <= 6:
                        items.append(item)
                except IndexError:
                    continue
        
        return items

    def _extract_quest_offered(self, response: str) -> Optional[str]:
        """Extract quest title from response."""
        for pattern in self.quest_offer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                quest_title = match.group(1).strip()
                # Clean up
                quest_title = re.sub(r'[.,!?;]*$', '', quest_title)
                if len(quest_title) < 100 and len(quest_title.split()) <= 8:
                    return quest_title
        return None

    def _extract_quest_completed(self, response: str) -> Optional[str]:
        """Extract completed quest title from response."""
        for pattern in self.quest_complete_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                quest_title = match.group(1).strip()
                # Clean up
                quest_title = re.sub(r'[.,!?;]*$', '', quest_title)
                if len(quest_title) < 100 and len(quest_title.split()) <= 8:
                    return quest_title
        return None

    def _extract_npc(self, response: str) -> Optional[str]:
        """Extract NPC name from response."""
        for pattern in self.npc_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                npc_name = match.group(1).strip()
                # Clean up
                npc_name = re.sub(r'[.,!?;]*$', '', npc_name)
                npc_name = re.sub(r'^(?:a|an|the)\s+', '', npc_name, flags=re.IGNORECASE)
                
                # Filter out common non-NPC words
                if len(npc_name) < 50 and len(npc_name.split()) <= 4:
                    if not any(word in npc_name.lower() for word in ['your', 'yourself', 'the ground', 'the air']):
                        return npc_name
        return None
