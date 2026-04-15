"""Regression test for rag-quest-aem: narrator now actually queries RAG lore.

Before the fix, narrator._call_llm called `self.world_rag.query(player_input)`
— a method that doesn't exist on WorldRAG. The resulting AttributeError was
swallowed by a bare `except Exception: pass`, so rag_context stayed empty on
every turn. The fix changes the call to `query_world()` (the real method).

These tests verify the narrator's LLM system prompt actually includes the
RAG lore string, using a fake WorldRAG double.
"""

from rag_quest.engine.character import Character, CharacterClass, Race
from rag_quest.engine.narrator import Narrator
from rag_quest.engine.world import World


class FakeWorldRAG:
    """Minimal stand-in that records calls and returns a canned lore string."""

    def __init__(self, lore: str = "The Goblin Cave is guarded by Chief Grash."):
        self.lore = lore
        self.calls: list[str] = []

    def query_world(self, question: str, context: str = "", param=None) -> str:
        self.calls.append(question)
        return self.lore


class RecordingLLM:
    """LLM double that just records the messages it was called with."""

    def __init__(self):
        self.last_messages = None

    def complete(self, messages, **kwargs):
        self.last_messages = messages
        return "You push the door open and step inside."

    def close(self):
        pass


def _make_narrator(rag_lore: str = "The Goblin Cave is guarded by Chief Grash."):
    character = Character(
        name="Hero",
        race=Race.HUMAN,
        character_class=CharacterClass.FIGHTER,
        location="Goblin Cave",
    )
    world = World(name="Test", setting="Fantasy", tone="Heroic")
    return Narrator(
        llm=RecordingLLM(),
        world_rag=FakeWorldRAG(rag_lore),
        character=character,
        world=world,
    )


def test_narrator_queries_world_rag_with_player_input():
    """The narrator should hit WorldRAG.query_world(player_input), not .query()."""
    narrator = _make_narrator()
    narrator.process_action("open the door")
    assert narrator.world_rag.calls == ["open the door"]


def test_narrator_injects_rag_lore_into_llm_system_prompt():
    narrator = _make_narrator("The cave echoes with goblin laughter.")
    narrator.process_action("listen carefully")
    messages = narrator.llm.last_messages
    assert messages is not None
    system_content = messages[0]["content"]
    assert "RELEVANT WORLD LORE" in system_content
    assert "goblin laughter" in system_content


def test_narrator_swallows_rag_failures_without_crashing():
    """If WorldRAG.query_world raises, narrator should fall back silently
    (same contract as before — we just shouldn't silently no-op when it works)."""

    class BrokenRAG:
        def query_world(self, *a, **k):
            raise RuntimeError("boom")

    narrator = _make_narrator()
    narrator.world_rag = BrokenRAG()
    # Should not raise; returns something (LLM fallback).
    response = narrator.process_action("look around")
    assert isinstance(response, str)
    messages = narrator.llm.last_messages
    # LLM still gets called; just without the lore section.
    assert messages is not None
    assert "RELEVANT WORLD LORE" not in messages[0]["content"]


def test_narrator_caps_lore_string_length():
    """Very long lore strings should be capped so the LLM context doesn't blow up."""
    huge = "x" * 5000
    narrator = _make_narrator(huge)
    narrator.process_action("anything")
    messages = narrator.llm.last_messages
    system_content = messages[0]["content"]
    # Cap is ~800 chars; with the header and formatting we expect well under 1200.
    lore_block_start = system_content.index("=== RELEVANT WORLD LORE ===")
    lore_block_end = system_content.find("\n\n=== CURRENT SITUATION ===")
    lore_block = system_content[lore_block_start:lore_block_end]
    assert len(lore_block) < 1000


def test_call_llm_delegates_to_build_llm_messages():
    """rag-quest-7uc: _call_llm must route through _build_llm_messages, not
    duplicate the prompt-building logic. Patching the shared builder must
    intercept the messages _call_llm sends to the LLM."""
    narrator = _make_narrator()
    sentinel = [
        {"role": "system", "content": "SENTINEL_SYSTEM"},
        {"role": "user", "content": "SENTINEL_USER"},
    ]
    narrator._build_llm_messages = lambda player_input: sentinel  # type: ignore[method-assign]

    narrator.process_action("anything")

    assert narrator.llm.last_messages == sentinel
