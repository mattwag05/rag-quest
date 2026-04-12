"""Regression tests: state parser strips Markdown emphasis from extractions."""

from rag_quest.engine.state_parser import StateParser


def test_strip_markdown_unit():
    p = StateParser()
    assert p._strip_markdown("**Captain Mira**") == "Captain Mira"
    assert p._strip_markdown("__bold__") == "bold"
    assert p._strip_markdown("*italic*") == "italic"
    assert p._strip_markdown("_under_") == "under"
    assert p._strip_markdown("plain text") == "plain text"
    assert p._strip_markdown("") == ""
    # Dangling / mismatched markers still get cleaned
    assert "**" not in p._strip_markdown("**half")
    assert "__" not in p._strip_markdown("broken__")


def test_npc_extraction_strips_bold():
    p = StateParser()
    change = p.parse_narrator_response(
        "You meet **Captain Mira**, the harbormaster.", "look around"
    )
    assert change.npc_met == "Captain Mira"


def test_item_extraction_strips_bold():
    p = StateParser()
    change = p.parse_narrator_response(
        "You pick up a **rusty iron sword**.", "search the chest"
    )
    assert "rusty iron sword" in change.items_gained
    assert not any("*" in item for item in change.items_gained)


def test_location_extraction_strips_bold():
    p = StateParser()
    change = p.parse_narrator_response(
        "You travel to **Whispering Woods**.", "go north"
    )
    assert change.location == "Whispering Woods"


def test_quest_extraction_strips_italic():
    p = StateParser()
    change = p.parse_narrator_response(
        "New quest: *Recover the lost amulet*.", "accept"
    )
    assert change.quest_offered is not None
    assert "*" not in change.quest_offered


# ---------------------------------------------------------------------------
# False-positive extractions (rag-quest-b2n)
# ---------------------------------------------------------------------------


def test_location_strips_trailing_prepositional_clause():
    p = StateParser()
    change = p.parse_narrator_response("You travel to Whispering Woods at dawn.", "go")
    assert change.location == "Whispering Woods"


def test_pickup_rejects_idioms():
    """'take a deep breath' must not become an inventory gain."""
    p = StateParser()
    change = p.parse_narrator_response(
        "You take a deep breath and steady yourself.", "rest"
    )
    assert change.items_gained == []


def test_npc_rejects_scenery():
    """'the morning sun' is scenery, not an NPC."""
    p = StateParser()
    change = p.parse_narrator_response("You see the morning sun rising.", "look")
    assert change.npc_met is None


def test_npc_strips_trailing_dangling_preposition():
    """'wild fox in' → 'wild fox' (trailing 'in' from truncated match)."""
    p = StateParser()
    change = p.parse_narrator_response("You encounter a wild fox in the path.", "look")
    assert change.npc_met == "wild fox"
