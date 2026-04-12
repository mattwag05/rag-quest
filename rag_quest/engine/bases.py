"""Hub Base entity — v0.7 Modular Adventures & Hub Bases.

A `Base` is a player-owned stronghold tied to a visited location. It has its own
storage (an `Inventory`), a roster of stationed NPCs (names that reference
`RelationshipManager`), a list of offered services, and an upgrade dict.

Bases live on `World.bases` and serialize via `to_dict` / `from_dict` alongside
existing world state. The save-format bump that accompanies claim/use flows
lives in a follow-up beads issue (see `rag-quest-vei`).
"""

from dataclasses import dataclass, field

from .inventory import Inventory


@dataclass
class Base:
    name: str
    location_ref: str
    storage: Inventory = field(default_factory=Inventory)
    stationed_npcs: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    upgrades: dict[str, int] = field(default_factory=dict)

    def add_service(self, service: str) -> bool:
        service = service.strip().lower()
        if not service or service in self.services:
            return False
        self.services.append(service)
        return True

    def station_npc(self, npc_name: str) -> bool:
        if not npc_name or npc_name in self.stationed_npcs:
            return False
        self.stationed_npcs.append(npc_name)
        return True

    def upgrade(self, key: str, delta: int = 1) -> int:
        self.upgrades[key] = self.upgrades.get(key, 0) + delta
        return self.upgrades[key]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "location_ref": self.location_ref,
            "storage": self.storage.to_dict(),
            "stationed_npcs": list(self.stationed_npcs),
            "services": list(self.services),
            "upgrades": dict(self.upgrades),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Base":
        return cls(
            name=data["name"],
            location_ref=data["location_ref"],
            storage=Inventory.from_dict(data["storage"]),
            stationed_npcs=list(data.get("stationed_npcs", [])),
            services=list(data.get("services", [])),
            upgrades=dict(data.get("upgrades", {})),
        )
