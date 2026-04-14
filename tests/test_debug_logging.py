"""Tests for rag_quest._debug.log_swallowed_exc and its wiring into silent catches."""

import os

import pytest

from rag_quest._debug import debug_enabled, log_swallowed_exc

# ---------------------------------------------------------------------------
# Core helper
# ---------------------------------------------------------------------------


def test_debug_disabled_by_default(monkeypatch):
    monkeypatch.delenv("RAG_QUEST_DEBUG", raising=False)
    assert debug_enabled() is False


def test_debug_enabled_when_env_set(monkeypatch):
    monkeypatch.setenv("RAG_QUEST_DEBUG", "1")
    assert debug_enabled() is True


def test_empty_env_value_is_disabled(monkeypatch):
    monkeypatch.setenv("RAG_QUEST_DEBUG", "")
    assert debug_enabled() is False


def test_log_swallowed_exc_is_silent_when_disabled(monkeypatch, capsys):
    monkeypatch.delenv("RAG_QUEST_DEBUG", raising=False)
    try:
        raise ValueError("should be silent")
    except ValueError:
        log_swallowed_exc("test.silent")
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""


def test_log_swallowed_exc_prints_traceback_when_enabled(monkeypatch, capsys):
    monkeypatch.setenv("RAG_QUEST_DEBUG", "1")
    try:
        raise ValueError("visible in debug mode")
    except ValueError:
        log_swallowed_exc("test.visible")
    captured = capsys.readouterr()
    # stderr contains the context tag + the exception class + message
    assert "test.visible" in captured.err
    assert "ValueError" in captured.err
    assert "visible in debug mode" in captured.err


# ---------------------------------------------------------------------------
# Integration: narrator's swallowed RAG exception surfaces in debug mode
# ---------------------------------------------------------------------------


class _BrokenRAG:
    def query_world(self, *a, **k):
        raise RuntimeError("rag is offline")


class _RecordingLLM:
    def __init__(self):
        self.last_messages = None

    def complete(self, messages, **kwargs):
        self.last_messages = messages
        return "Nothing much happens."

    def close(self):
        pass


def _narrator_with_broken_rag():
    from rag_quest.engine.character import Character, CharacterClass, Race
    from rag_quest.engine.narrator import Narrator
    from rag_quest.engine.world import World

    return Narrator(
        llm=_RecordingLLM(),
        world_rag=_BrokenRAG(),
        character=Character(
            name="Hero",
            race=Race.HUMAN,
            character_class=CharacterClass.FIGHTER,
            location="Cave",
        ),
        world=World(name="Test", setting="Fantasy", tone="Heroic"),
    )


def test_narrator_rag_failure_is_silent_without_debug_flag(monkeypatch, capsys):
    monkeypatch.delenv("RAG_QUEST_DEBUG", raising=False)
    narrator = _narrator_with_broken_rag()
    narrator.process_action("look around")
    captured = capsys.readouterr()
    assert "rag is offline" not in captured.err
    assert "rag is offline" not in captured.out


def test_narrator_rag_failure_surfaces_under_debug_flag(monkeypatch, capsys):
    monkeypatch.setenv("RAG_QUEST_DEBUG", "1")
    narrator = _narrator_with_broken_rag()
    narrator.process_action("look around")
    captured = capsys.readouterr()
    assert "narrator._gather_external_context.world_rag" in captured.err
    assert "RuntimeError" in captured.err
    assert "rag is offline" in captured.err
