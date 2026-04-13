"""Pure turn-loop mechanics shared by the CLI loop and the web endpoints.

The CLI's ``run_game`` loop interleaves Rich console prints with state
mutations — great for a terminal session, impossible to reuse from a web
handler. This module extracts the mutation layer so both callers can
invoke the exact same sequence:

    1. Increment ``turn_number``.
    2. Pre-turn side effects (event check / expire / party loyalty).
    3. Narrator response (non-streaming).
    4. Post-turn side effects (timeline / module gating / achievements).

CLI streaming and web streaming compose ``collect_pre_turn_effects`` +
``Narrator.stream_action`` + ``collect_post_turn_effects`` directly, so
streaming clients get identical semantics without going through
``advance_one_turn`` (which owns the non-streaming narrator call).

**Contract**: no Rich imports, no ``console.print``, no I/O beyond what
the underlying subsystems already do. Every exception from a subsystem
is logged via ``log_swallowed_exc`` so a flaky component never kills a
turn — the CLI loop uses the same additive pattern today.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .._debug import log_swallowed_exc

if TYPE_CHECKING:
    from .game import GameState
    from .state_parser import StateChange


@dataclass
class PreTurnEffects:
    """Side effects collected before the narrator runs."""

    new_event: Optional[Any] = None
    expired_events: List[str] = field(default_factory=list)
    departed_party_members: List[str] = field(default_factory=list)


@dataclass
class PostTurnEffects:
    """Side effects collected after the narrator runs."""

    state_change: Optional["StateChange"] = None
    module_transitions: List[Any] = field(default_factory=list)
    achievements_unlocked: List[Any] = field(default_factory=list)
    # Cached ``GameState.to_dict()`` produced inside
    # ``collect_post_turn_effects`` so web callers can emit the done
    # payload without re-serializing the whole state. The CLI loop
    # ignores this field. ``None`` when the serialization itself raised.
    state_dict: Optional[Dict[str, Any]] = None


@dataclass
class TurnResult:
    """Full result of ``advance_one_turn``."""

    response: str
    pre: PreTurnEffects
    post: PostTurnEffects


def collect_pre_turn_effects(game_state: "GameState") -> PreTurnEffects:
    """Advance the turn counter and run all pre-narrator subsystems.

    Matches the CLI ordering in ``game.run_game``: increment first, then
    check for a new world event (which depends on the new turn number),
    then expire stale events, then check party loyalty. Each subsystem
    is wrapped in its own swallow block so one failure can't cascade.
    """
    game_state.turn_number += 1

    new_event: Optional[Any] = None
    try:
        new_event = game_state.events.check_for_events(
            game_state.turn_number, event_chance=0.08
        )
    except Exception:
        log_swallowed_exc("turn.pre.check_for_events")

    expired: List[str] = []
    try:
        expired = game_state.events.expire_events()
    except Exception:
        log_swallowed_exc("turn.pre.expire_events")

    departed: List[str] = []
    try:
        departed = game_state.party.check_loyalty_departures()
    except Exception:
        log_swallowed_exc("turn.pre.loyalty_departures")

    return PreTurnEffects(
        new_event=new_event,
        expired_events=expired,
        departed_party_members=departed,
    )


def collect_post_turn_effects(
    game_state: "GameState", player_input: str
) -> PostTurnEffects:
    """Run timeline, module gating, and achievement checks after a turn.

    Reads ``game_state.narrator.last_change`` for the state delta — both
    ``Narrator.process_action`` and ``Narrator.stream_action`` populate
    it as part of their contract. If ``last_change`` is missing (e.g.
    narrator fell back to an error string), the timeline recorder is
    skipped but module/achievement checks still run.
    """
    change: Optional["StateChange"] = getattr(game_state.narrator, "last_change", None)

    if change is not None:
        try:
            location = ""
            character = getattr(game_state, "character", None)
            if character is not None:
                location = getattr(character, "location", "") or ""
            game_state.timeline.record_from_state_change(
                turn=game_state.turn_number,
                change=change,
                player_input=player_input,
                location=location,
            )
        except Exception:
            log_swallowed_exc("turn.post.timeline_record")

    module_transitions: List[Any] = []
    try:
        module_transitions = list(
            game_state.world.module_registry.reevaluate(game_state.quest_log) or []
        )
    except Exception:
        log_swallowed_exc("turn.post.module_reevaluate")

    # Serialize the full state ONCE after timeline + module mutations
    # have landed. ``check_achievements`` reads from this same dict, and
    # the web layer reuses it for the non-streaming done payload so we
    # don't pay for a second full ``to_dict()`` per turn (rag-quest-dqr).
    state_dict: Optional[Dict[str, Any]] = None
    try:
        state_dict = game_state.to_dict()
    except Exception:
        log_swallowed_exc("turn.post.state_dict")

    achievements_unlocked: List[Any] = []
    if getattr(game_state, "achievements", None) is not None:
        try:
            achievements_unlocked = list(
                game_state.achievements.check_achievements(state_dict) or []
            )
        except Exception:
            log_swallowed_exc("turn.post.check_achievements")
        # ``check_achievements`` mutates ``game_state.achievements`` in
        # place when it unlocks something. Refresh just the achievements
        # subtree so the cached dict reflects the newly unlocked entries
        # without re-serializing character/world/inventory/etc.
        if achievements_unlocked and state_dict is not None:
            try:
                state_dict["achievements"] = game_state.achievements.to_dict()
            except Exception:
                log_swallowed_exc("turn.post.state_dict_refresh")

    return PostTurnEffects(
        state_change=change,
        module_transitions=module_transitions,
        achievements_unlocked=achievements_unlocked,
        state_dict=state_dict,
    )


def advance_one_turn(game_state: "GameState", player_input: str) -> TurnResult:
    """Non-streaming turn: pre → narrator.process_action → post.

    Used by ``POST /session/{id}/turn`` in the web layer. The CLI loop
    streams via ``Narrator.stream_action`` and composes the pre/post
    helpers manually, so it does not call this function.
    """
    pre = collect_pre_turn_effects(game_state)
    response = game_state.narrator.process_action(player_input)
    post = collect_post_turn_effects(game_state, player_input)
    return TurnResult(response=response, pre=pre, post=post)
