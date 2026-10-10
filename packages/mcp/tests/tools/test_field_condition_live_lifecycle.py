"""Exercise the live-test lifecycle with real SDK code and a GraphQL executor fake."""

import pytest
from _mcp_compat import (
    create_connected_server_and_client_session as create_client_session,
)
from _shared.mock_clients import mock_executor
from pipefy_sdk import PipefyClient
from pipefy_sdk.client import Executors
from pipefy_sdk.settings import PipefySettings

from pipefy_mcp.tools.field_condition_tools import FieldConditionTools
from tools.conftest import build_tool_test_server
from tools.field_condition_live_test_support import exercise_field_condition_lifecycle


@pytest.mark.unit
@pytest.mark.anyio
@pytest.mark.parametrize(
    "actual_phase", ["20", None, "10"], ids=["wrong-phase", "missing", "verified"]
)
async def test_live_lifecycle_deletes_returned_condition_before_asserting(
    actual_phase, envelope_flag
):
    calls = []

    async def execute_query(document, variables):
        field = document.document.definitions[0].selection_set.selections[0]
        operation = field.name.value
        calls.append((operation, variables))
        if operation == "phase":
            return {"phase": {"fields": [], "fieldConditions": []}}
        if operation == "createFieldCondition":
            assert variables["input"]["phaseId"] == "10"
            return {"createFieldCondition": {"fieldCondition": {"id": "301"}}}
        if operation == "fieldCondition":
            return {
                "fieldCondition": {
                    "id": "301",
                    "phase": {"id": actual_phase} if actual_phase else None,
                }
            }
        if operation == "deleteFieldCondition":
            return {"deleteFieldCondition": {"success": True}}
        raise AssertionError(f"Unexpected GraphQL operation: {operation}")

    executor = mock_executor(side_effect=execute_query)
    unused = mock_executor(
        side_effect=AssertionError("Only public GraphQL is expected")
    )
    client = PipefyClient.from_executors(
        Executors(public=executor, interfaces=unused, internal=unused),
        settings=PipefySettings(),
    )
    server = build_tool_test_server(
        "Field-condition lifecycle", FieldConditionTools.register, client
    )
    arguments = {
        "phase_id": 10,
        "name": "Disposable rule",
        "condition": {
            "expressions": [
                {
                    "field_address": "101",
                    "operation": "equals",
                    "value": "sentinel",
                    "structure_id": 1,
                }
            ],
            "expressions_structure": [[1]],
        },
        "actions": [{"phaseFieldId": "102", "actionId": "hide"}],
    }
    async with create_client_session(server, raise_exceptions=True) as session:
        if actual_phase == "10":
            payload = await exercise_field_condition_lifecycle(session, arguments)
            assert payload["success"] is True
            assert payload["verified"] is True
        else:
            with pytest.raises(AssertionError) as failure:
                await exercise_field_condition_lifecycle(session, arguments)
            code = (
                "FIELD_CONDITION_WRONG_PHASE"
                if actual_phase
                else "FIELD_CONDITION_NOT_PERSISTED"
            )
            assert code in str(failure.value)

    assert [
        variables
        for operation, variables in calls
        if operation == "deleteFieldCondition"
    ] == [{"input": {"id": "301"}}]
    assert (
        len(
            [operation for operation, _ in calls if operation == "createFieldCondition"]
        )
        == 1
    )
    unused.execute_query.assert_not_awaited()
