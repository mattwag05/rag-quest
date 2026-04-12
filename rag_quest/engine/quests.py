"""Quest system with chains and objectives."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List


class QuestStatus(Enum):
    """Quest status."""
    ACTIVE = "Active"
    COMPLETED = "Completed"
    FAILED = "Failed"
    ABANDONED = "Abandoned"


class ObjectiveType(Enum):
    """Types of quest objectives."""
    KILL = "Kill"
    FETCH = "Fetch"
    TALK = "Talk"
    EXPLORE = "Explore"
    ESCORT = "Escort"
    DELIVER = "Deliver"


@dataclass
class QuestObjective:
    """A single objective within a quest."""
    description: str
    objective_type: ObjectiveType
    target: str  # Enemy name, item name, NPC name, or location
    required_count: int = 1
    current_count: int = 0
    is_optional: bool = False

    def is_complete(self) -> bool:
        """Check if objective is complete."""
        return self.current_count >= self.required_count

    def increment(self, amount: int = 1) -> None:
        """Progress the objective."""
        self.current_count = min(self.required_count, self.current_count + amount)

    def to_dict(self) -> dict:
        """Serialize objective."""
        return {
            "description": self.description,
            "objective_type": self.objective_type.value,
            "target": self.target,
            "required_count": self.required_count,
            "current_count": self.current_count,
            "is_optional": self.is_optional,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QuestObjective":
        """Deserialize objective."""
        data = data.copy()
        data["objective_type"] = ObjectiveType(data["objective_type"])
        return cls(**data)


@dataclass
class QuestReward:
    """Reward for completing a quest."""
    xp: int = 0
    gold: int = 0
    items: List[str] = field(default_factory=list)
    reputation_changes: Dict[str, int] = field(default_factory=dict)
    unlocks: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize reward."""
        return {
            "xp": self.xp,
            "gold": self.gold,
            "items": self.items,
            "reputation_changes": self.reputation_changes,
            "unlocks": self.unlocks,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QuestReward":
        """Deserialize reward."""
        return cls(**data)


@dataclass
class Quest:
    """Represents a quest."""

    title: str
    description: str
    status: QuestStatus = QuestStatus.ACTIVE
    objectives: List[QuestObjective] = field(default_factory=list)
    reward: QuestReward = field(default_factory=QuestReward)
    giver_npc: str = "Unknown"
    required_level: int = 1

    def get_progress(self) -> str:
        """Get progress as a string."""
        if not self.objectives:
            return "No objectives"

        total = len(self.objectives)
        completed = sum(1 for obj in self.objectives if obj.is_complete())
        return f"{completed}/{total} objectives"

    def mark_objective_complete(self, objective_description: str) -> bool:
        """Mark an objective as complete by description."""
        for obj in self.objectives:
            if obj.description == objective_description and not obj.is_complete():
                obj.increment(obj.required_count)
                return True
        return False

    def increment_objective(self, objective_description: str, amount: int = 1) -> bool:
        """Increment an objective's progress."""
        for obj in self.objectives:
            if obj.description == objective_description:
                obj.increment(amount)
                return True
        return False

    def is_completed(self) -> bool:
        """Check if all required objectives are complete."""
        if not self.objectives:
            return False
        return all(obj.is_complete() for obj in self.objectives if not obj.is_optional)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "status": self.status.name,
            "objectives": [obj.to_dict() for obj in self.objectives],
            "reward": self.reward.to_dict(),
            "giver_npc": self.giver_npc,
            "required_level": self.required_level,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Quest":
        """Create from dictionary."""
        data = data.copy()
        data["status"] = QuestStatus[data["status"]]
        data["objectives"] = [QuestObjective.from_dict(obj) for obj in data.get("objectives", [])]
        data["reward"] = QuestReward.from_dict(data.get("reward", {}))
        return cls(**data)


@dataclass
class QuestChain:
    """A series of connected quests that tell a story."""
    chain_id: str
    title: str
    description: str
    quests: List[Quest] = field(default_factory=list)
    current_quest_index: int = 0
    branching_points: Dict[int, Dict[str, int]] = field(default_factory=dict)
    is_complete: bool = False
    lore_context: str = ""

    def get_current_quest(self) -> Optional[Quest]:
        """Get the current quest in the chain."""
        if self.current_quest_index < len(self.quests):
            return self.quests[self.current_quest_index]
        return None

    def advance(self, choice: Optional[str] = None) -> bool:
        """
        Advance to the next quest in the chain.
        
        Args:
            choice: For branching points, which branch to take
        
        Returns:
            True if advanced, False if chain is complete
        """
        if self.current_quest_index >= len(self.quests):
            return False

        # Check for branching point
        if self.current_quest_index in self.branching_points and choice:
            next_idx = self.branching_points[self.current_quest_index].get(choice)
            if next_idx is not None:
                self.current_quest_index = next_idx
                return True

        self.current_quest_index += 1
        if self.current_quest_index >= len(self.quests):
            self.is_complete = True
            return False

        return True

    def add_quest(self, quest: Quest) -> None:
        """Add a quest to the chain."""
        self.quests.append(quest)

    def add_branching_point(self, quest_index: int, choice: str, next_index: int) -> None:
        """Add a branching point to the chain."""
        if quest_index not in self.branching_points:
            self.branching_points[quest_index] = {}
        self.branching_points[quest_index][choice] = next_index

    def get_progress(self) -> str:
        """Get formatted progress."""
        return f"{self.current_quest_index + 1}/{len(self.quests)} quests complete"

    def to_dict(self) -> dict:
        """Serialize chain."""
        return {
            "chain_id": self.chain_id,
            "title": self.title,
            "description": self.description,
            "quests": [q.to_dict() for q in self.quests],
            "current_quest_index": self.current_quest_index,
            "branching_points": self.branching_points,
            "is_complete": self.is_complete,
            "lore_context": self.lore_context,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QuestChain":
        """Deserialize chain."""
        data = data.copy()
        data["quests"] = [Quest.from_dict(q) for q in data.get("quests", [])]
        return cls(**data)


class QuestLog:
    """Manages quests and quest chains."""

    def __init__(self):
        self.quests: List[Quest] = []
        self.quest_chains: Dict[str, QuestChain] = {}

    def add_quest(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        objectives: Optional[List[QuestObjective]] = None,
        reward: Optional[QuestReward] = None,
        giver_npc: str = "Unknown",
        required_level: int = 1,
        reward_xp: int = 0,
        reward_description: str = "",
    ) -> Quest:
        """Add a new quest. Can be called with either a Quest object or individual fields."""
        # Handle both calling styles: add_quest(quest_object) or add_quest(title=..., description=...)
        if isinstance(title, Quest):
            # Called with Quest object as first positional argument
            quest = title
        else:
            # Called with individual fields
            # Handle reward_xp / reward_description style arguments from narrator.py
            if reward_xp or reward_description:
                reward = QuestReward(xp=reward_xp, gold=0)
            
            quest = Quest(
                title=title or "Untitled Quest",
                description=description or "",
                objectives=objectives or [],
                reward=reward or QuestReward(),
                giver_npc=giver_npc,
                required_level=required_level,
            )
        
        self.quests.append(quest)
        return quest

    def add_quest_chain(self, chain: QuestChain) -> None:
        """Add a quest chain."""
        self.quest_chains[chain.chain_id] = chain

    def get_quest_chain(self, chain_id: str) -> Optional[QuestChain]:
        """Get a quest chain by ID."""
        return self.quest_chains.get(chain_id)

    def get_active_quests(self) -> List[Quest]:
        """Get all active quests."""
        return [q for q in self.quests if q.status == QuestStatus.ACTIVE]

    def get_quest_by_title(self, title: str) -> Optional[Quest]:
        """Find a quest by title."""
        for quest in self.quests:
            if quest.title.lower() == title.lower():
                return quest
        return None

    def complete_quest(self, title: str) -> bool:
        """Mark a quest as completed."""
        quest = self.get_quest_by_title(title)
        if quest:
            quest.status = QuestStatus.COMPLETED
            return True
        return False

    def list_quests(self) -> str:
        """Get formatted quest list."""
        if not self.quests:
            return "No quests."

        lines = []
        for q in self.get_active_quests():
            progress = q.get_progress()
            lines.append(f"  [{q.status.value}] {q.title} - {progress}")

        return "\n".join(lines) if lines else "No active quests."

    def list_quest_chains(self) -> str:
        """Get formatted quest chain list."""
        if not self.quest_chains:
            return "No quest chains."

        lines = []
        for chain in self.quest_chains.values():
            status = "Complete" if chain.is_complete else "In Progress"
            progress = chain.get_progress()
            lines.append(f"  [{status}] {chain.title} - {progress}")

        return "\n".join(lines) if lines else "No quest chains."

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "quests": [q.to_dict() for q in self.quests],
            "quest_chains": {cid: chain.to_dict() for cid, chain in self.quest_chains.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QuestLog":
        """Create from dictionary."""
        log = cls()
        for quest_data in data.get("quests", []):
            log.quests.append(Quest.from_dict(quest_data))
        for chain_data in data.get("quest_chains", {}).values():
            log.quest_chains[chain_data["chain_id"]] = QuestChain.from_dict(chain_data)
        return log
