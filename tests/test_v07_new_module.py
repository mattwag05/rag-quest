"""Tests for v0.7 rag-quest new-module interactive CLI."""

import textwrap
from pathlib import Path

import pytest

from rag_quest.worlds.modules import (
    MANIFEST_FILENAME,
    ModuleManifestError,
    load_modules,
)
from rag_quest.worlds.new_module import (
    NewModuleAnswers,
    render_stanza,
    run_interactive,
    slugify,
    write_module,
)

# ---------------------------------------------------------------------------
# Pure helpers: slugify, render_stanza
# ---------------------------------------------------------------------------


def test_slugify_basic():
    assert slugify("Goblin Cave") == "goblin-cave"
    assert slugify("The Haunted Mill!") == "the-haunted-mill"
    assert slugify("   ") == "module"


def test_render_stanza_minimal():
    answers = NewModuleAnswers(
        id="cave",
        title="The Cave",
        description="Dark stuff.",
        entry_location="Stonebridge",
    )
    text = render_stanza(answers)
    assert "- id: cave" in text
    assert "title: The Cave" in text
    assert "description: Dark stuff." in text
    assert "entry_location: Stonebridge" in text
    # minimal stanza has no optional fields
    assert "unlock_when_quests_completed" not in text
    assert "completion_quest" not in text
    assert "lore_files" not in text
    assert "rewards" not in text


def test_render_stanza_full():
    answers = NewModuleAnswers(
        id="tower",
        title="Tower of Echoes",
        description="Old ruin.",
        entry_location="Silver Hollow",
        completion_quest="Silence the Echoes",
        unlock_when_quests_completed=["Slay the Chief", "Cross the River"],
        lore_file="lore/modules/tower.md",
        rewards_xp=300,
    )
    text = render_stanza(answers)
    assert "unlock_when_quests_completed:" in text
    assert "- Slay the Chief" in text
    assert "- Cross the River" in text
    assert "completion_quest: Silence the Echoes" in text
    assert "lore_files:" in text
    assert "lore/modules/tower.md" in text
    assert "rewards:" in text
    assert "xp: 300" in text


def test_render_stanza_quotes_strings_with_colons():
    answers = NewModuleAnswers(
        id="m",
        title="The Hero: Rise",
        description="Epic.",
        entry_location="Camp",
    )
    text = render_stanza(answers)
    # colon-bearing titles must be quoted so PyYAML doesn't mis-parse
    assert '"The Hero: Rise"' in text


# ---------------------------------------------------------------------------
# write_module — creates manifest, appends, validates
# ---------------------------------------------------------------------------


def test_write_module_creates_manifest_if_missing(tmp_path):
    answers = NewModuleAnswers(
        id="cave",
        title="The Cave",
        description="Dark stuff.",
        entry_location="Stonebridge",
    )
    path = write_module(tmp_path, answers)
    assert path == tmp_path / MANIFEST_FILENAME
    registry = load_modules(tmp_path)
    assert len(registry) == 1
    assert registry.get("cave") is not None


def test_write_module_appends_to_existing_manifest(tmp_path):
    (tmp_path / MANIFEST_FILENAME).write_text(textwrap.dedent("""
            modules:
              - id: first
                title: First
                description: d
                entry_location: X
            """).lstrip())
    write_module(
        tmp_path,
        NewModuleAnswers(
            id="second",
            title="Second",
            description="d",
            entry_location="Y",
        ),
    )
    registry = load_modules(tmp_path)
    assert len(registry) == 2
    assert {m.id for m in registry.all()} == {"first", "second"}


def test_write_module_rejects_duplicate_id(tmp_path):
    write_module(
        tmp_path,
        NewModuleAnswers(id="dup", title="A", description="d", entry_location="X"),
    )
    with pytest.raises(ModuleManifestError, match="already exists"):
        write_module(
            tmp_path,
            NewModuleAnswers(id="dup", title="B", description="d", entry_location="Y"),
        )


