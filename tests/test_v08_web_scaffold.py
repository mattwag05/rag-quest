"""Smoke tests for rag_quest.web scaffold.

Skips gracefully when the optional ``[web]`` extras are not installed
so a base-install ``pytest`` run still collects cleanly.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

from rag_quest import __version__  # noqa: E402
from rag_quest.web.app import SessionStore, app  # noqa: E402


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    return TestClient(app)


def _fake_game_state() -> MagicMock:
    return MagicMock(name="game_state")


def test_healthz_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_session_store_put_and_get():
    store = SessionStore()
    gs = _fake_game_state()
    store.put("alpha", gs)

    assert store.get("alpha") is gs
    assert store.get("missing") is None
    assert store.list_names() == ["alpha"]


def test_session_store_replacing_name_closes_previous():
    store = SessionStore()
    first = _fake_game_state()
    second = _fake_game_state()

    store.put("alpha", first)
    store.put("alpha", second)

    first.world_rag.close.assert_called_once()
    first.llm.close.assert_called_once()
    assert store.get("alpha") is second


def test_session_store_close_returns_bool_and_releases_resources():
    store = SessionStore()
    gs = _fake_game_state()
    store.put("alpha", gs)

    assert store.close("alpha") is True
    assert store.close("alpha") is False
    assert store.get("alpha") is None
    gs.world_rag.close.assert_called_once()
    gs.llm.close.assert_called_once()


def test_session_store_swallows_close_errors():
    store = SessionStore()
    gs = _fake_game_state()
    gs.world_rag.close.side_effect = RuntimeError("boom rag")
    gs.llm.close.side_effect = RuntimeError("boom llm")
    store.put("alpha", gs)

    assert store.close("alpha") is True
