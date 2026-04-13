"""Tests for v0.8.2 web onboarding — new game creation from the browser.

Covers:
- Onboarding data endpoints (/onboarding/races, /classes, /templates)
- New session creation endpoint (/session/new)
- Static HTML contains onboarding UI elements
- Onboarding module data integrity
"""

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


# ---------------------------------------------------------------------------
# Onboarding data endpoints
# ---------------------------------------------------------------------------


def test_list_races_returns_five(client):
    """GET /onboarding/races should return all 5 playable races."""
    res = client.get("/onboarding/races")
    assert res.status_code == 200
    races = res.json()
    assert len(races) == 5
    ids = {r["id"] for r in races}
    assert ids == {"HUMAN", "ELF", "DWARF", "HALFLING", "ORC"}


def test_races_have_required_fields(client):
    """Each race must have id, name, description, bonuses."""
    for race in client.get("/onboarding/races").json():
        assert "id" in race
        assert "name" in race
        assert "description" in race
        assert "bonuses" in race


def test_list_classes_returns_five(client):
    """GET /onboarding/classes should return all 5 classes."""
    res = client.get("/onboarding/classes")
    assert res.status_code == 200
    classes = res.json()
    assert len(classes) == 5
    ids = {c["id"] for c in classes}
    assert ids == {"FIGHTER", "MAGE", "ROGUE", "RANGER", "CLERIC"}


def test_classes_have_required_fields(client):
    """Each class must have id, name, description, abilities, hp."""
    for cls in client.get("/onboarding/classes").json():
        assert "id" in cls
        assert "name" in cls
        assert "description" in cls
        assert "abilities" in cls
        assert "hp" in cls
        assert isinstance(cls["hp"], int)


def test_list_templates_returns_four(client):
    """GET /onboarding/templates should return all 4 starter templates."""
    res = client.get("/onboarding/templates")
    assert res.status_code == 200
    templates = res.json()
    assert len(templates) == 4


def test_templates_have_required_fields(client):
    """Each template must have id, name, description, setting, tone."""
    for tpl in client.get("/onboarding/templates").json():
        assert "id" in tpl
        assert "name" in tpl
        assert "description" in tpl
        assert "setting" in tpl
        assert "tone" in tpl
        assert "starting_location" in tpl


# ---------------------------------------------------------------------------
# /session/new endpoint validation
# ---------------------------------------------------------------------------


def test_new_session_rejects_empty_name(client):
    """POST /session/new with an empty character name should 400."""
    res = client.post(
        "/session/new",
        json={
            "character_name": "",
            "race": "HUMAN",
            "character_class": "FIGHTER",
            "template_id": "classic_dungeon",
        },
    )
    assert res.status_code == 400
    assert "empty" in res.text.lower()


def test_new_session_rejects_unknown_race(client):
    """POST /session/new with a bogus race should 400."""
    res = client.post(
        "/session/new",
        json={
            "character_name": "Tester",
            "race": "GOBLIN",
            "character_class": "FIGHTER",
            "template_id": "classic_dungeon",
        },
    )
    assert res.status_code == 400
    assert "race" in res.text.lower() or "unknown" in res.text.lower()


def test_new_session_rejects_unknown_class(client):
    """POST /session/new with a bogus class should 400."""
    res = client.post(
        "/session/new",
        json={
            "character_name": "Tester",
            "race": "HUMAN",
            "character_class": "BARD",
            "template_id": "classic_dungeon",
        },
    )
    assert res.status_code == 400
    assert "class" in res.text.lower() or "unknown" in res.text.lower()


def test_new_session_rejects_unknown_template(client):
    """POST /session/new with a bogus template should 400."""
    res = client.post(
        "/session/new",
        json={
            "character_name": "Tester",
            "race": "HUMAN",
            "character_class": "FIGHTER",
            "template_id": "nonexistent_world",
        },
    )
    assert res.status_code == 400
    assert "template" in res.text.lower() or "unknown" in res.text.lower()


def test_new_session_rejects_long_name(client):
    """Character names > 50 chars should be rejected."""
    res = client.post(
        "/session/new",
        json={
            "character_name": "A" * 51,
            "race": "HUMAN",
            "character_class": "FIGHTER",
            "template_id": "classic_dungeon",
        },
    )
    assert res.status_code == 400
    assert "long" in res.text.lower() or "50" in res.text


# ---------------------------------------------------------------------------
# Static HTML onboarding elements
# ---------------------------------------------------------------------------


def _get_html(client) -> str:
    res = client.get("/")
    assert res.status_code == 200
    return res.text


def test_new_game_button_exists(client):
    """The header must have a New Game button."""
    html = _get_html(client)
    assert 'id="new-game-btn"' in html


def test_onboarding_overlay_exists(client):
    """The onboarding overlay container must be in the DOM."""
    html = _get_html(client)
    assert 'id="onboarding-overlay"' in html
    assert 'id="onboarding-card"' in html


def test_onboarding_overlay_starts_hidden(client):
    """The overlay must start with the hidden class."""
    html = _get_html(client)
    assert 'class="hidden"' in html or "hidden" in html


def test_onboarding_has_dialog_role(client):
    """The overlay should have role='dialog' for accessibility."""
    html = _get_html(client)
    assert 'role="dialog"' in html


def test_onboarding_js_functions_exist(client):
    """Key onboarding JS functions must be defined."""
    html = _get_html(client)
    assert "function openOnboarding" in html
    assert "function closeOnboarding" in html
    assert "function renderOnboardingStep" in html
    assert "function submitNewGame" in html


def test_onboarding_fetches_data(client):
    """The JS should fetch /onboarding/races, /classes, /templates."""
    html = _get_html(client)
    assert "/onboarding/races" in html
    assert "/onboarding/classes" in html
    assert "/onboarding/templates" in html


def test_no_innerhtml_in_onboarding(client):
    """innerHTML must never appear — XSS safety invariant."""
    import re

    html = _get_html(client)
    assignments = re.findall(r"innerHTML\s*=", html)
    assert len(assignments) == 0, "innerHTML assignment detected — XSS risk"


# ---------------------------------------------------------------------------
# Onboarding module data integrity
# ---------------------------------------------------------------------------


def test_onboarding_races_match_engine():
    """Onboarding RACES should match the engine's Race enum."""
    from rag_quest.engine.character import Race
    from rag_quest.web.onboarding import RACES

    onboarding_ids = {r["id"] for r in RACES}
    engine_ids = {r.name for r in Race}
    assert onboarding_ids == engine_ids


def test_onboarding_classes_match_engine():
    """Onboarding CLASSES should match the engine's CharacterClass enum."""
    from rag_quest.engine.character import CharacterClass
    from rag_quest.web.onboarding import CLASSES

    onboarding_ids = {c["id"] for c in CLASSES}
    engine_ids = {c.name for c in CharacterClass}
    assert onboarding_ids == engine_ids


def test_onboarding_templates_match_starter_worlds():
    """Onboarding TEMPLATES should cover all STARTER_WORLDS keys."""
    from rag_quest.web.onboarding import TEMPLATES
    from rag_quest.worlds.templates import STARTER_WORLDS

    onboarding_ids = {t["id"] for t in TEMPLATES}
    starter_ids = set(STARTER_WORLDS.keys())
    assert onboarding_ids == starter_ids