def test_write_module_rejects_invalid_id_slug(tmp_path):
    with pytest.raises(ModuleManifestError, match="Invalid module id"):
        write_module(
            tmp_path,
            NewModuleAnswers(
                id="Not A Slug!",
                title="A",
                description="d",
                entry_location="X",
            ),
        )


def test_write_module_creates_lore_stub_when_requested(tmp_path):
    answers = NewModuleAnswers(
        id="cave",
        title="The Cave",
        description="Dark.",
        entry_location="Stonebridge",
        completion_quest="Clear the Cave",
        lore_file="lore/modules/cave.md",
        create_lore_stub=True,
    )
    write_module(tmp_path, answers)
    stub = tmp_path / "lore" / "modules" / "cave.md"
    assert stub.exists()
    body = stub.read_text()
    assert "The Cave" in body  # title rendered into stub
    assert "Clear the Cave" in body  # completion quest mentioned


def test_write_module_does_not_overwrite_existing_lore_file(tmp_path):
    lore_path = tmp_path / "lore" / "modules" / "cave.md"
    lore_path.parent.mkdir(parents=True)
    lore_path.write_text("# HAND WRITTEN - DO NOT OVERWRITE")

    write_module(
        tmp_path,
        NewModuleAnswers(
            id="cave",
            title="The Cave",
            description="d",
            entry_location="X",
            lore_file="lore/modules/cave.md",
            create_lore_stub=True,
        ),
    )
    assert "HAND WRITTEN" in lore_path.read_text()


def test_write_module_rejects_lore_path_escaping_world_dir(tmp_path):
    with pytest.raises(ModuleManifestError, match="escapes"):
        write_module(
            tmp_path,
            NewModuleAnswers(
                id="m",
                title="M",
                description="d",
                entry_location="X",
                lore_file="../outside/secret.md",
                create_lore_stub=True,
            ),
        )


def test_write_module_rolls_back_on_validator_failure(tmp_path):
    """If the new stanza would reference a nonexistent lore file, validator
    catches it and write_module rolls back the append so the manifest isn't
    left in a broken state."""
    answers = NewModuleAnswers(
        id="cave",
        title="The Cave",
        description="d",
        entry_location="X",
        lore_file="lore/does-not-exist.md",
        create_lore_stub=False,  # so the file actually doesn't exist
    )
    with pytest.raises(ModuleManifestError, match="invalid state"):
        write_module(tmp_path, answers)

    # Manifest was created with just the "modules:" header but the rolled-back
    # stanza is gone. Loading should yield zero modules.
    if (tmp_path / MANIFEST_FILENAME).exists():
        registry = load_modules(tmp_path)
        assert len(registry) == 0


def test_written_manifest_survives_roundtrip_through_load_modules(tmp_path):
    """Every field the tool writes must parse back via load_modules."""
    answers = NewModuleAnswers(
        id="tower",
        title="Tower of Echoes",
        description="Old ruin.",
        entry_location="Silver Hollow",
        completion_quest="Silence the Echoes",
        unlock_when_quests_completed=["Slay the Chief"],
        lore_file="lore/modules/tower.md",
        create_lore_stub=True,
        rewards_xp=300,
    )
    # Also create the first module so the prereq reference isn't an orphan.
    write_module(
        tmp_path,
        NewModuleAnswers(
            id="first",
            title="First",
            description="d",
            entry_location="X",
            completion_quest="Slay the Chief",
        ),
    )
    write_module(tmp_path, answers)

    registry = load_modules(tmp_path)
    tower = registry.get("tower")
    assert tower is not None
    assert tower.title == "Tower of Echoes"
    assert tower.completion_quest == "Silence the Echoes"
    assert tower.unlock_when_quests_completed == ["Slay the Chief"]
    assert tower.lore_files == ["lore/modules/tower.md"]
    assert tower.rewards == {"xp": 300}


