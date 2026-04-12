"""Tests for v0.7 validate-module sanity checker."""

import textwrap
from pathlib import Path

from rag_quest.worlds.validate import ValidationResult, validate_manifest


def _write_manifest(tmp_path: Path, body: str) -> Path:
    (tmp_path / "modules.yaml").write_text(textwrap.dedent(body).lstrip())
    return tmp_path


# ---------------------------------------------------------------------------
# Happy path + missing-manifest errors
# ---------------------------------------------------------------------------


def test_validate_missing_manifest_is_error(tmp_path):
    result = validate_manifest(tmp_path)
    assert not result.ok
    assert any("No modules.yaml" in e for e in result.errors)


def test_validate_clean_manifest(tmp_path):
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: goblin-cave
            title: Goblin Cave
            description: d
            entry_location: Stonebridge
          - id: tower
            title: Tower of Echoes
            description: d
            entry_location: Silver Hollow
            unlock_when_quests_completed: [Slay the Chief]
        """,
    )
    # goblin-cave does NOT declare `Slay the Chief` as a completion_quest,
    # so there will be a *warning* but no error.
    result = validate_manifest(tmp_path)
    assert result.ok  # warnings don't fail
    assert result.registry is not None
    assert len(result.registry) == 2
    assert any("Slay the Chief" in w for w in result.warnings)
    assert result.errors == []


def test_validate_surfaces_schema_errors_from_load(tmp_path):
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: bad
            title: Bad
            description: d
        """,  # missing entry_location
    )
    result = validate_manifest(tmp_path)
    assert not result.ok
    assert any("entry_location" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Lore file existence checks
# ---------------------------------------------------------------------------


def test_validate_missing_lore_file_is_error(tmp_path):
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: m1
            title: M1
            description: d
            entry_location: X
            lore_files:
              - lore/missing.md
        """,
    )
    result = validate_manifest(tmp_path)
    assert not result.ok
    assert any("lore file does not exist" in e for e in result.errors)


def test_validate_passes_with_existing_lore(tmp_path):
    lore = tmp_path / "lore"
    lore.mkdir()
    (lore / "m1.md").write_text("# M1")
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: m1
            title: M1
            description: d
            entry_location: X
            lore_files:
              - lore/m1.md
        """,
    )
    result = validate_manifest(tmp_path)
    assert result.ok
    assert result.errors == []


# ---------------------------------------------------------------------------
# Unlock-reference warnings
# ---------------------------------------------------------------------------


def test_validate_warns_on_unknown_unlock_reference(tmp_path):
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: m
            title: M
            description: d
            entry_location: X
            unlock_when_quests_completed: [mystery-quest]
        """,
    )
    result = validate_manifest(tmp_path)
    assert result.ok  # warning only
    assert any("mystery-quest" in w for w in result.warnings)


def test_validate_no_warning_when_unlock_matches_another_modules_completion(
    tmp_path,
):
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: first
            title: First
            description: d
            entry_location: X
            completion_quest: Defeat the Chief
          - id: second
            title: Second
            description: d
            entry_location: Y
            unlock_when_quests_completed: [defeat the chief]
        """,
    )
    result = validate_manifest(tmp_path)
    assert result.ok
    assert result.warnings == []  # case-insensitive match


# ---------------------------------------------------------------------------
# Prerequisite cycle detection
# ---------------------------------------------------------------------------


def test_validate_detects_two_module_cycle(tmp_path):
    """A → B → A cycle via completion_quest ↔ unlock_when_quests_completed."""
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: a
            title: A
            description: d
            entry_location: X
            completion_quest: Q1
            unlock_when_quests_completed: [Q2]
          - id: b
            title: B
            description: d
            entry_location: Y
            completion_quest: Q2
            unlock_when_quests_completed: [Q1]
        """,
    )
    result = validate_manifest(tmp_path)
    assert not result.ok
    assert any("cycle detected" in e for e in result.errors)


def test_validate_detects_three_module_cycle(tmp_path):
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: a
            title: A
            description: d
            entry_location: X
            completion_quest: QA
            unlock_when_quests_completed: [QC]
          - id: b
            title: B
            description: d
            entry_location: Y
            completion_quest: QB
            unlock_when_quests_completed: [QA]
          - id: c
            title: C
            description: d
            entry_location: Z
            completion_quest: QC
            unlock_when_quests_completed: [QB]
        """,
    )
    result = validate_manifest(tmp_path)
    assert not result.ok
    assert any("cycle detected" in e for e in result.errors)


def test_validate_linear_chain_is_not_a_cycle(tmp_path):
    _write_manifest(
        tmp_path,
        """
        modules:
          - id: a
            title: A
            description: d
            entry_location: X
            completion_quest: QA
          - id: b
            title: B
            description: d
            entry_location: Y
            completion_quest: QB
            unlock_when_quests_completed: [QA]
          - id: c
            title: C
            description: d
            entry_location: Z
            unlock_when_quests_completed: [QB]
        """,
    )
    result = validate_manifest(tmp_path)
    assert result.ok
    assert not any("cycle" in e for e in result.errors)


# ---------------------------------------------------------------------------
# ValidationResult shape
# ---------------------------------------------------------------------------


def test_validation_result_ok_property():
    assert ValidationResult().ok is True
    assert ValidationResult(errors=["x"]).ok is False
    assert ValidationResult(warnings=["x"]).ok is True  # warnings don't fail
