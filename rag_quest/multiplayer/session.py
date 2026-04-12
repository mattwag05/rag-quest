"""Multiplayer session management (local/hot-seat)."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from uuid import uuid4


@dataclass
class PlayerState:
    """Individual player state in a multiplayer session."""
    player_name: str
    character_level: int = 1
    current_hp: int = 20
    max_hp: int = 20
    location: str = "Starting Location"
    inventory: List[str] = field(default_factory=list)
    completed_actions: int = 0

    def to_dict(self) -> dict:
        """Serialize player state."""
        return {
            "player_name": self.player_name,
            "character_level": self.character_level,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "location": self.location,
            "inventory": self.inventory,
            "completed_actions": self.completed_actions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerState":
        """Deserialize player state."""
        return cls(**data)


class MultiplayerSession:
    """A shared game session that multiple players can join (local/hot-seat)."""

    def __init__(self, session_id: Optional[str] = None, host_player: str = "Host",
                 world_name: str = None, max_players: int = None):
        """Initialize a multiplayer session.
        
        Args:
            session_id: Optional session ID. Defaults to generated UUID. (NEW API)
            host_player: Name of the host player (NEW API)
            world_name: World name (OLD API backwards compat)
            max_players: Max players (OLD API backwards compat)
        """
        # Handle backwards compatibility: MultiplayerSession(world_name, max_players)
        if world_name is not None and session_id is None:
            # Old style call: MultiplayerSession(world_name="...", max_players=4)
            session_id = f"session-{world_name.lower().replace(' ', '-')}"
            host_player = f"Host of {world_name}"
        
        # Store max_players for backwards compatibility
        self.max_players = max_players or 4
        self.session_id = session_id or str(uuid4())
        self.host_player = host_player
        self.players: Dict[str, PlayerState] = {}
        self.turn_order: List[str] = []
        self.current_turn_index: int = 0
        self.shared_world: Optional[dict] = None
        self.shared_events: List[str] = []
        self.is_active: bool = False
        # Store world_name for backwards compatibility
        self.world_name = world_name

    def create_session(self, host_name: str, world_config: dict) -> str:
        """Create and initialize a new session.
        
        Args:
            host_name: Name of the host player
            world_config: Initial world configuration dict
        
        Returns:
            Session ID
        """
        self.host_player = host_name
        self.shared_world = world_config.copy()
        self.is_active = True
        return self.session_id

    def join_session(self, player_name: str, character_level: int = 1) -> bool:
        """Add a player to the session.
        
        Args:
            player_name: Name of the player
            character_level: Initial character level
        
        Returns:
            True if successful, False if player already exists
        """
        if player_name in self.players:
            return False

        self.players[player_name] = PlayerState(
            player_name=player_name,
            character_level=character_level
        )
        self.turn_order.append(player_name)
        return True

    def leave_session(self, player_name: str) -> bool:
        """Remove a player from the session.
        
        Args:
            player_name: Name of the player
        
        Returns:
            True if successful, False if player not found
        """
        if player_name not in self.players:
            return False

        del self.players[player_name]
        if player_name in self.turn_order:
            self.turn_order.remove(player_name)

        # Adjust current turn if needed
        if self.current_turn_index >= len(self.turn_order) and self.turn_order:
            self.current_turn_index = 0

        return True

    def get_current_player(self) -> Optional[str]:
        """Get the name of the current player (whose turn it is).
        
        Returns:
            Player name, or None if no players
        """
        if not self.turn_order:
            return None
        return self.turn_order[self.current_turn_index]

    def advance_turn(self) -> Optional[str]:
        """Move to the next player's turn.
        
        Returns:
            Name of the next player, or None if no players
        """
        if not self.turn_order:
            return None

        self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)
        return self.get_current_player()

    def get_game_state(self, player_name: str) -> Optional[dict]:
        """Get the game state as seen by a specific player.
        
        Args:
            player_name: Name of the player
        
        Returns:
            Game state dict, or None if player not found
        """
        if player_name not in self.players:
            return None

        player = self.players[player_name]
        return {
            "session_id": self.session_id,
            "host_player": self.host_player,
            "current_player": self.get_current_player(),
            "is_your_turn": player_name == self.get_current_player(),
            "shared_world": self.shared_world,
            "players": {name: state.to_dict() for name, state in self.players.items()},
            "recent_events": self.shared_events[-5:],  # Last 5 events
            "your_state": player.to_dict(),
        }

    def submit_action(self, player_name: str, action: str) -> str:
        """Submit an action from a player.
        
        Args:
            player_name: Name of the player
            action: Action description
        
        Returns:
            Response string describing action result
        """
        if player_name not in self.players:
            return "Player not found."

        if player_name != self.get_current_player():
            return f"It is not your turn. {self.get_current_player()}'s turn."

        player = self.players[player_name]
        player.completed_actions += 1

        response = f"{player_name} performed: {action}"
        self.shared_events.append(response)

        return response

    def broadcast_event(self, event_text: str) -> None:
        """Notify all players of an event.
        
        Args:
            event_text: Event description
        """
        self.shared_events.append(event_text)

    def to_dict(self) -> dict:
        """Serialize session."""
        return {
            "session_id": self.session_id,
            "host_player": self.host_player,
            "players": {name: state.to_dict() for name, state in self.players.items()},
            "turn_order": self.turn_order,
            "current_turn_index": self.current_turn_index,
            "shared_world": self.shared_world,
            "shared_events": self.shared_events,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MultiplayerSession":
        """Deserialize session."""
        session = cls(
            session_id=data["session_id"],
            host_player=data["host_player"]
        )
        session.players = {
            name: PlayerState.from_dict(state)
            for name, state in data.get("players", {}).items()
        }
        session.turn_order = data.get("turn_order", [])
        session.current_turn_index = data.get("current_turn_index", 0)
        session.shared_world = data.get("shared_world")
        session.shared_events = data.get("shared_events", [])
        session.is_active = data.get("is_active", False)
        return session
