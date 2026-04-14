"""Tests for v0.8.1 WebUI improvements.

Validates the static client improvements: responsive layout, HP bar,
quest sidebar, loading indicator, welcome panel, and accessibility
attributes.  These are structural HTML tests — they parse the served
``index.html`` and assert on DOM presence / attribute correctness.
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


def _get_html(client) -> str:
    response = client.get("/")
    assert response.status_code == 200
    return response.text


# ---------------------------------------------------------------------------
# Accessibility
# ---------------------------------------------------------------------------


def test_skip_link_present(client):
    """A skip-to-content link should exist for keyboard navigation."""
    html = _get_html(client)
    assert "skip-link" in html
    assert 'href="#turn-input"' in html


def test_narrator_has_role_log(client):
    """The narrator pane should have role='log' for screen readers."""
    html = _get_html(client)
    assert 'role="log"' in html


def test_status_has_aria_live(client):
    """Status element should announce changes to screen readers."""
    html = _get_html(client)
    assert 'role="status"' in html


def test_input_has_aria_label(client):
    """The turn input must have an accessible label."""
    html = _get_html(client)
    assert 'aria-label="Enter your action"' in html


def test_state_panel_has_aria_label(client):
    """The sidebar panel should be labeled for assistive tech."""
    html = _get_html(client)
    assert 'aria-label="Game state panel"' in html


# ---------------------------------------------------------------------------
# HP bar
# ---------------------------------------------------------------------------


def test_hp_bar_element_exists(client):
    """The HP bar container and fill elements must be in the DOM."""
    html = _get_html(client)
    assert 'id="hp-bar-wrapper"' in html
    assert 'id="hp-bar"' in html
    assert "hp-bar-fill" in html


def test_hp_bar_initially_hidden(client):
    """The HP bar should be hidden until character data arrives."""
    html = _get_html(client)
    assert 'id="hp-bar-wrapper" style="display: none"' in html


def test_updateHpBar_function_exists(client):
    """The JS must define the updateHpBar function."""
    html = _get_html(client)
    assert "function updateHpBar" in html


# ---------------------------------------------------------------------------
# Quest sidebar
# ---------------------------------------------------------------------------


def test_quest_section_exists(client):
    """The sidebar should have a Quests section."""
    html = _get_html(client)
    assert 'id="quest-list"' in html
    # The heading text
    assert ">Quests<" in html


def test_renderQuests_function_exists(client):
    """The JS must define the renderQuests function."""
    html = _get_html(client)
    assert "function renderQuests" in html


# ---------------------------------------------------------------------------
# Loading indicator
# ---------------------------------------------------------------------------


def test_loading_indicator_functions_exist(client):
    """showLoading and hideLoading must be defined in the JS."""
    html = _get_html(client)
    assert "function showLoading" in html
    assert "function hideLoading" in html


def test_loading_indicator_css_animation(client):
    """The CSS should include the pulse animation for the loading dots."""
    html = _get_html(client)
    assert "@keyframes pulse" in html
    assert "loading-indicator" in html


# ---------------------------------------------------------------------------
# Welcome panel
# ---------------------------------------------------------------------------


def test_welcome_panel_function_exists(client):
    """The showWelcome function must be defined and called on load."""
    html = _get_html(client)
    assert "function showWelcome" in html
    # Called at the end of the script
    assert "showWelcome()" in html


def test_welcome_panel_css(client):
    """Welcome panel styles must be present."""
    html = _get_html(client)
    assert ".welcome-panel" in html


# ---------------------------------------------------------------------------
# Responsive layout
# ---------------------------------------------------------------------------


def test_responsive_media_query(client):
    """A mobile breakpoint should exist to stack the layout."""
    html = _get_html(client)
    assert "@media (max-width: 768px)" in html


# ---------------------------------------------------------------------------
# Visual polish
# ---------------------------------------------------------------------------


def test_border_radius_variable(client):
    """CSS custom property for consistent border radius.

    v0.8.3 renamed ``--radius`` to ``--radius-soft`` as part of the
    Illuminated Terminal redesign — most surfaces are intentionally
    sharp-cornered now, so the token is used only where the HP bar
    and residual elements still need rounding.
    """
    html = _get_html(client)
    assert "--radius-soft:" in html


def test_transition_variable(client):
    """CSS custom property for consistent motion tokens.

    v0.8.3 split the single ``--transition`` shorthand into semantic
    duration + easing tokens (``--duration-fast``, ``--duration-med``,
    ``--ease``) so each component can pick an appropriate speed.
    """
    html = _get_html(client)
    assert "--duration-fast:" in html
    assert "--ease:" in html


def test_player_input_prefix_removed(client):
    """Player messages should use a CSS ::before prefix, not inline '> '."""
    html = _get_html(client)
    # The player class should have a ::before pseudo-element for the prefix
    assert ".player::before" in html


# ---------------------------------------------------------------------------
# Existing invariants still hold
# ---------------------------------------------------------------------------


def test_no_innerhtml_usage(client):
    """innerHTML must never appear — XSS safety invariant."""
    html = _get_html(client)
    # Allow the string in comments explaining the policy, but not in
    # actual JS assignment.  A simple check: innerHTML should not
    # appear followed by '=' (assignment).
    import re

    assignments = re.findall(r"innerHTML\s*=", html)
    assert len(assignments) == 0, "innerHTML assignment detected — XSS risk"


def test_eventsource_still_present(client):
    """The streaming wire-up must survive the refactor."""
    html = _get_html(client)
    assert "EventSource" in html


def test_appendMarkdownText_still_present(client):
    """The safe markdown renderer must survive the refactor."""
    html = _get_html(client)
    assert "function appendMarkdownText" in html


def test_api_routes_not_shadowed(client):
    """Regression: static mount must not shadow API routes."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
