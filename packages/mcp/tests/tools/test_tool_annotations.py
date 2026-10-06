"""TOOL-2: every registered tool declares its own effect."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from pipefy_mcp.tools.registry import ToolRegistry


def test_every_tool_declares_whether_it_is_read_only():
    mcp = MCPServer("tool-annotations")
    ToolRegistry(mcp=mcp).register_tools()

    undeclared = sorted(
        tool.name
        for tool in ToolRegistry._live_tools(mcp)
        if tool.annotations is None or tool.annotations.read_only_hint is None
    )

    assert not undeclared, f"Declare readOnlyHint on: {', '.join(undeclared)}"
