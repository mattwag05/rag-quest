"""Interactive module-author tooling — v0.7.

Powers `rag-quest new-module <world-dir>`. Walks a manifest author through
the `Module` schema with Rich prompts, writes a validated stanza to
`modules.yaml` (creating the file if missing), and optionally stubs a
lore-file template under `lore/modules/<id>.md`.

The interactive layer is thin — all the hard work (schema validation,
unique-id check, cycle detection) is delegated to `load_modules` and
`validate_manifest`, which this tool invokes on the resulting file.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .modules import MANIFEST_FILENAME, ModuleManifestError, load_modules
from .validate import validate_manifest

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*$")

LORE_TEMPLATE = """\
# {title}

## Overview

{description}

## Entry point

The player arrives at **{entry_location}**.

## Key NPCs

- (add the NPCs the player will meet here)

## Key Locations

- (add the notable sub-locations inside the module here)

## Hooks

- (add any quest hooks / plot beats here)

## Completion

{completion_note}
"""


@dataclass
class NewModuleAnswers:
    """Plain-data carrier for the interactive answers.

    Exposed as a struct rather than a bag of args so the writer can be unit
    tested without going through Rich prompts.
    """

    id: str
    title: str
    description: str
    entry_location: str
    completion_quest: Optional[str] = None
    unlock_when_quests_completed: list[str] = field(default_factory=list)
    lore_file: Optional[str] = None  # relative to world_dir
    create_lore_stub: bool = False
    rewards_xp: int = 0


def slugify(text: str) -> str:
    """Fallback id generator: lowercase, hyphen-separated, alnum-only."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "module"


def render_stanza(answers: NewModuleAnswers) -> str:
    """Render a single module stanza as YAML text — always valid, minimal fields only."""
    lines = [
        f"  - id: {answers.id}",
        f"    title: {_yaml_str(answers.title)}",
        f"    description: {_yaml_str(answers.description)}",
        f"    entry_location: {_yaml_str(answers.entry_location)}",
    ]
    if answers.unlock_when_quests_completed:
        lines.append("    unlock_when_quests_completed:")
        for q in answers.unlock_when_quests_completed:
            lines.append(f"      - {_yaml_str(q)}")
    if answers.completion_quest:
        lines.append(f"    completion_quest: {_yaml_str(answers.completion_quest)}")
    if answers.lore_file:
        lines.append("    lore_files:")
        lines.append(f"      - {_yaml_str(answers.lore_file)}")
    if answers.rewards_xp:
        lines.append("    rewards:")
        lines.append(f"      xp: {answers.rewards_xp}")
    return "\n".join(lines) + "\n"


def _yaml_str(value: str) -> str:
    """Quote strings that need it, bare ones that don't.

    Keeps the output diff-friendly by not over-quoting.
    """
    if not value:
        return '""'
    if re.match(r"^[A-Za-z0-9 _./'-]+$", value) and not value[0].isdigit():
        # Still quote if it starts/ends with whitespace or contains a colon.
        if ":" not in value and value == value.strip():
            return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def write_module(
    world_dir: Path | str,
    answers: NewModuleAnswers,
    *,
    lore_body: Optional[str] = None,
) -> Path:
    """Append a new module stanza to `world_dir/modules.yaml`.

    Creates the manifest with a `modules:` header if missing, runs
    `validate_manifest` on the result, and (optionally) drops a lore-file
    stub at the declared path. Raises `ModuleManifestError` if the new
    stanza would collide with an existing module id, reference a lore
    file that's missing, or trip any validator check.
    """
    world_dir = Path(world_dir)
    world_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = world_dir / MANIFEST_FILENAME

    if not _ID_RE.match(answers.id):
        raise ModuleManifestError(
            f"Invalid module id '{answers.id}' — must be lowercase, start with a "
            "letter or digit, and contain only [a-z0-9-]"
        )

    # Collision check against the existing (if any) manifest.
    if manifest_path.exists():
        try:
            existing = load_modules(world_dir)
        except ModuleManifestError as e:
            raise ModuleManifestError(
                f"Existing {MANIFEST_FILENAME} is already broken — fix it before "
                f"adding more modules:\n  {e}"
            ) from None
        if answers.id in existing:
            raise ModuleManifestError(
                f"Module id '{answers.id}' already exists in {manifest_path}"
            )

    if answers.create_lore_stub and answers.lore_file:
        lore_abs = (world_dir / answers.lore_file).resolve()
        try:
            lore_abs.relative_to(world_dir.resolve())
        except ValueError:
            raise ModuleManifestError(
                f"Lore file path '{answers.lore_file}' escapes the world directory"
            ) from None
        if not lore_abs.exists():
            lore_abs.parent.mkdir(parents=True, exist_ok=True)
            lore_abs.write_text(
                lore_body
                or LORE_TEMPLATE.format(
                    title=answers.title,
                    description=answers.description,
                    entry_location=answers.entry_location,
                    completion_note=(
                        f"Completed when the quest **{answers.completion_quest}** "
                        "is marked done."
                        if answers.completion_quest
                        else "Completion quest not declared — set one if the "
                        "player needs a definitive finish."
                    ),
                )
            )

    stanza = render_stanza(answers)
    if manifest_path.exists():
        body = manifest_path.read_text()
        if "modules:" not in body:
            body = "modules:\n" + body
        if not body.endswith("\n"):
            body += "\n"
        body += stanza
        manifest_path.write_text(body)
    else:
        manifest_path.write_text("modules:\n" + stanza)

    result = validate_manifest(world_dir)
    if not result.ok:
        # Roll back the append so the author's manifest doesn't get wedged.
        if manifest_path.exists():
            body_now = manifest_path.read_text()
            if body_now.endswith(stanza):
                body_now = body_now[: -len(stanza)]
                manifest_path.write_text(body_now)
        raise ModuleManifestError(
            "Module would leave the manifest in an invalid state:\n  "
            + "\n  ".join(result.errors)
        )

    return manifest_path


