"""``docs/mcp/reference.md`` is generated from the registered tools and stays current."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts/gen_mcp_reference.py"
_spec = importlib.util.spec_from_file_location("gen_mcp_reference", _SCRIPT)
assert _spec and _spec.loader
_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gen)

_DOCSTRING = """Move a card to a target phase.

    Use this when the workflow should advance a card.

    Args:
        card_id: The card to move.
            Discover via: ``find_cards``.
        destination_phase_id: Target phase ID.

    Returns:
        dict: The move mutation response.
    """


def test_summary_is_the_first_paragraph():
    assert _gen.summary_of(_DOCSTRING) == "Move a card to a target phase."


def test_args_section_maps_each_parameter_to_its_joined_description():
    assert _gen.parse_args_section(_DOCSTRING) == {
        "card_id": "The card to move. Discover via: ``find_cards``.",
        "destination_phase_id": "Target phase ID.",
    }


def test_args_section_is_empty_without_an_args_block():
    assert _gen.parse_args_section("List organizations.") == {}


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ({"type": "string"}, "string"),
        ({}, "any"),
        ({"type": "array", "items": {"type": "string"}}, "array of string"),
        ({"type": "array", "items": {}}, "array"),
        ({"anyOf": [{"type": "integer"}, {"type": "null"}]}, "integer | null"),
        ({"$ref": "#/$defs/CardSearch"}, "CardSearch"),
        ({"enum": ["internal", "public"]}, '"internal" | "public"'),
    ],
)
def test_type_of_renders_a_json_schema(schema, expected):
    assert _gen.type_of(schema) == expected


def test_render_reference_writes_domains_tools_flags_and_parameters():
    tool = _gen.ToolEntry(
        name="delete_card",
        summary="Delete a card.",
        read_only=False,
        destructive=True,
        remote=True,
        params=(
            _gen.Param("card_id", "string", None, "The card | to delete."),
            _gen.Param("debug", "boolean", "false", ""),
        ),
    )
    page = _gen.render_reference(
        [_gen.Domain("workflow", "Running a process.", (tool,))]
    )

    assert page.startswith("# MCP tool reference\n")
    assert "## workflow\n\nRunning a process.\n" in page
    assert (
        "### `delete_card`\n\nDelete a card.\n\nFlags: destructive, remote.\n" in page
    )
    assert "| `card_id` | `string` | required | The card \\| to delete. |" in page
    assert "| `debug` | `boolean` | `false` |  |" in page


def test_render_reference_says_when_a_tool_takes_no_parameters():
    tool = _gen.ToolEntry("list_organizations", "List orgs.", True, False, False, ())
    page = _gen.render_reference([_gen.Domain("governance", "Admin.", (tool,))])

    assert "Flags: read-only.\n\nTakes no parameters.\n" in page


def test_committed_reference_matches_the_registered_tools():
    committed = (_ROOT / "docs/mcp/reference.md").read_text(encoding="utf-8")
    assert committed == _gen.render_reference(_gen.collect_domains()), (
        "docs/mcp/reference.md is stale. "
        "Run `uv run python scripts/gen_mcp_reference.py`."
    )
