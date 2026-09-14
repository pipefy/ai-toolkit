"""Unit tests for canonical tool error helpers."""

import pytest

from pipefy_mcp.core.tool_error_envelope import (
    tool_error,
    tool_error_message,
)


def test_tool_error_includes_message_and_optional_code() -> None:
    out = tool_error("nope", code="E_BAD")
    assert out == {
        "success": False,
        "error": {"message": "nope", "code": "E_BAD"},
    }


def test_tool_error_message_from_structured() -> None:
    assert tool_error_message({"success": False, "error": {"message": "x"}}) == "x"


def test_tool_error_message_legacy_string() -> None:
    assert tool_error_message({"success": False, "error": "plain"}) == "plain"


@pytest.mark.parametrize("message", ["", " ", "\t\r\n", "\u2003"])
def test_tool_error_blank_message_gets_fallback(message):
    assert tool_error(message, code="UPSTREAM", details={"request_id": "r1"}) == {
        "success": False,
        "error": {
            "message": "Tool request failed.",
            "code": "UPSTREAM",
            "details": {"request_id": "r1"},
        },
    }


@pytest.mark.parametrize(
    "message", ["Re-read the card before retrying.", "  Domain failure.\n"]
)
def test_tool_error_preserves_nonblank_message_verbatim(message):
    assert tool_error(message)["error"]["message"] == message


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["legacy", "auto"])
@pytest.mark.parametrize("message", ["", " \t\n", "Read the rule before retrying."])
async def test_tool_error_message_survives_mcp_serialization(mode, message):
    from mcp.client import Client
    from mcp.server.mcpserver import MCPServer

    app = MCPServer("Error envelope regression")

    @app.tool()
    def failed_request() -> dict:
        return tool_error(message, code="UPSTREAM_FAILURE")

    async with Client(app, mode=mode) as client:
        result = await client.call_tool("failed_request", {})

    import json

    envelope = json.loads(result.content[0].text)
    assert result.is_error is False
    assert envelope == {
        "success": False,
        "error": {
            "message": message if message.strip() else "Tool request failed.",
            "code": "UPSTREAM_FAILURE",
        },
    }
