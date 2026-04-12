"""Lightweight debug-log helper for silent-fallback catch sites.

The project deliberately keeps several `except Exception: pass` blocks in
additive per-turn hooks (timeline recorder, module gating, notetaker
auto-refresh) so a flaky subsystem can never crash the game loop. The
downside is that a real bug — method renamed, contract changed, typo —
can hide there for an unknown number of releases. That already happened
once with the narrator→WorldRAG.query typo (see rag-quest-aem).

`log_swallowed_exc(context)` is the one-call mitigation. Normal runs
stay silent. When `RAG_QUEST_DEBUG=1` is exported, every swallowed
exception prints a short traceback to stderr tagged with the context
string, so a developer can flip the switch and immediately see what's
being eaten.

Usage at the catch site:

    try:
        do_the_optional_thing()
    except Exception:
        from .._debug import log_swallowed_exc
        log_swallowed_exc("timeline.record")

The import stays local so the debug helper has zero startup cost on
the hot path.
"""

from __future__ import annotations

import os
import sys
import traceback

_ENV_FLAG = "RAG_QUEST_DEBUG"


def debug_enabled() -> bool:
    """True iff the `RAG_QUEST_DEBUG` env var is set to anything non-empty."""
    return bool(os.environ.get(_ENV_FLAG))


def log_swallowed_exc(context: str) -> None:
    """Print a tagged traceback for a just-caught exception, iff debug mode is on.

    Must be called from inside an `except` block — uses `traceback.print_exc`
    to grab the current exception. Caller passes a short context string
    ("timeline.record", "module.reevaluate") so the output identifies the
    site without needing to walk the frame.
    """
    if not debug_enabled():
        return
    sys.stderr.write(f"[RAG_QUEST_DEBUG {context}] ")
    traceback.print_exc(file=sys.stderr)
