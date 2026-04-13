"""Tests for the static web client mount."""

import pytest

pytest.importorskip("fastapi")

from rag_quest.web.app import SessionStore, app  # noqa: E402


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture(autouse=True)
def _isolate_session_store():
    app.state.sessions = SessionStore()
    yield
    app.state.sessions = SessionStore()


def test_root_serves_index_html(client):
    """``GET /`` must return the static index. Regression guard: if a
    future refactor registers the StaticFiles mount before the API
    routes, the mount would shadow ``/healthz`` etc. and every API test
    would flake with a 404 wall."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    body = response.text
    assert "<title>RAG-Quest</title>" in body
    # Sanity check: the JS wire-up code is present so we haven't shipped
    # an empty shell.
    assert "EventSource" in body
    assert "/session/load" in body


def test_api_routes_still_resolve_with_static_mount(client):
    """The static mount is registered last so API routes keep priority.
    This test exists so that invariant is load-bearing and not just
    something I happened to get right today."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
