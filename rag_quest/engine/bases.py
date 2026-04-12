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

SERVICE_DESCRIPTIONS = {
    "smith": (
        "The smith can repair or upgrade weapons and armor brought by the "
        "player. They cannot forge legendary items from nothing."
    ),
    "healer": (
        "The healer can restore HP, cure status effects, and brew healing "
        "potions from components the player supplies."
    ),
    "innkeeper": (
        "The innkeeper provides rest (full HP restore overnight), meals, and "
        "local gossip about nearby factions and events."
    ),
    "storage": (
        "The caretaker manages the base storage. They can deposit or withdraw "
        "items from the player's inventory into the base vault."
    ),
    "stable": (
        "The stablemaster cares for mounts and can supply traveling beasts "
        "for long journeys."
    ),
    "library": (
        "The librarian can research lore topics, identify arcane items, and "
        "recall rumors about distant places."
    ),
}


@dataclass
class Base:
    name: str
    location_ref: str
    storage: Inventory = field(default_factory=Inventory)
    stationed_npcs: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    upgrades: dict[str, int] = field(default_factory=dict)
    # npc_name -> service role (e.g. "Durin" -> "smith"). Optional.
    npc_service: dict[str, str] = field(default_factory=dict)

    def add_service(self, service: str) -> bool:
        service = service.strip().lower()
        if not service or service in self.services:
            return False
        self.services.append(service)
        return True

    def station_npc(self, npc_name: str, service: str = "") -> bool:
        """Station an NPC at the base. Optionally bind them to a service role.

        Returns True if the NPC was newly stationed, False on duplicate.
        Updating an existing NPC's service role (e.g. promoting) is allowed
        even when this returns False — the service mapping is always applied.
        """
        if not npc_name:
            return False
        service_norm = service.strip().lower() if service else ""
        added = False
        if npc_name not in self.stationed_npcs:
            self.stationed_npcs.append(npc_name)
            added = True
        if service_norm:
            self.npc_service[npc_name] = service_norm
            if service_norm not in self.services:
                self.services.append(service_norm)
        return added

    def service_of(self, npc_name: str) -> str:
        """Return the service role of a stationed NPC, or empty string."""
        return self.npc_service.get(npc_name, "")

    def npcs_by_service(self) -> dict[str, list[str]]:
        """Group stationed NPCs by their service role.

        NPCs without a bound service are grouped under an empty-string key
        so callers can render them as "Unassigned" separately.
        """
        grouped: dict[str, list[str]] = {}
        for npc in self.stationed_npcs:
            service = self.npc_service.get(npc, "")
            grouped.setdefault(service, []).append(npc)
        return grouped

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
            "npc_service": dict(self.npc_service),
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
            npc_service=dict(data.get("npc_service", {})),
        )


def build_service_prompt_addendum(
    base: Base, npc_name: str, player_message: str
) -> str:
    """Build a narrator system-prompt addendum for a scoped NPC conversation.

    The returned string slots into the narrator's system prompt so the model
    knows which NPC is speaking, what service they offer, and the mechanics
    available. The addendum is deterministic — same inputs always produce
    the same text — which lets tests assert against it without spinning up
    an LLM.
    """
    service = base.service_of(npc_name)
    service_note = SERVICE_DESCRIPTIONS.get(
        service,
        "This NPC has no bound service role — keep the conversation in "
        "character with whatever their stationed role at the base implies.",
    )
    service_label = service or "general staff"
    return (
        f"=== BASE CONVERSATION ===\n"
        f"The player is at their base '{base.name}' in {base.location_ref}, "
        f"talking to **{npc_name}** ({service_label}).\n"
        f"Role details: {service_note}\n"
        f"Stay in character as {npc_name}. Reference the base by name when "
        f"natural. Keep responses short — 2 to 3 sentences — unless the "
        f"player asks for specifics.\n"
        f"Player says: {player_message}"
    )
