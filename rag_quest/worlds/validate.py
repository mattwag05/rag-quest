"""Module manifest sanity checker — v0.7.

Non-interactive validator used by the `rag-quest validate-module <path>` CLI.
Author tooling runs this to catch common mistakes before runtime:

  * Schema errors (delegates to `load_modules` / `ModuleManifestError`)
  * Missing `lore_files`
  * Unknown `unlock_when_quests_completed` references (warning only — they
    may be narrative quests that aren't declared as another module's
    `completion_quest`)
  * Prerequisite graph cycles — detected via the implicit
    completion-quest → unlock dependency graph (module A completes quest Q,
    module B unlocks on Q, so A must finish before B is playable)

Quest-log presence checks are deferred to runtime: `ModuleRegistry.reevaluate`
handles missing quests by simply never transitioning that module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .modules import (
    MANIFEST_FILENAME,
    ModuleManifestError,
    ModuleRegistry,
    load_modules,
)


@dataclass
class ValidationResult:
    """Outcome of validating a modules.yaml manifest."""

    registry: ModuleRegistry | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_manifest(world_dir: Path | str) -> ValidationResult:
    """Validate a world's modules.yaml without ingesting lore into LightRAG.

    Returns a `ValidationResult` — callers decide how to render.
    """
    world_dir = Path(world_dir)
    result = ValidationResult()

    manifest_path = world_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        result.errors.append(f"No {MANIFEST_FILENAME} found at {manifest_path}")
        return result

    try:
        registry = load_modules(world_dir)  # no world_rag → no ingestion
    except ModuleManifestError as e:
        result.errors.append(f"{manifest_path}: {e}")
        return result

    result.registry = registry

    _check_lore_files(registry, world_dir, result)
    _check_unlock_references(registry, result)
    _check_prerequisite_cycles(registry, result)

    return result


def _check_lore_files(
    registry: ModuleRegistry, world_dir: Path, result: ValidationResult
) -> None:
    for module in registry.all():
        for lore_path in module.lore_files:
            resolved = (world_dir / lore_path).resolve()
            if not resolved.exists():
                result.errors.append(
                    f"module '{module.id}': lore file does not exist: {lore_path}"
                )


def _check_unlock_references(
    registry: ModuleRegistry, result: ValidationResult
) -> None:
    """Warn on unlock prereqs that no declared module completes.

    Such prereqs are assumed to be narrative quests the player will complete
    outside the module system. The warning just nudges authors to double-check
    for typos.
    """
    known_completion_quests = {
        m.completion_quest.lower() for m in registry.all() if m.completion_quest
    }
    for module in registry.all():
        for unlock in module.unlock_when_quests_completed:
            if unlock.lower() not in known_completion_quests:
                result.warnings.append(
                    f"module '{module.id}': unlock prereq '{unlock}' is not the "
                    f"completion_quest of any declared module — confirm it is a "
                    f"narrative quest the player can actually complete"
                )


def _check_prerequisite_cycles(
    registry: ModuleRegistry, result: ValidationResult
) -> None:
    """Detect cycles in the completion-quest → unlock dependency graph.

    Edge A → B exists when module A's `completion_quest` appears in module B's
    `unlock_when_quests_completed`. A cycle would mean module A can't complete
    until B unlocks, and B can't unlock until A completes — deadlock.
    """
    graph: dict[str, list[str]] = {m.id: [] for m in registry.all()}
    for a in registry.all():
        if not a.completion_quest:
            continue
        completion = a.completion_quest.lower()
        for b in registry.all():
            if a.id == b.id:
                continue
            if completion in (u.lower() for u in b.unlock_when_quests_completed):
                graph[a.id].append(b.id)

    WHITE, GRAY, BLACK = 0, 1, 2
    color = dict.fromkeys(graph, WHITE)
    reported: set[tuple[str, ...]] = set()

    def dfs(node: str, path: list[str]) -> None:
        if color[node] == GRAY:
            cycle_start = path.index(node)
            cycle = tuple(path[cycle_start:] + [node])
            key = tuple(sorted(cycle))  # dedupe rotations
            if key not in reported:
                reported.add(key)
                result.errors.append(
                    f"prerequisite cycle detected: {' → '.join(cycle)}"
                )
            return
        if color[node] == BLACK:
            return
        color[node] = GRAY
        path.append(node)
        for neighbor in graph[node]:
            dfs(neighbor, path)
        path.pop()
        color[node] = BLACK

    for module_id in graph:
        if color[module_id] == WHITE:
            dfs(module_id, [])
