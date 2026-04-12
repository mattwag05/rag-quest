"""State parser - extracts mechanical changes from narrator responses and player actions."""

import random
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

# Markdown emphasis strippers used by `_strip_markdown`. Compiled once so the
# per-turn hot path (every extracted location/item/quest/NPC passes through
# `_strip_markdown`) doesn't re-enter the `re` compile cache on every call.
_MD_BOLD_STAR = re.compile(r"\*\*(.+?)\*\*")
_MD_BOLD_UNDER = re.compile(r"__(.+?)__")
_MD_ITALIC_STAR = re.compile(r"(?<!\w)\*(.+?)\*(?!\w)")
_MD_ITALIC_UNDER = re.compile(r"(?<!\w)_(.+?)_(?!\w)")

# Shared cleanup regexes used by every extractor method to strip trailing
# punctuation and a leading article from a captured match.
_TRAILING_PUNCT = re.compile(r"[.,!?;]*$")
_LEADING_ARTICLE = re.compile(r"^(?:a|an|the)\s+", re.IGNORECASE)


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
    claim_base: bool = False  # narrator confirmed a base claim at current location

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
            re.compile(p, re.IGNORECASE)
            for p in (
                r"(?:arrive|enter|move|travel|walk|run|sail|journey|trek|head)\s+(?:to|at|in|into)\s+(.+?)(?:\.|,|!|\?|\n|$)",
                r"(?:find|discover|stumble upon)\s+(?:a|the)?\s*(.+?)(?:\s+(?:location|place|area))?(?:\.|,|!|\?|\n|$)",
                r"you\s+(?:are\s+)?(?:in|at|inside)\s+(?:a|the)?\s*(.+?)(?:\.|,|!|\?|\n|$)",
                r"stride\s+into\s+(.+?)(?:,|\.|\n|$)",
                r"step(?:s)?\s+into\s+(.+?)(?:,|\.|\n|$)",
            )
        ]

        # Combat-related keywords
        self.combat_keywords = {
            "attack",
            "fight",
            "strike",
            "hit",
            "punch",
            "slash",
            "stab",
            "shoot",
            "cast",
            "spell",
            "magic",
            "battle",
            "combat",
            "duel",
            "clash",
            "swing",
            "thrust",
            "smite",
            "charge",
            "assault",
            "skirmish",
        }

        # Damage patterns: must be explicit *player-directed* damage events.
        # The former catch-all r"(\d+)\s*(?:damage|hp|...)" false-positived on
        # the narrator's own HP readouts ("**22/22 HP**") and killed new
        # characters on turn 1 — see rag-quest-0gp. The `lose/lost` form
        # requires an HP qualifier so "lost 5 coins" stops counting as damage.
        self.damage_patterns = [
            re.compile(
                r"(?:take|takes|taking|suffer|suffers|suffering|receive|receives|receiving)"
                r"\s+(\d+)\s*(?:damage|hp|health|hit\s+points)",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?:lose|lost|losing)\s+(\d+)\s+(?:hp|health|hit\s+points)",
                re.IGNORECASE,
            ),
        ]

        # Word-boundary combat-keyword regex. Substring matching caused
        # "stable" → "stab" false positives that triggered dice-roll damage
        # on benign status text.
        self._combat_regex = re.compile(
            r"\b(?:"
            + "|".join(re.escape(w) for w in self.combat_keywords)
            + r")(?:s|es|ed|ing)?\b",
            re.IGNORECASE,
        )

        # Healing patterns
        self.healing_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (
                r"(?:heal|restore)[s]?\s+(\d+)\s*(?:hp|health|hit points)",
                r"(?:recover|regain)\s+(\d+)\s*(?:health|hp|hit points)",
                r"potion\s+(?:heal[s]?|restore[s]?)\s+(\d+)",
            )
        ]

        # Inventory patterns
        self.pickup_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (
                r"(?:pick\s+up|grab|take|obtain|find|receive|gain|discover)\s+(?:a\s+)?(.+?)(?:\.|,|!|\?|\n|$)",
                r"(?:you\s+)?(?:acquire|gain)\s+(?:a\s+)?(.+?)(?:\.|,|!|\?|\n|$)",
                r"you\s+(?:also\s+)?(?:notice|see)\s+(?:a\s+)?(.+?)(?:\s+(?:on|in|at)|\sand\s|,|\.)",
            )
        ]

        self.drop_patterns = [
            re.compile(
                r"(?:drop|discard|leave|abandon)\s+(?:the\s+)?(.+?)(?:\.|,|!|\?|\n)",
                re.IGNORECASE,
            ),
        ]

        self.use_patterns = [
            re.compile(
                r"(?:use|consume|drink|eat|activate|wield|equip)\s+(?:the\s+)?(.+?)(?:\.|,|!|\?|\n)",
                re.IGNORECASE,
            ),
        ]

        # Quest patterns
        self.quest_offer_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (
                r"(?:quest|mission|task|request)\s+(?:offered|given|started|begun):\s*(.+?)(?:\.|,|!|\?|\n|$)",
                r"(?:a\s+)?(?:quest|mission|task)\s+for\s+you:\s*(.+?)(?:\"|\.|\?|,|\n|$)",
                r"(.+?)\s+(?:ask|asks|request[s]?|offer[s]?)\s+(?:you|your\s+help|a\s+quest)(?:\.|\?|,|!|$)",
                r"new\s+(?:quest|mission|objective):\s*(.+?)(?:\.|,|!|\?|\n|$)",
                r"i\s+have\s+a\s+(?:quest|mission|task)\s+for\s+you:\s*(.+?)(?:\"|\.|\?|,|\n|$)",
            )
        ]

        self.quest_complete_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (
                r"(?:quest|mission|task)\s+(?:complete|finished|accomplished|succeeded):\s*(.+?)(?:\.|,|!|\?|\n)",
                r"(?:you\s+)?(?:complete|finish|accomplish)\s+(?:the\s+)?(.+?)(?:\s+quest)?(?:\.|,|!|\?|\n)",
            )
        ]

        # NPC meeting patterns
        self.npc_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (
                r"(?:you\s+)?(?:meet|encounter|find|see)\s+(.+?)(?:,|\s+the|!|\?|\.|\n)",
                r"(?:a|the)\s+(.+?)\s+(?:approach|greet)[s]?\s+you",
            )
        ]

        # Idioms that match pickup_patterns but are NOT inventory gains.
        # Narrators use these constantly; leaving them unfiltered pollutes Inventory.
        self.pickup_stopwords = {
            "deep breath",
            "breath",
            "break",
            "moment",
            "seat",
            "cover",
            "aim",
            "refuge",
            "shelter",
            "shape",
            "note",
            "care",
            "charge",
            "flight",
            "heed",
            "hold",
            "stock",
            "rest",
            "watch",
            "chance",
            "interest",
            "pride",
            "offense",
            "pity",
            "time",
            "stance",
            "comfort",
            "courage",
            "place",
            "position",
        }

        # Scenery / abstractions that match npc_patterns but aren't NPCs.
        self.npc_stopwords = {
            "sun",
            "moon",
            "sky",
            "stars",
            "star",
            "wind",
            "air",
            "ground",
            "floor",
            "ceiling",
            "light",
            "shadow",
            "shadows",
            "darkness",
            "path",
            "road",
            "door",
            "doorway",
            "room",
            "hall",
            "yourself",
            "nothing",
            "something",
            "someone",
            "anything",
            "everything",
            "wall",
            "walls",
            "window",
            "sign",
            "table",
            "chair",
        }

        # Base-claim phrasings. Narrator must explicitly tie the location to a
        # dwelling-word (base/stronghold/headquarters/hideout/etc). Player
        # saying "claim it" alone doesn't fire — the pattern looks at narrator
        # prose, not player input.
        #
        # Dwelling words trigger a claim ONLY when preceded by a possessive
        # ("your"/"thy") — "claim the treasure chest" never matches, "buy a
        # base for the statue" never matches. Leading verbs are restrictive
        # (claim / make / establish / found / become / be your).
        _dwell = r"(?:base|stronghold|headquarters|hideout|refuge|keep|encampment)"
        _poss = r"(?:your|thy)"
        self.claim_base_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (
                rf"claim(?:s|ed|ing)?\s+.{{1,60}}?\s+as\s+{_poss}\s+(?:new\s+|own\s+)?{_dwell}\b",
                rf"(?:make[s]?|made|makes)\s+.{{1,60}}?\s+{_poss}\s+(?:new\s+|own\s+)?{_dwell}\b",
                rf"\b(?:this|it|here)\s+(?:is\s+now|becomes|shall\s+be|will\s+be)\s+{_poss}\s+(?:new\s+|own\s+)?{_dwell}\b",
                rf"\bshall\s+be\s+{_poss}\s+(?:new\s+|own\s+)?(?:{_dwell}|hideaway|sanctuary)\b",
                rf"(?:establish(?:es|ed)?|found(?:s|ed)?)\s+(?:a|{_poss}|the)\s+(?:new\s+)?(?:{_dwell}|camp|outpost)\s+here",
            )
        ]

        # Trailing preposition clauses (or dangling prepositions) that leak
        # into greedy extractions. Matches "...at dawn" AND "...in" at EOL.
        self._trailing_prep_pattern = re.compile(
            r"\s+(?:at|in|on|with|by|from|of|under|over|near|beside|behind|before|after|into|onto)(?:\s+.+)?$",
            re.IGNORECASE,
        )

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Strip Markdown emphasis markers (**, __, *, _) and surrounding whitespace.

        Narrators frequently emit bold/italic formatting around proper nouns
        (e.g. '**Captain Mira**'). Left in place, these markers leak into
        World.npcs_met, Inventory items, and Timeline events.
        """
        if not text:
            return text
        # Remove paired emphasis markers first (greedy, inside-out).
        text = _MD_BOLD_STAR.sub(r"\1", text)
        text = _MD_BOLD_UNDER.sub(r"\1", text)
        text = _MD_ITALIC_STAR.sub(r"\1", text)
        text = _MD_ITALIC_UNDER.sub(r"\1", text)
        # Strip any dangling markers left by mismatched formatting.
        text = text.replace("**", "").replace("__", "")
        text = text.strip(" *_\t")
        return text

    def parse_narrator_response(self, response: str, player_input: str) -> StateChange:
        """Parse narrator response and extract state changes."""
        change = StateChange()
        response_lower = response.lower()

        # 1. Parse location changes
        location = self._extract_location(response)
        if location:
            change.location = location

        # 2. Parse damage. Explicit damage phrases extract directly; the
        # dice-roll fallback only runs when a real combat keyword is
        # present (word-boundary match, with "hit points/dice" excluded).
        damage = self._extract_damage(response)
        if damage > 0:
            change.damage_taken = damage
        elif self._has_combat_keyword(response):
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

        # 7. Parse base claim (v0.7)
        change.claim_base = self._detect_claim_base(response)

        return change

    def _detect_claim_base(self, response: str) -> bool:
        """True iff the narrator confirmed a base claim at the current location."""
        return any(p.search(response) for p in self.claim_base_patterns)

    def _extract_location(self, response: str) -> Optional[str]:
        """Extract location from response."""
        for pattern in self.location_patterns:
            match = pattern.search(response)
            if match:
                location = match.group(1).strip()
                # Clean up the location name
                location = _TRAILING_PUNCT.sub("", location)
                location = self._strip_markdown(location)
                # Strip trailing prepositional phrases ("Woods at dawn" → "Woods")
                location = self._trailing_prep_pattern.sub("", location).strip()
                # Filter out overly long extractions
                if location and len(location) < 50 and len(location.split()) <= 5:
                    return location
        return None

    def _extract_damage(self, response: str) -> int:
        """Extract explicit damage values from response."""
        for pattern in self.damage_patterns:
            match = pattern.search(response)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        return 0

    def _has_combat_keyword(self, response: str) -> bool:
        """True iff the response contains a real combat keyword.

        Uses word-boundary matching (so "stable" no longer matches "stab")
        and filters out "hit points" / "hit dice" so stat readouts don't
        look like combat.
        """
        for m in self._combat_regex.finditer(response):
            if m.group(0).lower().startswith("hit"):
                trailing = response[m.end() :].lstrip().lower()
                if trailing.startswith(("points", "point", "dice", "die")):
                    continue
            return True
        return False

    def _calculate_combat_damage(self, player_input: str, response: str) -> int:
        """Calculate combat damage when none is explicitly mentioned."""
        # Base damage: 1d6 (1-6)
        base_damage = random.randint(1, 6)

        # Modifiers based on keywords
        aggressive_words = [
            "attack",
            "strike",
            "smash",
            "destroy",
            "annihilate",
            "brutal",
        ]
        defensive_words = ["defend", "protect", "shield", "dodge", "evade"]

        input_lower = player_input.lower()
        response_lower = response.lower()

        # If player is aggressive and narrator confirms damage
        if any(word in input_lower for word in aggressive_words):
            if any(
                word in response_lower
                for word in ["hit", "struck", "damage", "wound", "fall", "defeated"]
            ):
                base_damage = random.randint(3, 8)

        # If narrator mentions critical hit or massive damage
        if any(
            word in response_lower
            for word in ["critical", "crushing", "devastating", "massive"]
        ):
            base_damage = random.randint(5, 10)

        # If narrator mentions enemy counterattack
        if any(
            word in response_lower
            for word in ["counterattack", "counter", "retaliation", "strike back"]
        ):
            base_damage = random.randint(1, 5)

        return base_damage

    def _extract_healing(self, response: str) -> int:
        """Extract healing values from response."""
        for pattern in self.healing_patterns:
            match = pattern.search(response)
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
            for match in pattern.finditer(response):
                try:
                    item = match.group(1).strip()
                    # Clean up
                    item = _LEADING_ARTICLE.sub("", item)
                    item = _TRAILING_PUNCT.sub("", item)
                    item = self._strip_markdown(item)

                    # Reject idioms that match pickup regex but aren't inventory.
                    # Match against the first word or first two words — narrow
                    # enough to keep "restorative potion" (starts with "rest")
                    # while still catching "deep breath and ...".
                    tokens = item.lower().split()
                    if tokens:
                        if tokens[0] in self.pickup_stopwords:
                            continue
                        if (
                            len(tokens) >= 2
                            and f"{tokens[0]} {tokens[1]}" in self.pickup_stopwords
                        ):
                            continue

                    # Avoid junk matches (too long or too vague)
                    if (
                        item
                        and len(item) < 60
                        and len(item.split()) <= 6
                        and item not in ["yourself", "your", "nothing"]
                    ):
                        items.append(item)
                except IndexError:
                    continue

        return items

    def _extract_items_lost(self, response: str) -> List[str]:
        """Extract items the player lost or dropped."""
        items = []

        for pattern in self.drop_patterns:
            for match in pattern.finditer(response):
                try:
                    item = match.group(1).strip()
                    # Clean up
                    item = _LEADING_ARTICLE.sub("", item)
                    item = _TRAILING_PUNCT.sub("", item)
                    item = self._strip_markdown(item)

                    if item and len(item) < 60 and len(item.split()) <= 6:
                        items.append(item)
                except IndexError:
                    continue

        return items

    def _extract_quest_offered(self, response: str) -> Optional[str]:
        """Extract quest title from response."""
        for pattern in self.quest_offer_patterns:
            match = pattern.search(response)
            if match:
                quest_title = match.group(1).strip()
                # Clean up
                quest_title = _TRAILING_PUNCT.sub("", quest_title)
                quest_title = self._strip_markdown(quest_title)
                if (
                    quest_title
                    and len(quest_title) < 100
                    and len(quest_title.split()) <= 8
                ):
                    return quest_title
        return None

    def _extract_quest_completed(self, response: str) -> Optional[str]:
        """Extract completed quest title from response."""
        for pattern in self.quest_complete_patterns:
            match = pattern.search(response)
            if match:
                quest_title = match.group(1).strip()
                # Clean up
                quest_title = _TRAILING_PUNCT.sub("", quest_title)
                quest_title = self._strip_markdown(quest_title)
                if (
                    quest_title
                    and len(quest_title) < 100
                    and len(quest_title.split()) <= 8
                ):
                    return quest_title
        return None

    def _extract_npc(self, response: str) -> Optional[str]:
        """Extract NPC name from response."""
        for pattern in self.npc_patterns:
            match = pattern.search(response)
            if match:
                npc_name = match.group(1).strip()
                # Clean up
                npc_name = _TRAILING_PUNCT.sub("", npc_name)
                npc_name = _LEADING_ARTICLE.sub("", npc_name)
                npc_name = self._strip_markdown(npc_name)
                # Strip trailing prepositional phrases ("wild fox in" → "wild fox")
                npc_name = self._trailing_prep_pattern.sub("", npc_name).strip()

                if not npc_name:
                    continue

                npc_lower = npc_name.lower()
                # Reject scenery/abstractions: any token is a stopword.
                if any(tok in self.npc_stopwords for tok in npc_lower.split()):
                    continue

                # Filter out common non-NPC words
                if len(npc_name) < 50 and len(npc_name.split()) <= 4:
                    if not any(
                        word in npc_lower
                        for word in ["your", "yourself", "the ground", "the air"]
                    ):
                        return npc_name
        return None