# ---------------------------------------------------------------------------
# run_interactive — inject fakes for prompt/confirm/int_prompt/printer
# ---------------------------------------------------------------------------


class _Scripted:
    """Tiny helper that pulls answers from a pre-recorded list."""

    def __init__(self, answers: list):
        self._answers = list(answers)

    def pop(self):
        return self._answers.pop(0)


def test_run_interactive_happy_path(tmp_path):
    scripted = _Scripted(
        [
            "Goblin Cave",  # title
            "goblin-cave",  # module id
            "Clear the goblins.",  # description
            "Stonebridge",  # entry location
            "Slay the Chief",  # completion quest (has_completion=True)
        ]
    )
    # No existing modules → the add_prereqs confirm is skipped.
    # has_completion=True, create_stub=True
    confirms = _Scripted([True, True])
    ints = _Scripted([0])
    printed: list[str] = []

    def prompt_fn(question, default=None, **_):
        return scripted.pop()

    def confirm_fn(question, default=False, **_):
        return confirms.pop()

    def int_prompt_fn(question, default=0, **_):
        return ints.pop()

    run_interactive(
        tmp_path,
        prompt_fn=prompt_fn,
        confirm_fn=confirm_fn,
        int_prompt_fn=int_prompt_fn,
        printer=printed.append,
    )
    registry = load_modules(tmp_path)
    module = registry.get("goblin-cave")
    assert module is not None
    assert module.completion_quest == "Slay the Chief"
    assert module.lore_files == ["lore/modules/goblin-cave.md"]
    assert (tmp_path / "lore" / "modules" / "goblin-cave.md").exists()


def test_run_interactive_skips_completion_when_declined(tmp_path):
    scripted = _Scripted(
        [
            "Wander Route",
            "wander-route",
            "Open-ended travel.",
            "Crossroads",
        ]
    )
    # has_completion=False, create_stub=False
    confirms = _Scripted([False, False])
    ints = _Scripted([0])
    printed: list[str] = []

    run_interactive(
        tmp_path,
        prompt_fn=lambda *a, **k: scripted.pop(),
        confirm_fn=lambda *a, **k: confirms.pop(),
        int_prompt_fn=lambda *a, **k: ints.pop(),
        printer=printed.append,
    )
    registry = load_modules(tmp_path)
    module = registry.get("wander-route")
    assert module is not None
    assert module.completion_quest is None
    assert module.lore_files == []
    assert not (tmp_path / "lore" / "modules" / "wander-route.md").exists()


def test_run_interactive_wires_prereq_modules_to_their_completion_quests(tmp_path):
    # Seed an existing module with a completion_quest so the interactive
    # flow has a prereq candidate to find.
    write_module(
        tmp_path,
        NewModuleAnswers(
            id="first",
            title="First",
            description="d",
            entry_location="X",
            completion_quest="Slay the Chief",
        ),
    )

    scripted = _Scripted(
        [
            "Second Step",  # title
            "second",  # id
            "Follow-up.",  # description
            "Silver Hollow",  # entry location
            "Silence the Echoes",  # completion quest
            "first",  # prereq ids (comma-separated)
        ]
    )
    # has_completion=True, add_prereqs=True, create_stub=False
    confirms = _Scripted([True, True, False])
    ints = _Scripted([100])
    printed: list[str] = []

    run_interactive(
        tmp_path,
        prompt_fn=lambda *a, **k: scripted.pop(),
        confirm_fn=lambda *a, **k: confirms.pop(),
        int_prompt_fn=lambda *a, **k: ints.pop(),
        printer=printed.append,
    )
    registry = load_modules(tmp_path)
    second = registry.get("second")
    assert second is not None
    # prereq module → unlock_when_quests_completed = [that module's completion_quest]
    assert second.unlock_when_quests_completed == ["Slay the Chief"]
    assert second.rewards == {"xp": 100}
