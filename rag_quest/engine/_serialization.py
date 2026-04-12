"""Serialization helpers shared by engine `from_dict` methods.

This module exists to harden deserializers against corrupted or schema-
drifted save files. The project's clean-break save policy (see CLAUDE.md)
means new fields always get `.get(key, default)` wrappers, but legacy
`cls(**data)` patterns and direct enum bracket lookups can still crash
hard on saves where a required field is missing, an enum name has been
renamed, or a new field has been added to the dataclass but not yet to
the serialized format.

All helpers in this file are pure, no-raise unless explicitly documented.
The goal is: a deserializer that used to crash with `KeyError` or
`TypeError` now degrades to a sensible default so the game loop can
surface a friendly `ui.print_error()` instead of a raw traceback.
"""

from __future__ import annotations

import inspect
from enum import Enum
from typing import Any, Type, TypeVar

T = TypeVar("T", bound=Enum)


def safe_enum(enum_cls: Type[T], value: Any, default: T) -> T:
    """Look up an Enum member by name OR value, falling back to `default`.

    Supports both `Enum[name]` (member name lookup) and `Enum(value)`
    (member value lookup) because `to_dict` methods in this codebase use
    both conventions — `Weather` and `TimeOfDay` serialize by `.name`
    while `Disposition` serializes by `.value`. A caller that doesn't
    know which convention was used can hand the raw value to
    `safe_enum` and get the member if either lookup succeeds.

    Missing, None, mistyped, or otherwise-invalid values collapse to
    `default`. Never raises.
    """
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls[value]  # by name ("HUMAN", "FIGHTER", ...)
    except (KeyError, TypeError):
        pass
    try:
        return enum_cls(value)  # by value (1, 2, "friendly", ...)
    except (ValueError, KeyError, TypeError):
        return default


def filter_init_kwargs(cls: type, data: dict) -> dict:
    """Strip keys from `data` that aren't valid `cls.__init__` parameters.

    Guards against `cls(**data)` blowing up with
    `TypeError: __init__() got an unexpected keyword argument 'X'`
    when the serialized format has an extra field the current class
    doesn't know about — e.g. a save written by a newer build being
    loaded by an older one, or a field rename that left the old key
    in a user's on-disk save.
    """
    try:
        sig = inspect.signature(cls.__init__)
    except (TypeError, ValueError):
        return dict(data)
    accepted = {
        name
        for name, param in sig.parameters.items()
        if param.kind
        in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
        and name != "self"
    }
    return {k: v for k, v in data.items() if k in accepted}
