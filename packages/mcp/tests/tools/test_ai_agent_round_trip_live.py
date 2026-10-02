"""Live AI agent round trip: read an agent, send it back unchanged, read it again (opt-in integration).

Covers ``human_validation`` and ``mcp_tool`` actions, whose metadata keys the read must select and the
write must keep. The test creates a throwaway MCP server and an inactive agent on the given pipe, and
deletes both at the end.

Run (``.env`` with ``PIPEFY_*`` and a disposable pipe you administer):

    export AI_AGENT_ROUND_TRIP_PIPE_ID=123456789
    uv run pytest packages/mcp/tests/tools/test_ai_agent_round_trip_live.py -m integration -v
"""

from __future__ import annotations

import os
import re
from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from _mcp_compat import (
    create_connected_server_and_client_session as create_client_session,
)
from _shared.live_settings import pipefy_live_configured, require_live_creds

from pipefy_mcp.server import build_pipefy_mcp_server
from pipefy_mcp.settings import settings

if not pipefy_live_configured():
    pytest.skip("live MCP tests require Pipefy credentials", allow_module_level=True)

mcp_server = build_pipefy_mcp_server(settings)

_PLACEHOLDER = re.compile(r"%\{action:([^}]+)\}")

# Saving an mcp_tool action does not need a connected server, so any MCP URL works here.
_MCP_SERVER_URL = "https://mcp.pipefy.com/mcp"

_CREATE_MCP_SERVER = """
mutation($input: CreateMcpServerInput!) {
  createMcpServer(input: $input) { mcpServer { id } }
}
"""
_DELETE_MCP_SERVER = """
mutation($input: DeleteMcpServerInput!) {
  deleteMcpServer(input: $input) { clientMutationId }
}
"""


def _round_trip_pipe_id() -> str | None:
    return os.environ.get("AI_AGENT_ROUND_TRIP_PIPE_ID", "").strip() or None


def _normalized(agent: dict[str, Any]) -> dict[str, Any]:
    """The agent with server-assigned ids and per-save ``referenceId`` values replaced by positions."""
    behaviors = []
    for behavior in agent.get("behaviors") or []:
        params = behavior["actionParams"]["aiBehaviorParams"]
        position = {
            a["referenceId"]: i for i, a in enumerate(params["actionsAttributes"])
        }
        instruction = _PLACEHOLDER.sub(
            lambda m: f"%{{action:#{position.get(m.group(1), 'stale')}}}",
            params["instruction"],
        )
        actions = [
            {k: v for k, v in a.items() if k not in ("id", "referenceId")}
            for a in params["actionsAttributes"]
        ]
        behaviors.append(
            {
                **{k: v for k, v in behavior.items() if k != "id"},
                "actionParams": {
                    **behavior["actionParams"],
                    "aiBehaviorParams": {
                        **params,
                        "instruction": instruction,
                        "actionsAttributes": actions,
                    },
                },
            }
        )
    return {
        **{k: v for k, v in agent.items() if k != "behaviors"},
        "behaviors": behaviors,
    }


