"""Regression tests: healing extraction must not fire on enemy self-healing.

Mirror of test_state_parser_damage.py discipline — subject-guard patterns
prevent "the troll regenerates and heals 15 hp" from crediting the player
with 15 HP.  Each pattern variant gets a positive *and* negative case so
regressions are caught in both directions.
"""

from rag_quest.engine.state_parser import StateParser


# ---------------------------------------------------------------------------
# Negative cases — enemy or context healing must NOT affect the player
# ---------------------------------------------------------------------------


def test_enemy_heals_hp_does_not_credit_player():
    p = StateParser()
    change = p.parse_narrator_response(
        "The troll regenerates and heals 15 hp.",
        "watch",
    )
    assert change.hp_healed == 0


def test_enemy_restores_health_does_not_credit_player():
    p = StateParser()
    change = p.parse_narrator_response(
        "The elder dragon restores 20 health through ancient magic.",
        "observe",
    )
    assert change.hp_healed == 0


def test_enemy_regains_health_does_not_credit_player():
    p = StateParser()
    change = p.parse_narrator_response(
        "The goblin shaman regains 8 health from the ritual.",
        "watch",
    )
    assert change.hp_healed == 0


def test_enemy_recovers_hp_does_not_credit_player():
    p = StateParser()
    change = p.parse_narrator_response(
        "The wounded orc recovers 5 hp between rounds.",
        "wait",
    )
    assert change.hp_healed == 0


# ---------------------------------------------------------------------------
# Positive cases — player healing must still be extracted correctly
# ---------------------------------------------------------------------------


def test_you_heal_hp_extracts():
    p = StateParser()
    change = p.parse_narrator_response(
        "You heal 10 hp from the spring water.",
        "drink",
    )
    assert change.hp_healed == 10


def test_you_restore_hp_extracts():
    p = StateParser()
    change = p.parse_narrator_response(
        "You restore 6 hp with the herbal remedy.",
        "use herb",
    )
    assert change.hp_healed == 6


def test_you_regain_health_extracts():
    p = StateParser()
    change = p.parse_narrator_response(
        "You regain 12 health after the short rest.",
        "rest",
    )
    assert change.hp_healed == 12


def test_you_recover_hp_extracts():
    p = StateParser()
    change = p.parse_narrator_response(
        "You recover 7 hp from the cleric's prayer.",
        "accept healing",
    )
    assert change.hp_healed == 7


def test_heals_you_for_extracts():
    p = StateParser()
    change = p.parse_narrator_response(
        "The potion heals you for 15 hp.",
        "drink potion",
    )
    assert change.hp_healed == 15


def test_restores_you_extracts():
    p = StateParser()
    change = p.parse_narrator_response(
        "The cleric's spell restores you 8 hp.",
        "ask for healing",
    )
    assert change.hp_healed == 8


def test_potion_heals_extracts():
    p = StateParser()
    change = p.parse_narrator_response(
        "The potion heals 20 hit points.",
        "drink potion",
    )
    assert change.hp_healed == 20


def test_passive_hp_restored_extracts():
    p = StateParser()
    change = p.parse_narrator_response(
        "10 hp is restored as the magic washes over you.",
        "step into the light",
    )
    assert change.hp_healed == 10


def test_passive_health_healed_extracts():
    p = StateParser()
    change = p.parse_narrator_response(
        "5 health is healed by the rune inscription.",
        "touch the rune",
    )
    assert change.hp_healed == 5
