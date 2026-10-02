"""Facade-level tests: ``PipefyClient`` exposes the read-only AI pre-flight validators."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from _shared.ai_agent_test_payloads import minimal_behavior_dict
from _shared.fixture_ids import EXAMPLE_PIPE_ID

from pipefy_sdk import PipefyClient

FIELD_ID = "900000001"


@pytest.fixture
def facade_client() -> PipefyClient:
    client = PipefyClient.__new__(PipefyClient)
    client.get_pipe = AsyncMock(
        return_value={
            "pipe": {
                "uuid": "pipe-uuid-1",
                "phases": [],
                "start_form_fields": [{"id": "slug", "internal_id": FIELD_ID}],
            }
        }
    )
    client.get_pipe_relations = AsyncMock(
        return_value={"pipe": {"childrenRelations": [], "parentsRelations": []}}
    )
    client.get_phase_fields = AsyncMock(return_value={"fields": []})
    client.get_ai_knowledge_bases = AsyncMock(return_value=[{"id": "kb-known"}])
    client.get_pipe_with_preferences = AsyncMock(
        return_value={
            "pipe": {
                "phases": [],
                "start_form_fields": [
                    {"internal_id": FIELD_ID, "label": "Input", "editable": True},
                    {"internal_id": "900000002", "label": "Output", "editable": True},
                ],
                "preferences": {"aiAgentsEnabled": True},
            }
        }
    )
    client.get_automation_events = AsyncMock(return_value=[{"id": "card_created"}])
    client.get_ai_credit_usage = AsyncMock(
        return_value={"aiCreditUsageStats": {"active": True}}
    )
    return client


@pytest.mark.anyio
async def test_validate_ai_agent_behaviors_runs_pipe_checks(
    facade_client: PipefyClient,
):
    behavior = minimal_behavior_dict(pipe_id=EXAMPLE_PIPE_ID, field_id=FIELD_ID)

    result = await facade_client.validate_ai_agent_behaviors(
        EXAMPLE_PIPE_ID, [behavior], data_source_ids=["kb-missing"]
    )

    assert result["success"] is True
    assert result["valid"] is True
    assert any("kb-missing" in w for w in result["warnings"])
    facade_client.get_ai_knowledge_bases.assert_awaited_once_with("pipe-uuid-1")


@pytest.mark.anyio
async def test_validate_ai_agent_behaviors_reports_unknown_field(
    facade_client: PipefyClient,
):
    behavior = minimal_behavior_dict(pipe_id=EXAMPLE_PIPE_ID, field_id="999999999")

    result = await facade_client.validate_ai_agent_behaviors(
        EXAMPLE_PIPE_ID, [behavior]
    )

    assert result["success"] is True
    assert result["valid"] is False
    assert any("999999999" in p for p in result["problems"])


@pytest.mark.anyio
async def test_validate_ai_automation_prompt_runs_pipe_checks(
    facade_client: PipefyClient,
):
    result = await facade_client.validate_ai_automation_prompt(
        "1", f"Summarize %{{{FIELD_ID}}}", ["900000002"], event_id="card_created"
    )

    assert result == {
        "success": True,
        "valid": True,
        "problems": [],
        "warnings": [],
        "field_map": {FIELD_ID: "Input", "900000002": "Output"},
    }
    facade_client.get_automation_events.assert_awaited_once_with("1")


@pytest.mark.anyio
async def test_validate_ai_automation_prompt_rejects_unknown_event(
    facade_client: PipefyClient,
):
    result = await facade_client.validate_ai_automation_prompt(
        "1", f"Summarize %{{{FIELD_ID}}}", ["900000002"], event_id="card_moved"
    )

    assert result["valid"] is False
    assert any("card_moved" in p for p in result["problems"])


@pytest.mark.anyio
async def test_validate_ai_agent_behaviors_pipe_read_failure_reports_in_problems(
    facade_client: PipefyClient,
):
    facade_client.get_pipe.side_effect = RuntimeError("denied")
    behavior = minimal_behavior_dict(pipe_id=EXAMPLE_PIPE_ID, field_id=FIELD_ID)

    result = await facade_client.validate_ai_agent_behaviors(
        EXAMPLE_PIPE_ID, [behavior]
    )

    assert result == {
        "success": False,
        "valid": False,
        "problems": [f"Failed to fetch pipe {EXAMPLE_PIPE_ID}: denied"],
        "warnings": [],
        "message": "Pipe fetch failed.",
    }


@pytest.mark.anyio
async def test_validate_ai_automation_prompt_pipe_read_failure_returns_error_only(
    facade_client: PipefyClient,
):
    facade_client.get_pipe_with_preferences.side_effect = RuntimeError("denied")

    result = await facade_client.validate_ai_automation_prompt(
        "1", f"Summarize %{{{FIELD_ID}}}", ["900000002"]
    )

    assert result == {
        "success": False,
        "valid": False,
        "error": "Failed to fetch pipe 1: denied",
    }