# ---------------------------------------------------------------------------
# Interactive CLI entry point
# ---------------------------------------------------------------------------


def run_interactive(
    world_dir: Path | str,
    prompt_fn: Optional[Callable[..., str]] = None,
    confirm_fn: Optional[Callable[..., bool]] = None,
    int_prompt_fn: Optional[Callable[..., int]] = None,
    printer: Optional[Callable[[str], None]] = None,
) -> Path:
    """Drive the interactive `rag-quest new-module` flow.

    The prompt / confirm / printer callables are injectable so the test suite
    can exercise the whole pipeline deterministically without Rich. Default
    implementations fall back to Rich prompts for the real CLI.
    """
    world_dir = Path(world_dir)

    if (
        prompt_fn is None
        or confirm_fn is None
        or int_prompt_fn is None
        or printer is None
    ):
        from rich.console import Console
        from rich.prompt import Confirm, IntPrompt, Prompt

        _console = Console()
        prompt_fn = prompt_fn or Prompt.ask
        confirm_fn = confirm_fn or Confirm.ask
        int_prompt_fn = int_prompt_fn or IntPrompt.ask
        printer = printer or _console.print

    existing_module_ids: list[str] = []
    existing_manifest = world_dir / MANIFEST_FILENAME
    if existing_manifest.exists():
        try:
            registry = load_modules(world_dir)
            existing_module_ids = [m.id for m in registry.all()]
        except ModuleManifestError as e:
            printer(
                f"[yellow]Existing {MANIFEST_FILENAME} is broken and needs "
                f"repair before adding new modules:[/yellow] {e}"
            )
            raise

    printer(f"[bold cyan]Create a new module in {world_dir}[/bold cyan]")
    if existing_module_ids:
        printer(f"Existing module ids: {', '.join(existing_module_ids)}")

    title = prompt_fn("Module title")
    suggested_id = slugify(title)
    module_id = prompt_fn("Module id (slug)", default=suggested_id)
    description = prompt_fn("One-sentence description")
    entry_location = prompt_fn("Entry location (a place name in your world)")

    has_completion = confirm_fn(
        "Does this module have a completion quest?", default=True
    )
    completion_quest = (
        prompt_fn(
            "Completion quest title (must match a Quest.title at runtime, "
            "case-insensitive)"
        )
        if has_completion
        else None
    )

    unlock: list[str] = []
    if existing_module_ids and confirm_fn(
        "Add prerequisite modules whose completion_quest must be done first?",
        default=False,
    ):
        raw = prompt_fn("Prereq module ids (comma-separated)", default="")
        picked = [x.strip() for x in raw.split(",") if x.strip()]
        registry = load_modules(world_dir)
        for pid in picked:
            module = registry.get(pid)
            if module is None:
                printer(f"[yellow]skipping unknown module id: {pid}[/yellow]")
                continue
            if not module.completion_quest:
                printer(
                    f"[yellow]skipping '{pid}': no completion_quest declared — "
                    "can't gate on it[/yellow]"
                )
                continue
            unlock.append(module.completion_quest)

    create_stub = confirm_fn("Create a lore-file stub for this module?", default=True)
    lore_file = f"lore/modules/{module_id}.md" if create_stub else None

    xp = int_prompt_fn("Reward XP (0 for none)", default=0)

    answers = NewModuleAnswers(
        id=module_id,
        title=title,
        description=description,
        entry_location=entry_location,
        completion_quest=completion_quest,
        unlock_when_quests_completed=unlock,
        lore_file=lore_file,
        create_lore_stub=create_stub,
        rewards_xp=xp,
    )

    manifest_path = write_module(world_dir, answers)
    printer(
        f"[green]✓ Added module '{answers.id}' to {manifest_path}[/green]"
        + (
            f"\n[dim]Lore stub written to " f"{world_dir / answers.lore_file}[/dim]"
            if answers.create_lore_stub and answers.lore_file
            else ""
        )
    )
    return manifest_path
