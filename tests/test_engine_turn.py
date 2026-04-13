"""Unit tests for the shared turn-loop helper (``rag_quest/engine/turn.py``).

These cover the pure state-mutation layer that both the CLI loop and the
web ``/turn`` endpoints now delegate to, so we can assert parity without
standing up a full game session.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from rag_quest.engine.state_parser import StateChange
from rag_quest.engine.turn import (
    PostTurnEffects,
    PreTurnEffects,
    TurnResult,
    advance_one_turn,
    collect_post_turn_effects,
    collect_pre_turn_effects,
)


def _make_game_state(
    *,
    turn_number: int = 0,
    narrator_response: str = "You look around.",
    state_change: StateChange | None = None,
    new_event=None,
    expired_events: list[str] | None = None,
    departed_party_members: list[str] | None = None,
    module_transitions: list | None = None,
    achievements_unlocked: list | None = None,
    character_location: str = "Town Square",
    achievements_attr: bool = True,
) -> MagicMock:
    """Build a MagicMock GameState wired with every subsystem the helper
    touches. Each subsystem's return value is configurable so tests can
    isolate a single side effect."""
    gs = MagicMock(name="game_state")
    gs.turn_number = turn_number

    # narrator
    gs.narrator = MagicMock(name="narrator")
    gs.narrator.process_action.return_value = narrator_response
    gs.narrator.last_change = state_change

    # character.location (used by timeline.record_from_state_change)
    gs.character = SimpleNamespace(location=character_location)

    # events
    gs.events = MagicMock(name="events")
    gs.events.check_for_events.return_value = new_event
    gs.events.expire_events.return_value = expired_events or []

    # party
    gs.party = MagicMock(name="party")
    gs.party.check_loyalty_departures.return_value = departed_party_members or []

    # timeline
    gs.timeline = MagicMock(name="timeline")
    gs.timeline.record_from_state_change.return_value = []

    # world.module_registry
    gs.world = MagicMock(name="world")
    gs.world.module_registry.reevaluate.return_value = module_transitions or []

    # achievements (optional on GameState)
    if achievements_attr:
        gs.achievements = MagicMock(name="achievements")
        gs.achievements.check_achievements.return_value = achievements_unlocked or []
    else:
        gs.achievements = None

    # to_dict (used by achievements.check_achievements)
    gs.to_dict.return_value = {"turn_number": turn_number + 1}

    return gs


# ----- collect_pre_turn_effects --------------------------------------------


def test_pre_turn_increments_turn_before_event_check():
    """events.check_for_events must see the post-increment turn number —
    this matches the CLI loop ordering (game.py: turn_number += 1 then
    check_for_events). If we ever flipped the order, event pacing would
    drift by one."""
    gs = _make_game_state(turn_number=7)

    collect_pre_turn_effects(gs)

    assert gs.turn_number == 8
    gs.events.check_for_events.assert_called_once()
    called_turn = gs.events.check_for_events.call_args[0][0]
    assert called_turn == 8


def test_pre_turn_returns_new_event_expired_and_departures():
    fake_event = SimpleNamespace(name="Goblin Raid", description="Bad day")
    gs = _make_game_state(
        new_event=fake_event,
        expired_events=["Festival of Light"],
        departed_party_members=["Gus"],
    )

    pre = collect_pre_turn_effects(gs)

    assert isinstance(pre, PreTurnEffects)
    assert pre.new_event is fake_event
    assert pre.expired_events == ["Festival of Light"]
    assert pre.departed_party_members == ["Gus"]


def test_pre_turn_swallows_subsystem_exceptions():
    """Every subsystem is additive — a failure in one must not kill the
    turn. The CLI loop swallows each of these today; the helper must
    preserve that contract so the web layer gets identical resilience."""
    gs = _make_game_state()
    gs.events.check_for_events.side_effect = RuntimeError("boom")
    gs.events.expire_events.side_effect = RuntimeError("boom")
    gs.party.check_loyalty_departures.side_effect = RuntimeError("boom")

    pre = collect_pre_turn_effects(gs)

    assert pre.new_event is None
    assert pre.expired_events == []
    assert pre.departed_party_members == []
    # turn_number still advances even if subsystems explode
    assert gs.turn_number == 1


# ----- collect_post_turn_effects -------------------------------------------


def test_post_turn_records_timeline_from_last_change():
    change = StateChange(location="Deep Woods", items_gained=["Map"])
    gs = _make_game_state(turn_number=4, state_change=change)

    collect_post_turn_effects(gs, "go forest")

    gs.timeline.record_from_state_change.assert_called_once()
    kwargs = gs.timeline.record_from_state_change.call_args.kwargs
    assert kwargs["turn"] == 4
    assert kwargs["change"] is change
    assert kwargs["player_input"] == "go forest"
    assert kwargs["location"] == "Town Square"


def test_post_turn_skips_timeline_when_no_last_change():
    gs = _make_game_state(state_change=None)

    post = collect_post_turn_effects(gs, "wait")

    assert post.state_change is None
    gs.timeline.record_from_state_change.assert_not_called()


def test_post_turn_reevaluates_modules_and_returns_transitions():
    transitioned = [SimpleNamespace(id="m1", title="The Lost Tomb")]
    gs = _make_game_state(module_transitions=transitioned)

    post = collect_post_turn_effects(gs, "explore")

    gs.world.module_registry.reevaluate.assert_called_once_with(gs.quest_log)
    assert post.module_transitions == transitioned


def test_post_turn_checks_achievements_with_serialized_state():
    unlocked = [SimpleNamespace(id="explorer", name="Explorer", icon="🗺️")]
    gs = _make_game_state(achievements_unlocked=unlocked)

    post = collect_post_turn_effects(gs, "travel north")

    gs.achievements.check_achievements.assert_called_once_with(gs.to_dict())
    assert post.achievements_unlocked == unlocked


def test_post_turn_handles_none_achievements_manager():
    """Old saves may load without an AchievementManager attached. The
    helper must not KeyError/AttributeError in that case."""
    gs = _make_game_state(achievements_attr=False)

    post = collect_post_turn_effects(gs, "look")

    assert isinstance(post, PostTurnEffects)
    assert post.achievements_unlocked == []


def test_post_turn_swallows_subsystem_exceptions():
    change = StateChange(location="Cave")
    gs = _make_game_state(state_change=change)
    gs.timeline.record_from_state_change.side_effect = RuntimeError("boom")
    gs.world.module_registry.reevaluate.side_effect = RuntimeError("boom")
    gs.achievements.check_achievements.side_effect = RuntimeError("boom")

    post = collect_post_turn_effects(gs, "do thing")

    assert post.state_change is change
    assert post.module_transitions == []
    assert post.achievements_unlocked == []


def test_post_turn_caches_state_dict_and_serializes_once(monkeypatch):
    """rag-quest-dqr: ``collect_post_turn_effects`` must serialize the
    game state exactly once per turn. Previously achievements.check and
    the web done payload each called ``game_state.to_dict()``, doubling
    the serialization cost on long-running saves."""
    gs = _make_game_state(
        achievements_unlocked=[
            SimpleNamespace(id="explorer", name="Explorer", icon="🗺️")
        ]
    )
    cached_dict = {"turn_number": 1, "achievements": {"achievements": {}}}
    gs.to_dict.return_value = cached_dict
    # Simulate the achievements manager mutating state during the check
    # so the refresh path has something meaningful to write.
    fresh_achievements = {"achievements": {"explorer": {"unlocked": True}}}
    gs.achievements.to_dict.return_value = fresh_achievements

    post = collect_post_turn_effects(gs, "travel north")

    # Exactly one serialization of the full game state per turn.
    assert gs.to_dict.call_count == 1
    # The cached dict is exposed on PostTurnEffects for web callers.
    assert post.state_dict is cached_dict
    # check_achievements receives the same cached dict (not a copy).
    call_arg = gs.achievements.check_achievements.call_args[0][0]
    assert call_arg is cached_dict
    # Because an achievement unlocked, the achievements subtree was
    # refreshed in place so the done payload reflects the new state.
    assert post.state_dict["achievements"] is fresh_achievements


def test_post_turn_skips_achievements_refresh_when_nothing_unlocks():
    """If ``check_achievements`` returns an empty list, there's nothing
    to refresh — skip the extra ``AchievementManager.to_dict()`` call."""
    gs = _make_game_state(achievements_unlocked=[])

    collect_post_turn_effects(gs, "wait")

    gs.achievements.to_dict.assert_not_called()


# ----- advance_one_turn ----------------------------------------------------


def test_advance_one_turn_orchestrates_full_flow():
    change = StateChange(location="Forest", items_gained=["Key"])
    fake_event = SimpleNamespace(name="Merchant Caravan", description="...")
    transitioned = [SimpleNamespace(id="m1", title="Caravan Ambush")]
    unlocked = [SimpleNamespace(id="explorer", name="Explorer", icon="🗺️")]

    gs = _make_game_state(
        turn_number=2,
        narrator_response="You enter the forest.",
        state_change=change,
        new_event=fake_event,
        module_transitions=transitioned,
        achievements_unlocked=unlocked,
    )

    result = advance_one_turn(gs, "go forest")

    assert isinstance(result, TurnResult)
    assert result.response == "You enter the forest."

    # pre-turn
    assert result.pre.new_event is fake_event
    assert gs.turn_number == 3  # incremented exactly once
    gs.events.check_for_events.assert_called_once()

    # narrator
    gs.narrator.process_action.assert_called_once_with("go forest")

    # post-turn
    assert result.post.state_change is change
    gs.timeline.record_from_state_change.assert_called_once()
    assert result.post.module_transitions == transitioned
    assert result.post.achievements_unlocked == unlocked


def test_advance_one_turn_ordering_matches_cli_loop():
    """Verify: increment → pre-turn side effects → narrator → post-turn.
    The CLI loop's order is load-bearing (achievements depend on the
    post-narrator game_state.to_dict), so we pin the sequence."""
    call_order: list[str] = []

    gs = _make_game_state(turn_number=0)
    gs.events.check_for_events.side_effect = lambda *a, **k: (
        call_order.append("pre_event_check") or None
    )
    gs.party.check_loyalty_departures.side_effect = lambda: (
        call_order.append("pre_loyalty") or []
    )
    gs.narrator.process_action.side_effect = lambda _input: (
        call_order.append("narrator") or "OK"
    )
    gs.world.module_registry.reevaluate.side_effect = lambda _ql: (
        call_order.append("post_modules") or []
    )
    gs.achievements.check_achievements.side_effect = lambda _state: (
        call_order.append("post_achievements") or []
    )

    advance_one_turn(gs, "test")

    # pre-turn subsystems run before narrator; post-turn after.
    assert call_order.index("pre_event_check") < call_order.index("narrator")
    assert call_order.index("pre_loyalty") < call_order.index("narrator")
    assert call_order.index("narrator") < call_order.index("post_modules")
    assert call_order.index("narrator") < call_order.index("post_achievements")
