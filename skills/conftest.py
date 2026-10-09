"""Check the MCP call examples in skill references against the tool input schemas.

Sybil collects each fenced block tagged ``mcp`` and checks every line in it as one
tool call: the tool must exist, every argument must be a parameter of the tool, and
every required parameter must be present. Argument values are placeholders, so the
check reads only the names.
"""

from __future__ import annotations

import shlex
from functools import cache

from mcp.server.mcpserver import MCPServer
from pipefy_mcp.tools.registry import ToolRegistry
from sybil import Example, Sybil
from sybil.parsers.markdown import CodeBlockParser


@cache
def _tool_schemas() -> dict[str, dict]:
    mcp = MCPServer("skill-examples")
    ToolRegistry(mcp).register_tools()
    return {tool.name: tool.parameters for tool in mcp._tool_manager.list_tools()}


def check_mcp_call(example: Example) -> str | None:
    for line in example.parsed.splitlines():
        if not line.strip():
            continue
        tool, *arguments = shlex.split(line)
        schema = _tool_schemas().get(tool)
        if schema is None:
            return f"{tool} is not an MCP tool"
        names = {argument.partition("=")[0] for argument in arguments}
        unknown = names - schema["properties"].keys()
        if unknown:
            return f"{tool} has no parameter {', '.join(sorted(unknown))}"
        missing = set(schema.get("required", ())) - names
        if missing:
            return f"{tool} needs {', '.join(sorted(missing))}"
    return None


pytest_collect_file = Sybil(
    parsers=[CodeBlockParser(language="mcp", evaluator=check_mcp_call)],
    patterns=["introspection/pipefy-introspection/references/mcp.md"],
).pytest()
