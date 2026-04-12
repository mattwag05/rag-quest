"""Trading system for multiplayer sessions."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4


class TradeStatus(Enum):
    """Status of a trade proposal."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Trade:
    """A trade proposal between two players."""
    trade_id: str
    from_player: str
    to_player: str
    offer_items: List[str] = field(default_factory=list)
    request_items: List[str] = field(default_factory=list)
    status: TradeStatus = TradeStatus.PENDING
    created_turn: int = 0
    responded_turn: Optional[int] = None

    def to_dict(self) -> dict:
        """Serialize trade."""
        return {
            "trade_id": self.trade_id,
            "from_player": self.from_player,
            "to_player": self.to_player,
            "offer_items": self.offer_items,
            "request_items": self.request_items,
            "status": self.status.value,
            "created_turn": self.created_turn,
            "responded_turn": self.responded_turn,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Trade":
        """Deserialize trade."""
        data = data.copy()
        data["status"] = TradeStatus(data["status"])
        return cls(**data)


class TradeManager:
    """Handle item trading between players in a session."""

    def __init__(self):
        """Initialize trade manager."""
        self.trades: Dict[str, Trade] = {}
        self.pending_trades: List[str] = []

    def propose_trade(self, from_player: str, to_player: str,
                      offer_items: List[str], request_items: List[str],
                      current_turn: int = 0) -> Trade:
        """Propose a trade between two players.
        
        Args:
            from_player: Name of player making offer
            to_player: Name of player receiving offer
            offer_items: Items player is offering
            request_items: Items player is requesting
            current_turn: Current game turn
        
        Returns:
            Trade object
        """
        trade_id = str(uuid4())
        trade = Trade(
            trade_id=trade_id,
            from_player=from_player,
            to_player=to_player,
            offer_items=offer_items,
            request_items=request_items,
            status=TradeStatus.PENDING,
            created_turn=current_turn,
        )

        self.trades[trade_id] = trade
        self.pending_trades.append(trade_id)
        return trade

    def accept_trade(self, trade_id: str, current_turn: int = 0) -> bool:
        """Accept a trade proposal.
        
        Args:
            trade_id: ID of the trade to accept
            current_turn: Current game turn
        
        Returns:
            True if accepted, False if trade not found or already responded
        """
        if trade_id not in self.trades:
            return False

        trade = self.trades[trade_id]
        if trade.status != TradeStatus.PENDING:
            return False

        trade.status = TradeStatus.ACCEPTED
        trade.responded_turn = current_turn
        if trade_id in self.pending_trades:
            self.pending_trades.remove(trade_id)

        return True

    def reject_trade(self, trade_id: str, current_turn: int = 0) -> bool:
        """Reject a trade proposal.
        
        Args:
            trade_id: ID of the trade to reject
            current_turn: Current game turn
        
        Returns:
            True if rejected, False if trade not found or already responded
        """
        if trade_id not in self.trades:
            return False

        trade = self.trades[trade_id]
        if trade.status != TradeStatus.PENDING:
            return False

        trade.status = TradeStatus.REJECTED
        trade.responded_turn = current_turn
        if trade_id in self.pending_trades:
            self.pending_trades.remove(trade_id)

        return True

    def list_pending_trades(self, player_name: str) -> List[Trade]:
        """List all pending trades for a player (as recipient).
        
        Args:
            player_name: Name of the player
        
        Returns:
            List of pending Trade objects
        """
        pending = []
        for trade_id in self.pending_trades:
            trade = self.trades[trade_id]
            if trade.to_player == player_name:
                pending.append(trade)

        return pending

    def get_completed_trades(self, player_name: str) -> List[Trade]:
        """Get all completed trades involving a player.
        
        Args:
            player_name: Name of the player
        
        Returns:
            List of completed Trade objects
        """
        completed = []
        for trade in self.trades.values():
            if trade.status == TradeStatus.COMPLETED:
                if trade.from_player == player_name or trade.to_player == player_name:
                    completed.append(trade)

        return completed

    def to_dict(self) -> dict:
        """Serialize trade manager."""
        return {
            "trades": {tid: trade.to_dict() for tid, trade in self.trades.items()},
            "pending_trades": self.pending_trades,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradeManager":
        """Deserialize trade manager."""
        manager = cls()
        manager.trades = {
            tid: Trade.from_dict(tdata)
            for tid, tdata in data.get("trades", {}).items()
        }
        manager.pending_trades = data.get("pending_trades", [])
        return manager
