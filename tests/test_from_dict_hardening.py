"""Tests for engine/_serialization.py and the hardened from_dict deserializers.

Scope: corrupted / partial / schema-drifted save dicts should load with safe
defaults instead of raising KeyError / TypeError. Supports the zero-traceback
principle documented in CLAUDE.md.
"""

from enum import Enum

import pytest

from rag_quest.engine._serialization import filter_init_kwargs, safe_enum

# ---------------------------------------------------------------------------
# safe_enum helper
# ---------------------------------------------------------------------------


class _Color(Enum):
    RED = "red"
    BLUE = "blue"
    GREEN = "green"


def test_safe_enum_by_name():
    assert safe_enum(_Color, "RED", _Color.BLUE) is _Color.RED


def test_safe_enum_by_value():
    assert safe_enum(_Color, "blue", _Color.RED) is _Color.BLUE


def test_safe_enum_passes_through_existing_member():
    assert safe_enum(_Color, _Color.GREEN, _Color.RED) is _Color.GREEN


def test_safe_enum_none_returns_default():
    assert safe_enum(_Color, None, _Color.RED) is _Color.RED


def test_safe_enum_unknown_name_returns_default():
    assert safe_enum(_Color, "PURPLE", _Color.RED) is _Color.RED


def test_safe_enum_wrong_type_returns_default():
    assert safe_enum(_Color, 42, _Color.RED) is _Color.RED


# ---------------------------------------------------------------------------
# filter_init_kwargs helper
# ---------------------------------------------------------------------------


class _Thing:
    def __init__(self, name: str, size: int = 5):
        self.name = name
        self.size = size


def test_filter_init_kwargs_drops_unknown_keys():
    data = {"name": "x", "size": 3, "extra": "drop me"}
    filtered = filter_init_kwargs(_Thing, data)
    assert "extra" not in filtered
    assert filtered == {"name": "x", "size": 3}


def test_filter_init_kwargs_preserves_all_known_keys():
    data = {"name": "x", "size": 3}
    assert filter_init_kwargs(_Thing, data) == data


def test_filter_init_kwargs_on_empty_dict():
    assert filter_init_kwargs(_Thing, {}) == {}


# ---------------------------------------------------------------------------
# Character.from_dict
# ---------------------------------------------------------------------------


def test_character_from_dict_missing_race_defaults_to_human():
    from rag_quest.engine.character import Character, CharacterClass, Race

    data = {"name": "Hero", "character_class": "FIGHTER"}
    char = Character.from_dict(data)
    assert char.race is Race.HUMAN
    assert char.character_class is CharacterClass.FIGHTER
    assert char.name == "Hero"


def test_character_from_dict_unknown_race_defaults_to_human():
    from rag_quest.engine.character import Character, Race

    data = {"name": "Hero", "race": "ELDRITCH", "character_class": "FIGHTER"}
    char = Character.from_dict(data)
    assert char.race is Race.HUMAN


def test_character_from_dict_missing_name_uses_hero_default():
    from rag_quest.engine.character import Character

    char = Character.from_dict({"race": "HUMAN", "character_class": "FIGHTER"})
    assert char.name == "Hero"


def test_character_from_dict_ignores_extra_keys_from_newer_builds():
    from rag_quest.engine.character import Character

    data = {
        "name": "Hero",
        "race": "HUMAN",
        "character_class": "FIGHTER",
        "some_future_field": "extra",  # simulate newer save format
    }
    char = Character.from_dict(data)  # must not raise TypeError
    assert char.name == "Hero"


def test_character_roundtrip_still_preserves_identity_fields():
    """Regression guard: hardening mustn't break the happy path.

    Only asserts on the identity/choice fields. HP and damage dice are
    recomputed by `Character.__init__` based on class+level, so a roundtrip
    can legitimately reset them — that behavior predates this commit.
    """
    from rag_quest.engine.character import Character, CharacterClass, Race

    original = Character(
        name="Durin",
        race=Race.DWARF,
        character_class=CharacterClass.CLERIC,
        level=7,
        experience=1500,
        location="Ironhold",
    )
    restored = Character.from_dict(original.to_dict())
    assert restored.name == "Durin"
    assert restored.race is Race.DWARF
    assert restored.character_class is CharacterClass.CLERIC
    assert restored.level == 7
    assert restored.experience == 1500
    assert restored.location == "Ironhold"


