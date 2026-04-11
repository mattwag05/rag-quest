"""Quest system."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class QuestStatus(Enum):
    """Quest status."""

    ACTIVE = "Active"
    COMPLETED = "Completed"
    FAILED = "Failed"
    ABANDONED = "Abandoned"


@dataclass
class Quest:
    """Represents a quest."""

    title: str
    description: str
    status: QuestStatus = QuestStatus.ACTIVE
    objectives: list[str] = field(default_factory=list)
    completed_objectives: list[str] = field(default_factory=list)
    reward_xp: int = 0
    reward_description: str = ""

    def get_progress(self) -> str:
        """Get progress as a string."""
        if not self.objectives:
            return "No objectives"

        total = len(self.objectives)
        completed = len(self.completed_objectives)
        return f"{completed}/{total} objectives"

    def mark_objective_complete(self, objective: str) -> bool:
        """Mark an objective as complete."""
        if objective in self.objectives and objective not in self.completed_objectives:
            self.completed_objectives.append(objective)
            return True
        return False

    def is_completed(self) -> bool:
        """Check if all objectives are complete."""
        return (
            len(self.objectives) > 0
            and len(self.completed_objectives) == len(self.objectives)
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "status": self.status.name,
            "objectives": self.objectives,
            "completed_objectives": self.completed_objectives,
            "reward_xp": self.reward_xp,
            "reward_description": self.reward_description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Quest":
        """Create from dictionary."""
        data = data.copy()
        data["status"] = QuestStatus[data["status"]]
        return cls(**data)


class QuestLog:
    """Manages quests."""

    def __init__(self):
        self.quests: list[Quest] = []

    def add_quest(
        self,
        title: str,
        description: str,
        objectives: Optional[list[str]] = None,
        reward_xp: int = 0,
        reward_description: str = "",
    ) -> Quest:
        """Add a new quest."""
        quest = Quest(
            title=title,
            description=description,
            objectives=objectives or [],
            reward_xp=reward_xp,
            reward_description=reward_description,
        )
        self.quests.append(quest)
        return quest

    def get_active_quests(self) -> list[Quest]:
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

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {"quests": [q.to_dict() for q in self.quests]}

    @classmethod
    def from_dict(cls, data: dict) -> "QuestLog":
        """Create from dictionary."""
        log = cls()
        for quest_data in data.get("quests", []):
            log.quests.append(Quest.from_dict(quest_data))
        return log
