"""Regression guard for v0.9.1 config default flips.

Locks in the `memory.assembler_enabled = True` default so it can't
silently regress. A fresh ConfigManager (no config file, no env vars)
must put the MemoryAssembler in the default-on state.
"""

import os

from rag_quest.config import ConfigManager


def test_memory_assembler_enabled_by_default(tmp_path, monkeypatch):
    """A fresh ConfigManager should report assembler_enabled=True."""
    # Isolate from both env vars and any real config file.
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setattr(
        "rag_quest.config.CONFIG_DIR", tmp_path / "rag-quest", raising=True
    )
    monkeypatch.setattr(
        "rag_quest.config.CONFIG_FILE",
        tmp_path / "rag-quest" / "config.json",
        raising=True,
    )

    cm = ConfigManager()

    assert cm.config["memory"]["assembler_enabled"] is True
    assert cm.config["memory"]["profile"] == "balanced"


def test_default_config_constant_has_memory_assembler_on():
    """The class-level DEFAULT_CONFIG must match — first-run writes this."""
    assert ConfigManager.DEFAULT_CONFIG["memory"]["assembler_enabled"] is True