# ---------------------------------------------------------------------------
# World.from_dict
# ---------------------------------------------------------------------------


def test_world_from_dict_unknown_time_of_day_defaults_to_morning():
    from rag_quest.engine.world import TimeOfDay, World

    data = {
        "name": "Test",
        "setting": "Fantasy",
        "tone": "Heroic",
        "current_time": "ECLIPSE",  # not a real TimeOfDay
        "weather": "CLEAR",
    }
    w = World.from_dict(data)
    assert w.current_time is TimeOfDay.MORNING


def test_world_from_dict_missing_name_uses_default():
    from rag_quest.engine.world import World

    w = World.from_dict({"setting": "Fantasy", "tone": "Heroic"})
    assert w.name == "Unknown World"


def test_world_from_dict_ignores_extra_keys():
    from rag_quest.engine.world import World

    w = World.from_dict(
        {
            "name": "Test",
            "setting": "Fantasy",
            "tone": "Heroic",
            "current_time": "MORNING",
            "weather": "CLEAR",
            "from_v0_10_future_field": 42,
        }
    )
    assert w.name == "Test"


# ---------------------------------------------------------------------------
# NPC / NPCRelationship / Faction
# ---------------------------------------------------------------------------


def test_npc_from_dict_missing_disposition_defaults_neutral():
    from rag_quest.engine.relationships import NPC, Disposition

    npc = NPC.from_dict({"name": "Mira", "role": "captain"})
    assert npc.disposition is Disposition.NEUTRAL


def test_npc_from_dict_unknown_disposition_defaults_neutral():
    from rag_quest.engine.relationships import NPC, Disposition

    npc = NPC.from_dict(
        {"name": "Mira", "role": "captain", "disposition": "WORSHIPFUL"}
    )
    assert npc.disposition is Disposition.NEUTRAL


def test_npc_from_dict_preserves_known_disposition_by_value():
    from rag_quest.engine.relationships import NPC, Disposition

    npc = NPC.from_dict(
        {
            "name": "Mira",
            "role": "captain",
            "disposition": Disposition.FRIENDLY.value,
        }
    )
    assert npc.disposition is Disposition.FRIENDLY


def test_npc_relationship_from_dict_missing_disposition_defaults_neutral():
    from rag_quest.engine.relationships import Disposition, NPCRelationship

    rel = NPCRelationship.from_dict({"npc_name": "Durin"})
    assert rel.disposition is Disposition.NEUTRAL


def test_faction_from_dict_with_extra_key_doesnt_crash():
    from rag_quest.engine.relationships import Faction

    data = {
        "name": "Guild",
        "description": "Trade",
        "future_field": "drop me",
    }
    faction = Faction.from_dict(data)
    assert faction.name == "Guild"


# ---------------------------------------------------------------------------
# Quest / QuestObjective / QuestReward
# ---------------------------------------------------------------------------


def test_quest_from_dict_unknown_status_defaults_active():
    from rag_quest.engine.quests import Quest, QuestStatus

    data = {"title": "T", "description": "d", "status": "PHANTOM"}
    q = Quest.from_dict(data)
    assert q.status is QuestStatus.ACTIVE


def test_quest_from_dict_missing_title_uses_default():
    from rag_quest.engine.quests import Quest

    q = Quest.from_dict({"description": "d"})
    assert q.title == "Untitled Quest"


def test_quest_objective_from_dict_missing_type_uses_default():
    from rag_quest.engine.quests import ObjectiveType, QuestObjective

    obj = QuestObjective.from_dict({"description": "Find the thing"})
    # Whatever the first ObjectiveType member is, it's the fallback.
    assert isinstance(obj.objective_type, ObjectiveType)


def test_quest_reward_from_dict_ignores_unknown_keys():
    from rag_quest.engine.quests import QuestReward

    reward = QuestReward.from_dict({"xp": 100, "gold": 50, "future_field": [1, 2, 3]})
    assert reward.xp == 100
    assert reward.gold == 50
