"""State synchronization for multiplayer sessions."""

from typing import Dict, List, Optional


class StateSync:
    """Synchronize game state between players in local multiplayer."""

    @staticmethod
    def sync_world_state(session: 'MultiplayerSession') -> dict:
        """Get synchronized world state visible to all players.
        
        Args:
            session: MultiplayerSession to sync
        
        Returns:
            Synchronized world state dict
        """
        if not session.shared_world:
            return {}

        # All players see the same world state
        world_state = session.shared_world.copy()
        world_state["active_players"] = len(session.players)
        world_state["current_turn_player"] = session.get_current_player()
        
        return world_state

    @staticmethod
    def merge_player_actions(session: 'MultiplayerSession') -> List[dict]:
        """Collect and merge all pending player actions.
        
        Args:
            session: MultiplayerSession to process
        
        Returns:
            List of action records
        """
        actions = []
        for player_name, player_state in session.players.items():
            if player_state.completed_actions > 0:
                actions.append({
                    "player": player_name,
                    "action_count": player_state.completed_actions,
                    "level": player_state.character_level,
                    "location": player_state.location,
                })
        
        return actions

    @staticmethod
    def resolve_conflicts(changes: Dict[str, any]) -> dict:
        """Resolve conflicts if multiple players affect the same state.
        
        Args:
            changes: Dict of attempted changes
        
        Returns:
            Resolved state changes
        """
        # For now, local multiplayer doesn't have significant conflicts
        # since turns are sequential. Future network multiplayer would need
        # more sophisticated conflict resolution.
        
        resolved = changes.copy()
        return resolved
