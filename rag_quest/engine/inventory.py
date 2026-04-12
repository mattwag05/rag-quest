"""Inventory system."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Item:
    """Represents an item."""

    name: str
    description: str
    weight: float = 1.0
    quantity: int = 1
    rarity: str = "common"  # common, uncommon, rare, legendary

    def to_dict(self) -> dict:
        """Convert item to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "weight": self.weight,
            "quantity": self.quantity,
            "rarity": self.rarity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Item":
        """Create item from dictionary."""
        return cls(**data)


class Inventory:
    """Manages character inventory."""

    def __init__(self, max_weight: float = 100.0):
        self.items: dict[str, Item] = {}
        self.max_weight = max_weight

    def add_item(
        self,
        name: str,
        description: str = "",
        quantity: int = 1,
        weight: float = 1.0,
        rarity: str = "common",
    ) -> bool:
        """Add an item to inventory. Returns True if successful."""
        item = Item(
            name=name,
            description=description,
            weight=weight,
            quantity=quantity,
            rarity=rarity,
        )

        if name in self.items:
            self.items[name].quantity += quantity
        else:
            if self.get_total_weight() + (weight * quantity) > self.max_weight:
                return False
            self.items[name] = item

        return True

    def remove_item(self, name: str, quantity: int = 1) -> bool:
        """Remove items from inventory. Returns True if successful."""
        if name not in self.items:
            return False

        self.items[name].quantity -= quantity
        if self.items[name].quantity <= 0:
            del self.items[name]

        return True

    def get_item(self, name: str) -> Optional[Item]:
        """Get an item from inventory."""
        return self.items.get(name)

    def get_total_weight(self) -> float:
        """Get total weight of inventory."""
        return sum(item.weight * item.quantity for item in self.items.values())

    def list_items(self) -> str:
        """Get formatted inventory list."""
        if not self.items:
            return "Your inventory is empty."

        lines = []
        for name, item in self.items.items():
            qty = f" x{item.quantity}" if item.quantity > 1 else ""
            lines.append(f"  {name}{qty} [{item.rarity}]")

        weight = self.get_total_weight()
        lines.append(f"\nCarrying {weight:.1f}/{self.max_weight:.1f} lbs")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert inventory to dictionary."""
        return {
            'items': {
                name: item.to_dict() for name, item in self.items.items()
            },
            'max_weight': self.max_weight
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Inventory":
        """Create inventory from dictionary."""
        max_weight = data.get('max_weight', 100.0)
        inv = cls(max_weight=max_weight)
        items_data = data.get('items', data)  # Support both old and new formats
        for item_data in items_data.values():
            item = Item.from_dict(item_data)
            inv.items[item.name] = item
        return inv