def _one_placeholder_per_action(agent: dict[str, Any]) -> bool:
    for behavior in agent.get("behaviors") or []:
        params = behavior["actionParams"]["aiBehaviorParams"]
        refs = sorted(a["referenceId"] for a in params["actionsAttributes"])
        if sorted(_PLACEHOLDER.findall(params["instruction"])) != refs:
            return False
    return True


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_ai_agent_read_update_round_trip_is_lossless(extract_payload):
    """Two read-then-update passes leave the agent as it was created, placeholders included."""
    require_live_creds()
    pipe_id = _round_trip_pipe_id()
    if not pipe_id:
        pytest.skip(
            "Set AI_AGENT_ROUND_TRIP_PIPE_ID to a disposable pipe to run the AI agent round trip"
        )

    with patch("pipefy_mcp.settings.settings", settings):
        async with create_client_session(
            mcp_server,
            read_timeout_seconds=timedelta(seconds=120),
            raise_exceptions=True,
        ) as session:

            async def call(name: str, args: dict[str, Any]) -> dict[str, Any]:
                result = await session.call_tool(name, args)
                assert result.is_error is False, result
                return extract_payload(result)

            async def graphql(query: str, variables: dict[str, Any]) -> dict[str, Any]:
                args = {"query": query, "variables": variables, "include_parsed": True}
                body = await call("execute_graphql", args)
                if body.get("requires_confirmation"):
                    body = await call(
                        "execute_graphql",
                        {
                            **args,
                            "confirm": True,
                            "confirmation_token": body["confirmation_token"],
                        },
                    )
                assert body.get("success") is True, body
                return body["data"]

            async def read(uuid: str) -> dict[str, Any]:
                body = await call("get_ai_agent", {"uuid": uuid})
                assert body.get("success") is True, body
                return body["data"]["agent"]

            pipe = (await call("get_pipe", {"pipe_id": pipe_id}))["pipe"]
            phases = pipe["phases"]
            destination_phase_id = phases[min(1, len(phases) - 1)]["id"]
            resource = {"id": pipe["uuid"], "type": "pipe"}
            reviewer = (await graphql("{ me { email } }", {}))["me"]["email"]

            server = await graphql(
                _CREATE_MCP_SERVER,
                {
                    "input": {
                        "name": "ai-toolkit round-trip test",
                        "description": "Throwaway server for the AI agent round-trip test",
                        "configuration": {
                            "serverUrl": _MCP_SERVER_URL,
                            "transportType": "streamable_http",
                            "authenticationType": "no_auth",
                        },
                        "resource": resource,
                    }
                },
            )
            server_id = server["createMcpServer"]["mcpServer"]["id"]
            agent_uuid = None
            try:
                created = await call(
                    "create_ai_agent",
                    {
                        "name": "ai-toolkit round-trip test",
                        "repo_uuid": pipe["uuid"],
                        "instruction": "Throwaway agent for the round-trip test.",
                        "active": False,
                        "behaviors": [
                            {
                                "name": "Move on create",
                                "event_id": "card_created",
                                "actionParams": {
                                    "aiBehaviorParams": {
                                        "instruction": "Move the card.",
                                        "actionsAttributes": [
                                            {
                                                "name": "Move",
                                                "actionType": "move_card",
                                                "metadata": {
                                                    "destinationPhaseId": destination_phase_id
                                                },
                                            }
                                        ],
                                    }
                                },
                            },
                            {
                                "name": "Review and look up",
                                "event_id": "card_created",
                                "actionParams": {
                                    "aiBehaviorParams": {
                                        "instruction": "Ask for a review, then look the pipe up.",
                                        "actionsAttributes": [
                                            {
                                                "name": "Review",
                                                "actionType": "human_validation",
                                                "metadata": {
                                                    "emails": [reviewer],
                                                    "title": "Review this card",
                                                },
                                            },
                                            {
                                                "name": "Look up pipe",
                                                "actionType": "mcp_tool",
                                                "metadata": {
                                                    "mcpServerId": server_id,
                                                    "toolName": "get_pipe",
                                                    "toolInputs": [
                                                        {
                                                            "name": "pipe_id",
                                                            "source": "fixed_value",
                                                            "value": pipe_id,
                                                        }
                                                    ],
                                                },
                                            },
                                        ],
                                    }
                                },
                            },
                        ],
                    },
                )
                assert created.get("success") is True, created
                agent_uuid = created["data"]["agent_uuid"]

                first = await read(agent_uuid)
                metadata = {
                    a["actionType"]: a["metadata"]
                    for b in first["behaviors"]
                    for a in b["actionParams"]["aiBehaviorParams"]["actionsAttributes"]
                }
                assert metadata["human_validation"]["emails"] == [reviewer]
                assert metadata["human_validation"]["title"] == "Review this card"
                assert metadata["mcp_tool"]["mcpServerId"] == server_id
                assert metadata["mcp_tool"]["toolName"] == "get_pipe"
                assert metadata["mcp_tool"]["toolInputs"]
                assert _one_placeholder_per_action(first)

                current = first
                for _ in range(2):
                    updated = await call(
                        "update_ai_agent",
                        {
                            "uuid": agent_uuid,
                            "name": current["name"],
                            "repo_uuid": current["repoUuid"],
                            "instruction": current["instruction"],
                            "behaviors": current["behaviors"],
                            "disabled_at": current["disabledAt"],
                        },
                    )
                    assert updated.get("success") is True, updated
                    current = await read(agent_uuid)
                    assert _normalized(current) == _normalized(first)
                    assert _one_placeholder_per_action(current)
            finally:
                if agent_uuid:
                    preview = await call("delete_ai_agent", {"uuid": agent_uuid})
                    await call(
                        "delete_ai_agent",
                        {
                            "uuid": agent_uuid,
                            "confirm": True,
                            "confirmation_token": preview["confirmation_token"],
                        },
                    )
                await graphql(
                    _DELETE_MCP_SERVER,
                    {"input": {"uuid": server_id, "resource": resource}},
                )
