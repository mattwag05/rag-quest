"""Shared StateChange → event payload helper.

``Timeline.record_from_state_change`` and the v0.9 ``WorldDB`` shadow write
in ``engine/turn.py`` both translate a ``StateChange`` into per-turn event
records. Phase 3 of the memory architecture redesign will make Timeline a
view over ``WorldDB.events``, at which point both call sites must emit the
exact same rows. Centralizing the mapping here pre-pays that debt — new
``StateChange`` fields go in one place, and the two consumers keep lockstep.

Phase 1 scope: this module only produces payloads for ``WorldDB.record_event``
(and ``WorldDB.upsert_entity`` for entity-producing fields). Timeline is
unchanged — its recorder still builds ``TimelineEvent`` objects the old way.
When Phase 3 lands, ``Timeline.record_from_state_change`` will switch to
reading these payloads too.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EntityWrite:
    """An upsert to run against ``WorldDB.entities``."""

    entity_type: str
    name: str
    location: str | None = None
    status: str = "active"
    summary: str | None = None


@dataclass(frozen=True)
class EventWrite:
    """An append to run against ``WorldDB.events``."""

    event_type: str
    summary: str
    primary_entity: str | None = None
    location: str | None = None
    mechanical_changes: dict | None = None
    secondary_entities: list[str] | None = None
    is_notable: bool = False


@dataclass(frozen=True)
class RelationshipWrite:
    """A disposition / faction relationship update."""

    entity_a: str
    entity_b: str
    rel_type: str
    value: float
    cause: str | None = None


@dataclass(frozen=True)
class ShadowWrites:
    """Bundle of writes derived from a single ``StateChange``."""

    entities: list[EntityWrite]
    events: list[EventWrite]
    relationships: list[RelationshipWrite]


def state_change_to_writes(
    change: Any,
    *,
    player_input: str = "",
    location: str = "",
) -> ShadowWrites:
    """Translate a ``StateChange`` into ``WorldDB`` writes.

    Pure function, no I/O, no side effects. Each field of the ``StateChange``
    becomes zero or more entity upserts and zero or more event appends,
    matching the semantics of ``engine/narrator.py::_parse_and_apply_changes``
    and ``engine/timeline.py::Timeline.record_from_state_change``.

    Notability is flagged for combat outcomes, quest transitions,
    relationship deltas, base claims, world events, and recruits — see
    §3.2 "Notability Criteria" in ``docs/MEMORY_ARCHITECTURE.md``.
    """
    entities: list[EntityWrite] = []
    events: list[EventWrite] = []
    relationships: list[RelationshipWrite] = []

    new_location = getattr(change, "location", None)
    if new_location:
        entities.append(EntityWrite(entity_type="location", name=new_location))
        events.append(
            EventWrite(
                event_type="travel",
                summary=f"Travelled to {new_location}",
                primary_entity=new_location,
                location=new_location,
                is_notable=True,
            )
        )

    # Combat/social damage. We don't always know whether the damage came from
    # combat or a trap, so the event_type is always 'combat' and the narrator
    # prose remains the source of truth for the flavor.
    damage_taken = int(getattr(change, "damage_taken", 0) or 0)
    if damage_taken > 0:
        events.append(
            EventWrite(
                event_type="combat",
                summary=f"Took {damage_taken} damage",
                location=location or None,
                mechanical_changes={"hp_delta": -damage_taken},
                is_notable=True,
            )
        )

    hp_healed = int(getattr(change, "hp_healed", 0) or 0)
    if hp_healed > 0:
        events.append(
            EventWrite(
                event_type="combat",
                summary=f"Healed {hp_healed} HP",
                location=location or None,
                mechanical_changes={"hp_delta": hp_healed},
                is_notable=False,
            )
        )

    for item in getattr(change, "items_gained", []) or []:
        entities.append(EntityWrite(entity_type="item", name=item))
        events.append(
            EventWrite(
                event_type="item",
                summary=f"Obtained {item}",
                primary_entity=item,
                location=location or None,
                mechanical_changes={"items_gained": [item]},
            )
        )

    for item in getattr(change, "items_lost", []) or []:
        events.append(
            EventWrite(
                event_type="item",
                summary=f"Lost {item}",
                primary_entity=item,
                location=location or None,
                mechanical_changes={"items_lost": [item]},
            )
        )

    quest_offered = getattr(change, "quest_offered", None)
    if quest_offered:
        entities.append(
            EntityWrite(entity_type="quest", name=quest_offered, status="active")
        )
        events.append(
            EventWrite(
                event_type="quest_offer",
                summary=f"Quest offered: {quest_offered}",
                primary_entity=quest_offered,
                location=location or None,
                is_notable=True,
            )
        )

    quest_completed = getattr(change, "quest_completed", None)
    if quest_completed:
        entities.append(
            EntityWrite(entity_type="quest", name=quest_completed, status="completed")
        )
        events.append(
            EventWrite(
                event_type="quest_complete",
                summary=f"Quest completed: {quest_completed}",
                primary_entity=quest_completed,
                location=location or None,
                is_notable=True,
            )
        )

    npc_met = getattr(change, "npc_met", None)
    if npc_met:
        entities.append(
            EntityWrite(entity_type="npc", name=npc_met, location=location or None)
        )
        events.append(
            EventWrite(
                event_type="social",
                summary=f"Met {npc_met}",
                primary_entity=npc_met,
                location=location or None,
                is_notable=True,
            )
        )

    npc_recruited = getattr(change, "npc_recruited", None)
    if npc_recruited:
        entities.append(
            EntityWrite(
                entity_type="npc", name=npc_recruited, location=location or None
            )
        )
        events.append(
            EventWrite(
                event_type="social",
                summary=f"Recruited {npc_recruited}",
                primary_entity=npc_recruited,
                location=location or None,
                is_notable=True,
            )
        )

    # Relationship deltas. The dict keys are NPC names, values are integer
    # trust deltas (0-100 scale). Normalize to the [-1.0, 1.0] range the
    # memory architecture doc specifies, emitted as a delta that Phase 2's
    # assembler will apply on top of the current value.
    rel_changes = getattr(change, "npc_relationship_change", {}) or {}
    for npc_name, delta in rel_changes.items():
        try:
            norm = float(delta) / 50.0
        except (TypeError, ValueError):
            continue
        relationships.append(
            RelationshipWrite(
                entity_a="player",
                entity_b=npc_name,
                rel_type="disposition_delta",
                value=norm,
                cause=player_input[:120] if player_input else None,
            )
        )

    world_event = getattr(change, "world_event_triggered", None)
    if world_event:
        events.append(
            EventWrite(
                event_type="world_event",
                summary=f"World event: {world_event}",
                location=location or None,
                is_notable=True,
            )
        )

    if getattr(change, "claim_base", False):
        base_location = location or ""
        if base_location:
            entities.append(
                EntityWrite(
                    entity_type="base",
                    name=base_location,
                    location=base_location,
                )
            )
        events.append(
            EventWrite(
                event_type="base_claim",
                summary=(
                    f"Claimed base at {base_location}"
                    if base_location
                    else "Claimed base"
                ),
                location=base_location or None,
                is_notable=True,
            )
        )

    return ShadowWrites(entities=entities, events=events, relationships=relationships)
