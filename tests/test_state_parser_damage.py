"""Regression tests: damage extraction must not fire on narrator HP readouts.

Turn-1 death bug (rag-quest-0gp): a fresh 22-HP character died on the first
turn because the narrator's own status line ("**22/22 HP**") was parsed as
22 points of damage. These tests pin the fix and guard the positive cases.
"""

from rag_quest.engine.state_parser import StateParser


def test_hp_status_readout_does_not_apply_damage():
    p = StateParser()
    change = p.parse_narrator_response(
        "Your current state is stable: **22/22 HP**. What do you do next?",
        "I wake in the forest",
    )
    assert change.damage_taken == 0


def test_bare_hit_points_mention_does_not_apply_damage():
    p = StateParser()
    change = p.parse_narrator_response(
        "You feel your 22 hit points coursing through you.",
        "check self",
    )
    assert change.damage_taken == 0


def test_slash_ratio_hp_does_not_apply_damage():
    p = StateParser()
    change = p.parse_narrator_response(
        "HP: 18/22 - you are still standing.",
        "look",
    )
    assert change.damage_taken == 0


def test_lose_coins_does_not_apply_damage():
    p = StateParser()
    change = p.parse_narrator_response(
        "You lost 5 coins to the pickpocket.",
        "walk through market",
    )
    assert change.damage_taken == 0


def test_take_damage_phrase_still_extracts():
    p = StateParser()
    change = p.parse_narrator_response(
        "The goblin strikes and you take 5 damage.",
        "attack goblin",
    )
    assert change.damage_taken == 5


def test_suffer_damage_phrase_still_extracts():
    p = StateParser()
    change = p.parse_narrator_response(
        "You suffer 7 damage from the fall.",
        "jump",
    )
    assert change.damage_taken == 7


def test_lose_hp_phrase_still_extracts():
    p = StateParser()
    change = p.parse_narrator_response(
        "You lose 4 hp to the freezing wind.",
        "push on",
    )
    assert change.damage_taken == 4


def test_deal_damage_to_enemy_does_not_hurt_player():
    """`deal/inflict N damage` describes damage *dealt*, not taken.
    Historically this was ungated-accidentally-safe via the combat-keyword
    gate; after the fix it must be explicitly non-extracted."""
    p = StateParser()
    change = p.parse_narrator_response(
        "You deal 8 damage to the orc.",
        "attack orc",
    )
    assert change.damage_taken == 0
