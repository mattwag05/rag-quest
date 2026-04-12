"""Procedural dungeon generation and exploration."""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4


class RoomType(Enum):
    """Types of dungeon rooms."""
    CORRIDOR = "corridor"
    CHAMBER = "chamber"
    BOSS_ROOM = "boss_room"
    TREASURE_ROOM = "treasure_room"
    TRAP_ROOM = "trap_room"
    SHRINE = "shrine"


class DifficultyLevel(Enum):
    """Dungeon difficulty."""
    EASY = "easy"
    NORMAL = "normal"
    MEDIUM = "normal"  # Alias for NORMAL for backwards compatibility
    HARD = "hard"


@dataclass
class DungeonRoom:
    """A single room in a dungeon."""
    room_id: str
    room_type: RoomType
    description: str
    enemies: List[str] = field(default_factory=list)
    items: List[str] = field(default_factory=list)
    exits: Dict[str, str] = field(default_factory=dict)  # direction -> room_id
    is_explored: bool = False
    has_trap: bool = False
    treasure_value: int = 0

    def to_dict(self) -> dict:
        """Serialize room."""
        return {
            "room_id": self.room_id,
            "room_type": self.room_type.value,
            "description": self.description,
            "enemies": self.enemies,
            "items": self.items,
            "exits": self.exits,
            "is_explored": self.is_explored,
            "has_trap": self.has_trap,
            "treasure_value": self.treasure_value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DungeonRoom":
        """Deserialize room."""
        data = data.copy()
        data["room_type"] = RoomType(data["room_type"])
        return cls(**data)


class Dungeon:
    """A complete procedurally generated dungeon."""

    def __init__(self, dungeon_id: Optional[str] = None,
                 depth: int = 5, difficulty: str = "normal"):
        """Initialize dungeon.
        
        Args:
            dungeon_id: Optional ID. Defaults to UUID.
            depth: Number of levels deep (affects room count, 5-15 rooms)
            difficulty: "easy", "normal", or "hard"
        """
        self.dungeon_id = dungeon_id or str(uuid4())
        self.depth = depth
        self.difficulty = DifficultyLevel(difficulty)
        self.rooms: Dict[str, DungeonRoom] = {}
        self.entrance: Optional[str] = None
        self.boss_room: Optional[str] = None
        self.current_room: Optional[str] = None
        self.is_cleared: bool = False
        self.visited_rooms: set[str] = set()

    def get_map_ascii(self) -> str:
        """Generate an ASCII map of explored rooms.
        
        Returns:
            ASCII representation of the dungeon map
        """
        if not self.rooms:
            return "Empty dungeon"

        lines = ["Dungeon Map:", "============"]
        for room_id, room in self.rooms.items():
            explored = "✓" if room.is_explored else "?"
            room_symbol = {
                RoomType.CORRIDOR: "—",
                RoomType.CHAMBER: "●",
                RoomType.BOSS_ROOM: "★",
                RoomType.TREASURE_ROOM: "♦",
                RoomType.TRAP_ROOM: "⚡",
                RoomType.SHRINE: "✦",
            }.get(room.room_type, "●")

            current = " <--" if room_id == self.current_room else ""
            lines.append(f"  {explored} {room_symbol} {room.description}{current}")

        return "\n".join(lines)

    def enter(self) -> Optional[DungeonRoom]:
        """Enter the dungeon at the entrance.
        
        Returns:
            The entrance room
        """
        if self.entrance:
            self.current_room = self.entrance
            if self.entrance in self.rooms:
                room = self.rooms[self.entrance]
                room.is_explored = True
                self.visited_rooms.add(self.entrance)
                return room
        return None

    def move(self, direction: str) -> Optional[DungeonRoom]:
        """Move to an adjacent room.
        
        Args:
            direction: Direction to move (north, south, east, west, up, down)
        
        Returns:
            The new room, or None if can't move that way
        """
        if not self.current_room or self.current_room not in self.rooms:
            return None

        current = self.rooms[self.current_room]
        direction_lower = direction.lower()

        if direction_lower not in current.exits:
            return None

        next_room_id = current.exits[direction_lower]
        if next_room_id not in self.rooms:
            return None

        self.current_room = next_room_id
        next_room = self.rooms[next_room_id]
        next_room.is_explored = True
        self.visited_rooms.add(next_room_id)

        return next_room

    def to_dict(self) -> dict:
        """Serialize dungeon."""
        return {
            "dungeon_id": self.dungeon_id,
            "depth": self.depth,
            "difficulty": self.difficulty.value,
            "rooms": {rid: room.to_dict() for rid, room in self.rooms.items()},
            "entrance": self.entrance,
            "boss_room": self.boss_room,
            "current_room": self.current_room,
            "is_cleared": self.is_cleared,
            "visited_rooms": list(self.visited_rooms),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Dungeon":
        """Deserialize dungeon."""
        dungeon = cls(
            dungeon_id=data["dungeon_id"],
            depth=data["depth"],
            difficulty=data["difficulty"]
        )
        dungeon.rooms = {
            rid: DungeonRoom.from_dict(rdata)
            for rid, rdata in data.get("rooms", {}).items()
        }
        dungeon.entrance = data.get("entrance")
        dungeon.boss_room = data.get("boss_room")
        dungeon.current_room = data.get("current_room")
        dungeon.is_cleared = data.get("is_cleared", False)
        dungeon.visited_rooms = set(data.get("visited_rooms", []))
        return dungeon


class DungeonGenerator:
    """Generate procedural dungeons."""

    ROOM_DESCRIPTIONS = {
        RoomType.CORRIDOR: [
            "A narrow stone corridor echoes with your footsteps",
            "A long hallway stretches before you",
            "Torchlit passage with crumbling walls",
        ],
        RoomType.CHAMBER: [
            "A spacious underground chamber",
            "A grand hall with pillars",
            "An ancient gathering place",
        ],
        RoomType.BOSS_ROOM: [
            "The lair of the dungeon's master",
            "A throne room of dark power",
            "The heart of the dungeon",
        ],
        RoomType.TREASURE_ROOM: [
            "A vault filled with glimmering treasure",
            "Gold and jewels shimmer before you",
            "The spoils of conquest",
        ],
        RoomType.TRAP_ROOM: [
            "A dangerous chamber with hidden mechanisms",
            "Pressure plates and pendulums",
            "A room designed to kill",
        ],
        RoomType.SHRINE: [
            "An ancient shrine to forgotten gods",
            "An altar of power",
            "A place of healing magic",
        ],
    }

    ENEMIES_BY_DIFFICULTY = {
        DifficultyLevel.EASY: ["Goblin", "Skeleton", "Giant Rat"],
        DifficultyLevel.NORMAL: ["Orc", "Zombie", "Giant Spider", "Cultist"],
        DifficultyLevel.HARD: ["Ogre", "Wraith", "Demon", "Ancient Guardian"],
    }

    ITEMS_BY_DIFFICULTY = {
        DifficultyLevel.EASY: [
            "Iron Sword", "Leather Armor", "Health Potion",
            "Gold Coins", "Torch"
        ],
        DifficultyLevel.NORMAL: [
            "Steel Sword", "Chainmail", "Greater Health Potion",
            "Gemstone", "Magic Scroll"
        ],
        DifficultyLevel.HARD: [
            "Enchanted Blade", "Plate Armor", "Elixir",
            "Cursed Crown", "Ancient Artifact"
        ],
    }

    @staticmethod
    def generate(depth: int = 5, difficulty: str = "normal") -> Dungeon:
        """Generate a new dungeon.
        
        Args:
            depth: Number of levels (controls room count: 5-15)
            difficulty: "easy", "normal", or "hard"
        
        Returns:
            Generated Dungeon object
        """
        dungeon = Dungeon(depth=depth, difficulty=difficulty)
        diff_enum = DifficultyLevel(difficulty)

        # Generate room count based on depth
        room_count = min(5 + depth, 15)

        # Create rooms
        rooms_created = []
        for i in range(room_count):
            room_id = str(uuid4())[:8]

            # Determine room type
            if i == 0:
                room_type = RoomType.CORRIDOR  # Entrance
            elif i == room_count - 1:
                room_type = RoomType.BOSS_ROOM  # Boss room at end
            else:
                weights = {
                    RoomType.CORRIDOR: 4,
                    RoomType.CHAMBER: 3,
                    RoomType.TREASURE_ROOM: 1,
                    RoomType.TRAP_ROOM: 1,
                    RoomType.SHRINE: 1,
                }
                room_type = random.choices(
                    list(weights.keys()),
                    weights=list(weights.values())
                )[0]

            description = random.choice(
                DungeonGenerator.ROOM_DESCRIPTIONS[room_type]
            )

            # Generate enemies based on difficulty
            enemies = []
            enemy_count = random.randint(
                0 if room_type == RoomType.CORRIDOR else 1,
                3 if diff_enum == DifficultyLevel.HARD else 2
            )
            if room_type != RoomType.TREASURE_ROOM and room_type != RoomType.SHRINE:
                enemies = random.choices(
                    DungeonGenerator.ENEMIES_BY_DIFFICULTY[diff_enum],
                    k=enemy_count
                )

            # Generate items
            items = []
            if room_type in (RoomType.TREASURE_ROOM, RoomType.CHAMBER):
                items = random.sample(
                    DungeonGenerator.ITEMS_BY_DIFFICULTY[diff_enum],
                    k=random.randint(1, 3)
                )

            room = DungeonRoom(
                room_id=room_id,
                room_type=room_type,
                description=description,
                enemies=enemies,
                items=items,
                has_trap=(room_type == RoomType.TRAP_ROOM),
                treasure_value=random.randint(50, 200) if room_type == RoomType.TREASURE_ROOM else 0,
            )

            dungeon.rooms[room_id] = room
            rooms_created.append(room_id)

            if i == 0:
                dungeon.entrance = room_id
            elif i == room_count - 1:
                dungeon.boss_room = room_id

        # Create connections between rooms
        for i in range(len(rooms_created) - 1):
            current_room_id = rooms_created[i]
            next_room_id = rooms_created[i + 1]

            # Random direction
            directions = ["north", "south", "east", "west", "down", "up"]
            direction = random.choice(directions)

            dungeon.rooms[current_room_id].exits[direction] = next_room_id
            dungeon.rooms[next_room_id].exits["back"] = current_room_id

        dungeon.current_room = dungeon.entrance
        return dungeon
    
    @staticmethod
    def generate_level(level: int, difficulty: str = "normal") -> "Dungeon":
        """Generate a single dungeon level (backwards compatibility alias).
        
        Args:
            level: Dungeon level (used as depth)
            difficulty: Difficulty level
        
        Returns:
            Generated Dungeon
        """
        # Map difficulty strings to appropriate depth
        depth_map = {"easy": 3, "normal": 5, "hard": 8, "deadly": 10}
        depth = depth_map.get(difficulty.lower(), 5) + (level - 1)
        
        return DungeonGenerator.generate(depth=depth, difficulty=difficulty)
