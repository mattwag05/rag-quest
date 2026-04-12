"""Module manifest loader — v0.7 Modular Adventures.

A world directory may contain a top-level `modules.yaml` declaring one or more
hub-and-spoke adventures. On world load, `load_modules()` parses the manifest,
validates each entry against a known schema, and returns a `ModuleRegistry`.
When a `WorldRAG` is supplied, each module's `lore_files` are ingested into
the knowledge graph.

Schema (per module):

    modules:
      - id: goblin-cave                        # required, slug
        title: The Goblin Cave                 # required
        description: Clear the goblins ...     # required
        entry_location: Stonebridge            # required
        unlock_when_quests_completed: []       # optional, list[str]
        completion_quest: defeat-goblin-chief  # optional, str
        lore_files:                            # optional, list[str] — relative paths
          - lore/modules/goblin-cave.md
        rewards:                               # optional, dict
          xp: 200
          items: [goblin-chief-ring]

Zero-traceback principle: any malformed manifest raises `ModuleManifestError`
with a friendly, actionable message. Callers catch the error and surface it via
the existing `ui.print_error()` path rather than letting a raw PyYAML trace
leak into the game loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..knowledge import WorldRAG

MANIFEST_FILENAME = "modules.yaml"

_REQUIRED_FIELDS = ("id", "title", "description", "entry_location")
_OPTIONAL_FIELDS = (
    "unlock_when_quests_completed",
    "completion_quest",
    "lore_files",
    "rewards",
)
_ALL_FIELDS = set(_REQUIRED_FIELDS) | set(_OPTIONAL_FIELDS)


class ModuleManifestError(ValueError):
    """Raised when a modules.yaml file is malformed.

    The message is user-facing — game loop catches this and renders via
    `ui.print_error()`. Never leaks a PyYAML traceback.
    """


class ModuleStatus(Enum):
    """Lifecycle status of a declared module."""

    LOCKED = "locked"
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"


@dataclass
class Module:
    """A declared adventure module from a world's `modules.yaml`."""

    id: str
    title: str
    description: str
    entry_location: str
    unlock_when_quests_completed: list[str] = field(default_factory=list)
    completion_quest: Optional[str] = None
    lore_files: list[str] = field(default_factory=list)
    rewards: dict = field(default_factory=dict)
    status: ModuleStatus = ModuleStatus.LOCKED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "entry_location": self.entry_location,
            "unlock_when_quests_completed": list(self.unlock_when_quests_completed),
            "completion_quest": self.completion_quest,
            "lore_files": list(self.lore_files),
            "rewards": dict(self.rewards),
            "status": self.status.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Module":
        raw_status = data.get("status", ModuleStatus.LOCKED.name)
        try:
            status = ModuleStatus[raw_status]
        except KeyError:
            status = ModuleStatus.LOCKED
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            entry_location=data["entry_location"],
            unlock_when_quests_completed=list(
                data.get("unlock_when_quests_completed", [])
            ),
            completion_quest=data.get("completion_quest"),
            lore_files=list(data.get("lore_files", [])),
            rewards=dict(data.get("rewards", {})),
            status=status,
        )


class ModuleRegistry:
    """Holds all modules declared for a world plus their lifecycle state."""

    def __init__(
        self,
        modules: Optional[list[Module]] = None,
        compute_initial_states: bool = True,
    ) -> None:
        self._modules: dict[str, Module] = {}
        for m in modules or []:
            self._modules[m.id] = m
        if compute_initial_states:
            self._recompute_initial_states()

    def __len__(self) -> int:
        return len(self._modules)

    def __iter__(self):
        return iter(self._modules.values())

    def __contains__(self, module_id: str) -> bool:
        return module_id in self._modules

    def get(self, module_id: str) -> Optional[Module]:
        return self._modules.get(module_id)

    def all(self) -> list[Module]:
        return list(self._modules.values())

    def by_status(self, status: ModuleStatus) -> list[Module]:
        return [m for m in self._modules.values() if m.status == status]

    def _recompute_initial_states(self) -> None:
        """Set initial status: empty unlock list → available, else locked."""
        for m in self._modules.values():
            if not m.unlock_when_quests_completed and m.status == ModuleStatus.LOCKED:
                m.status = ModuleStatus.AVAILABLE

    def reevaluate(self, quest_log) -> list[Module]:
        """Transition module statuses based on the current QuestLog.

        Gating rules (monotonic — modules never go backwards):
          * LOCKED → AVAILABLE when every quest title in
            `unlock_when_quests_completed` is marked completed.
          * AVAILABLE / ACTIVE → COMPLETED when `completion_quest` (if set)
            is marked completed.

        Quest references in the manifest match against `Quest.title`
        case-insensitively. Returns the list of modules whose status changed
        on this call, so callers can surface unlock/completion notifications
        without polling.
        """
        # Lazy import: engine.quests pulls in engine/__init__.py → game.py →
        # worlds.modules, causing a cycle if hoisted to the top of this file.
        from ..engine.quests import QuestStatus

        completed_titles = {
            q.title.lower()
            for q in quest_log.quests
            if q.status == QuestStatus.COMPLETED
        }

        transitioned: list[Module] = []
        for module in self._modules.values():
            if module.status == ModuleStatus.COMPLETED:
                continue
            if (
                module.completion_quest
                and module.completion_quest.lower() in completed_titles
            ):
                module.status = ModuleStatus.COMPLETED
                transitioned.append(module)
                continue
            if module.status == ModuleStatus.LOCKED and all(
                q.lower() in completed_titles
                for q in module.unlock_when_quests_completed
            ):
                module.status = ModuleStatus.AVAILABLE
                transitioned.append(module)
        return transitioned

    def to_dict(self) -> dict:
        return {"modules": [m.to_dict() for m in self._modules.values()]}

    @classmethod
    def from_dict(cls, data: dict) -> "ModuleRegistry":
        mods = [Module.from_dict(m) for m in data.get("modules", [])]
        # Persisted statuses win over initial-state computation on reload.
        return cls(mods, compute_initial_states=False)


