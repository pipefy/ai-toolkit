"""Live MCP path for field conditions (no execute_graphql).

Exercises **get_phase_fields** → **create_field_condition** → **delete_field_condition**
through **pipefy_mcp.server.mcp** (full ToolRegistry + PipefyClient). Skips without
**PIPEFY_*** OAuth or when **PIPE_FIELD_CONDITION_LIVE_PHASE_ID** is unset.

**Setup:** Use a disposable pipe's start-form phase with **at least two optional
text fields**. The API can attach a condition requested for an ordinary phase to
the start form instead; that still fails this test after deleting the created rule.
The test uses one field as the condition trigger (**field_address** = its **internal_id**)
and the other as **phaseFieldId** in **actions**. Grant the service account **create /
delete field conditions** on that phase.

Run:
    uv run pytest tests/tools/test_field_conditions_tools_live.py -m integration -v

Env:
    PIPE_FIELD_CONDITION_LIVE_PHASE_ID  — numeric phase ID (required for this module)
"""

from __future__ import annotations

import os
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from _mcp_compat import (
    create_connected_server_and_client_session as create_client_session,
)
from _shared.live_settings import pipefy_live_configured, require_live_creds

from pipefy_mcp.server import build_pipefy_mcp_server
from pipefy_mcp.settings import settings
from tools.field_condition_live_test_support import exercise_field_condition_lifecycle

# Building the app now resolves the Pipefy credential (the runtime wires its
# client at construction), so this credential-dependent module skips itself
# when no live creds are configured rather than failing at collection.
if not pipefy_live_configured():
    pytest.skip("live MCP tests require Pipefy credentials", allow_module_level=True)

mcp_server = build_pipefy_mcp_server(settings)


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_field_condition_tools_only_happy_path(extract_payload):
    """Full stack: get_phase_fields → create_field_condition → delete_field_condition."""
    require_live_creds()
    phase_raw = os.environ.get("PIPE_FIELD_CONDITION_LIVE_PHASE_ID")
    if not phase_raw:
        pytest.skip(
            "Set PIPE_FIELD_CONDITION_LIVE_PHASE_ID to a phase with 2+ fields "
            "(see tests/tools/test_field_conditions_tools_live.py docstring)"
        )
    phase_id = int(phase_raw)

    with patch("pipefy_mcp.settings.settings", settings):
        async with create_client_session(
            mcp_server,
            read_timeout_seconds=timedelta(seconds=120),
            raise_exceptions=True,
        ) as session:
            r_fields = await session.call_tool(
                "get_phase_fields",
                {"phase_id": phase_id, "required_only": False},
            )
    assert r_fields.is_error is False, r_fields
    pf_payload = extract_payload(r_fields)
    fields = pf_payload.get("fields") or []
    if len(fields) < 2:
        pytest.skip(
            f"Phase {phase_id} has fewer than 2 fields ({len(fields)}); "
            "add fields or pick another phase."
        )

    trigger = fields[0]
    target = fields[1]
    for label, f in ("trigger", trigger), ("target", target):
        iid = f.get("internal_id")
        if iid is None or str(iid).strip() == "":
            pytest.skip(
                f"Phase field ({label}) missing internal_id — cannot build field condition "
                "payload (ensure get_phase_fields returns internal_id from the API)."
            )

    trigger_id = str(trigger["internal_id"]).strip()
    target_id = str(target["internal_id"]).strip()

    expr_token = uuid.uuid4().hex[:10]
    condition = {
        "expressions": [
            {
                "field_address": trigger_id,
                "operation": "equals",
                "value": f"mcp_fc_sentinel_{expr_token}",
                "structure_id": 1,
            }
        ],
        "expressions_structure": [[1]],
    }
    actions = [{"phaseFieldId": target_id, "whenEvaluator": True, "actionId": "hide"}]
    rule_name = f"MCP field cond {expr_token}"

    with patch("pipefy_mcp.settings.settings", settings):
        async with create_client_session(
            mcp_server,
            read_timeout_seconds=timedelta(seconds=120),
            raise_exceptions=True,
        ) as session:
            await exercise_field_condition_lifecycle(
                session,
                {
                    "phase_id": phase_id,
                    "condition": condition,
                    "actions": actions,
                    "name": rule_name,
                    "debug": True,
                },
            )
