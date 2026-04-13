"""Shared test helpers for RAG-Quest test suite.

Helpers here are used across multiple test files. Import explicitly with
``from conftest import <name>`` in any test module that needs them.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock


def wire_turn_subsystems(
    gs: MagicMock,
    *,
    new_event=None,
    expired_events: list | None = None,
    departed_party_members: list | None = None,
    module_transitions: list | None = None,
    achievements_unlocked: list | None = None,
) -> None:
    """Wire every subsystem that the shared turn helper touches to safe defaults.

    Tests override individual subsystems by replacing the relevant
    ``return_value`` / ``side_effect`` after calling this helper.
    """
    gs.character = SimpleNamespace(location="Town Square")

    gs.events = MagicMock(name="events")
    gs.events.check_for_events.return_value = new_event
    gs.events.expire_events.return_value = expired_events or []

    gs.party = MagicMock(name="party")
    gs.party.check_loyalty_departures.return_value = departed_party_members or []

    gs.timeline = MagicMock(name="timeline")
    gs.timeline.record_from_state_change.return_value = []

    gs.world = MagicMock(name="world")
    gs.world.module_registry.reevaluate.return_value = module_transitions or []

    gs.achievements = MagicMock(name="achievements")
    gs.achievements.check_achievements.return_value = achievements_unlocked or []