def load_modules(
    world_dir: Path | str,
    world_rag: Optional["WorldRAG"] = None,
) -> ModuleRegistry:
    """Load and validate a world's `modules.yaml`, ingesting referenced lore.

    Returns an empty `ModuleRegistry` when no manifest exists (modules are
    opt-in). When `world_rag` is provided, each module's `lore_files` are
    piped through `WorldRAG.ingest_file()` — failures are logged by
    `ingest_file` but do not abort loading.

    Raises `ModuleManifestError` on any schema problem.
    """
    import yaml

    world_dir = Path(world_dir)
    manifest_path = world_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        return ModuleRegistry()

    try:
        with manifest_path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except yaml.YAMLError as e:
        raise ModuleManifestError(
            f"{MANIFEST_FILENAME} is not valid YAML: {e}"
        ) from None
    except OSError as e:
        raise ModuleManifestError(f"Cannot read {manifest_path}: {e}") from None

    if raw is None:
        return ModuleRegistry()
    if not isinstance(raw, dict) or "modules" not in raw:
        raise ModuleManifestError(
            f"{MANIFEST_FILENAME} must be a mapping with a top-level 'modules:' key"
        )
    entries = raw["modules"]
    if not isinstance(entries, list):
        raise ModuleManifestError(
            f"{MANIFEST_FILENAME} 'modules' must be a list of module definitions"
        )

    modules: list[Module] = []
    seen_ids: set[str] = set()
    for idx, entry in enumerate(entries, start=1):
        modules.append(_parse_module(entry, idx, seen_ids))

    registry = ModuleRegistry(modules)

    if world_rag is not None:
        from .. import ui as _ui

        for module in registry.all():
            for lore_path in module.lore_files:
                resolved = (world_dir / lore_path).resolve()
                if not resolved.exists():
                    # Missing lore is a soft failure — warn and continue.
                    _ui.print_warning(
                        f"modules.yaml: module '{module.id}' references "
                        f"missing lore file {lore_path} (expected at {resolved})"
                    )
                    continue
                try:
                    world_rag.ingest_file(str(resolved))
                except Exception as e:
                    _ui.print_warning(
                        f"modules.yaml: failed to ingest {lore_path} "
                        f"for module '{module.id}': {e}"
                    )

    return registry


def _parse_module(entry, idx: int, seen_ids: set[str]) -> Module:
    """Validate a single module entry. Raises ModuleManifestError on any issue."""
    if not isinstance(entry, dict):
        raise ModuleManifestError(
            f"Module #{idx} in {MANIFEST_FILENAME} must be a mapping, got {type(entry).__name__}"
        )

    for required in _REQUIRED_FIELDS:
        if required not in entry or entry[required] in (None, ""):
            raise ModuleManifestError(
                f"Module #{idx} in {MANIFEST_FILENAME} is missing required field '{required}'"
            )

    unknown = set(entry) - _ALL_FIELDS
    if unknown:
        raise ModuleManifestError(
            f"Module '{entry.get('id', idx)}' in {MANIFEST_FILENAME} has "
            f"unknown field(s): {', '.join(sorted(unknown))}"
        )

    module_id = str(entry["id"]).strip()
    if not module_id:
        raise ModuleManifestError(
            f"Module #{idx} in {MANIFEST_FILENAME} has an empty 'id'"
        )
    if module_id in seen_ids:
        raise ModuleManifestError(
            f"Duplicate module id '{module_id}' in {MANIFEST_FILENAME}"
        )
    seen_ids.add(module_id)

    unlock = entry.get("unlock_when_quests_completed") or []
    if not isinstance(unlock, list) or not all(isinstance(q, str) for q in unlock):
        raise ModuleManifestError(
            f"Module '{module_id}': 'unlock_when_quests_completed' must be a list of strings"
        )

    lore_files = entry.get("lore_files") or []
    if not isinstance(lore_files, list) or not all(
        isinstance(f, str) for f in lore_files
    ):
        raise ModuleManifestError(
            f"Module '{module_id}': 'lore_files' must be a list of strings"
        )

    rewards = entry.get("rewards") or {}
    if not isinstance(rewards, dict):
        raise ModuleManifestError(f"Module '{module_id}': 'rewards' must be a mapping")

    return Module(
        id=module_id,
        title=str(entry["title"]),
        description=str(entry["description"]),
        entry_location=str(entry["entry_location"]),
        unlock_when_quests_completed=list(unlock),
        completion_quest=(
            str(entry["completion_quest"]) if entry.get("completion_quest") else None
        ),
        lore_files=list(lore_files),
        rewards=dict(rewards),
    )
