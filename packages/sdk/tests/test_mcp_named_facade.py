"""Facade-level tests: MCP-named methods on ``PipefyClient``."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from _shared.fixture_ids import (
    EXAMPLE_FIELD_INTERNAL_ID,
    EXAMPLE_NUMERIC_ORG_ID,
    EXAMPLE_ORG_UUID,
    EXAMPLE_PHASE_ID,
    EXAMPLE_PIPE_ID,
)

from pipefy_sdk import PipefyClient
from pipefy_sdk.models.form import MalformedFieldDefinitionError

AI_ROW = {"id": "1", "name": "AI", "action_id": "generate_with_ai"}
MOVE_ROW = {"id": "2", "name": "Move", "action_id": "move_single_card"}
AUTOMATION_RECORD = {
    "id": "501",
    "name": "AI rule",
    "action_id": "generate_with_ai",
}
MIXED_PAGE = {
    "nodes": [AI_ROW, MOVE_ROW],
    "totalCount": 2,
    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
}
MUTATION_RESULT = {"removeMembersFromPipe": {"success": True}}
REMAINING_USER_ID = EXAMPLE_FIELD_INTERNAL_ID
STILL_PRESENT_WARNING = (
    f"API returned success but member(s) [{REMAINING_USER_ID}] are still present in the pipe. "
    "They may have org-level permissions that override pipe-level removal."
)
CARD_ID = "99"
PHASE_NAME = "Review"
TWO_EDITABLE_FIELDS = [
    {"id": "status", "editable": True},
    {"id": "title", "editable": True},
]
NON_EDITABLE_FIELDS = [
    {"id": "readonly", "editable": False},
    {"id": "locked", "editable": False},
]
UPDATE_CARD_RESULT = {"updateFieldsValues": {"success": True}}
MALFORMED_PHASE_FIELDS = MalformedFieldDefinitionError(
    "Cannot return phase fields: 1 field definition(s) from Pipefy are "
    "missing required 'id' or 'type'. The pipe configuration may be "
    "incomplete or unsupported."
)


def _phase_fields(fields: list[dict]) -> dict:
    return {
        "phase_id": EXAMPLE_PHASE_ID,
        "phase_name": PHASE_NAME,
        "fields": fields,
    }


def _collected_nothing_message(editable_count: int) -> str:
    return (
        "No field values were collected, so nothing was updated. "
        f"Phase '{PHASE_NAME}' has {editable_count} editable field(s); "
        "pass 'fields' keyed by the IDs from get_phase_fields(phase_id)."
    )


@pytest.fixture
def facade_client() -> PipefyClient:
    client = PipefyClient.__new__(PipefyClient)
    client.get_automation = AsyncMock(return_value=AUTOMATION_RECORD)
    client.get_automations = AsyncMock(return_value=MIXED_PAGE)
    client.delete_automation = AsyncMock(return_value={"success": True})
    client.remove_members_from_pipe = AsyncMock(return_value=MUTATION_RESULT)
    client.get_pipe_members = AsyncMock(return_value={"pipe": {"members": []}})
    client.get_phase_fields = AsyncMock(return_value=_phase_fields(TWO_EDITABLE_FIELDS))
    client.update_card = AsyncMock(return_value=UPDATE_CARD_RESULT)
    return client


@pytest.mark.anyio
async def test_get_ai_automation_forwards_id_and_returns_record(
    facade_client: PipefyClient,
):
    record = await facade_client.get_ai_automation("501")

    assert record == AUTOMATION_RECORD
    facade_client.get_automation.assert_awaited_once_with("501")


@pytest.mark.anyio
async def test_get_ai_automations_filters_nodes_keeps_mixed_page_pagination(
    facade_client: PipefyClient,
):
    page = await facade_client.get_ai_automations(
        EXAMPLE_PIPE_ID,
        organization_id=EXAMPLE_NUMERIC_ORG_ID,
        first=10,
        after="cursor-0",
    )

    facade_client.get_automations.assert_awaited_once_with(
        organization_id=EXAMPLE_NUMERIC_ORG_ID,
        pipe_id=EXAMPLE_PIPE_ID,
        first=10,
        after="cursor-0",
    )
    assert page["nodes"] == [AI_ROW]
    assert page["totalCount"] == MIXED_PAGE["totalCount"]
    assert page["pageInfo"] == MIXED_PAGE["pageInfo"]


@pytest.mark.anyio
async def test_delete_ai_automation_forwards_to_delete_automation(
    facade_client: PipefyClient,
):
    result = await facade_client.delete_ai_automation("501")

    assert result == {"success": True}
    facade_client.delete_automation.assert_awaited_once_with("501")


@pytest.mark.anyio
async def test_remove_member_from_pipe_returns_data_and_null_warning_when_gone(
    facade_client: PipefyClient,
):
    result = await facade_client.remove_member_from_pipe(
        EXAMPLE_PIPE_ID, [REMAINING_USER_ID]
    )

    facade_client.remove_members_from_pipe.assert_awaited_once_with(
        EXAMPLE_PIPE_ID, [REMAINING_USER_ID]
    )
    assert result == {"data": MUTATION_RESULT, "warning": None}


@pytest.mark.anyio
async def test_remove_member_from_pipe_returns_warning_when_member_still_present(
    facade_client: PipefyClient,
):
    facade_client.get_pipe_members.return_value = {
        "pipe": {
            "members": [
                {"user": {"id": REMAINING_USER_ID, "uuid": EXAMPLE_ORG_UUID}},
            ]
        }
    }

    result = await facade_client.remove_member_from_pipe(
        EXAMPLE_PIPE_ID, [REMAINING_USER_ID]
    )

    facade_client.remove_members_from_pipe.assert_awaited_once_with(
        EXAMPLE_PIPE_ID, [REMAINING_USER_ID]
    )
    assert result == {"data": MUTATION_RESULT, "warning": STILL_PRESENT_WARNING}


@pytest.mark.anyio
async def test_fill_card_phase_fields_writes_one_editable_and_skips_unknown(
    facade_client: PipefyClient,
):
    result = await facade_client.fill_card_phase_fields(
        CARD_ID,
        EXAMPLE_PHASE_ID,
        {"status": "done", "unknown": "x"},
    )

    facade_client.get_phase_fields.assert_awaited_once_with(
        EXAMPLE_PHASE_ID, required_only=False
    )
    facade_client.update_card.assert_awaited_once_with(
        CARD_ID,
        field_updates=[{"field_id": "status", "value": "done"}],
    )
    assert result == {**UPDATE_CARD_RESULT, "skipped_field_ids": ["unknown"]}


@pytest.mark.anyio
async def test_fill_card_phase_fields_write_omits_skipped_ids_when_none_dropped(
    facade_client: PipefyClient,
):
    result = await facade_client.fill_card_phase_fields(
        CARD_ID,
        EXAMPLE_PHASE_ID,
        {"status": "done"},
    )

    facade_client.get_phase_fields.assert_awaited_once_with(
        EXAMPLE_PHASE_ID, required_only=False
    )
    facade_client.update_card.assert_awaited_once_with(
        CARD_ID,
        field_updates=[{"field_id": "status", "value": "done"}],
    )
    assert result == UPDATE_CARD_RESULT
    assert "skipped_field_ids" not in result


@pytest.mark.anyio
async def test_fill_card_phase_fields_skips_write_when_only_unknown_keys(
    facade_client: PipefyClient,
):
    result = await facade_client.fill_card_phase_fields(
        CARD_ID,
        EXAMPLE_PHASE_ID,
        {"unknown": "x", "other": "y"},
    )

    facade_client.get_phase_fields.assert_awaited_once_with(
        EXAMPLE_PHASE_ID, required_only=False
    )
    facade_client.update_card.assert_not_awaited()
    assert result == {
        "success": True,
        "message": _collected_nothing_message(2),
        "phase_id": EXAMPLE_PHASE_ID,
        "phase_name": PHASE_NAME,
        "skipped_field_ids": ["unknown", "other"],
    }


@pytest.mark.anyio
@pytest.mark.parametrize("fields", [None, {}])
async def test_fill_card_phase_fields_skips_write_when_fields_empty_or_none(
    facade_client: PipefyClient,
    fields: dict | None,
):
    result = await facade_client.fill_card_phase_fields(
        CARD_ID, EXAMPLE_PHASE_ID, fields
    )

    facade_client.get_phase_fields.assert_awaited_once_with(
        EXAMPLE_PHASE_ID, required_only=False
    )
    facade_client.update_card.assert_not_awaited()
    assert result == {
        "success": True,
        "message": _collected_nothing_message(2),
        "phase_id": EXAMPLE_PHASE_ID,
        "phase_name": PHASE_NAME,
        "skipped_field_ids": [],
    }


@pytest.mark.anyio
async def test_fill_card_phase_fields_skips_write_when_no_editable_fields(
    facade_client: PipefyClient,
):
    facade_client.get_phase_fields.return_value = _phase_fields(NON_EDITABLE_FIELDS)

    result = await facade_client.fill_card_phase_fields(
        CARD_ID,
        EXAMPLE_PHASE_ID,
        {"readonly": "nope", "locked": "nope"},
    )

    facade_client.get_phase_fields.assert_awaited_once_with(
        EXAMPLE_PHASE_ID, required_only=False
    )
    facade_client.update_card.assert_not_awaited()
    assert result == {
        "success": True,
        "message": (
            f"Phase '{PHASE_NAME}' has no editable fields; nothing was updated."
        ),
        "phase_id": EXAMPLE_PHASE_ID,
        "phase_name": PHASE_NAME,
        "skipped_field_ids": ["readonly", "locked"],
    }


@pytest.mark.anyio
async def test_fill_card_phase_fields_skips_write_when_required_only_finds_none(
    facade_client: PipefyClient,
):
    facade_client.get_phase_fields.return_value = {
        "phase_id": EXAMPLE_PHASE_ID,
        "phase_name": PHASE_NAME,
        "fields": [],
        "message": "This phase has no required fields.",
    }

    result = await facade_client.fill_card_phase_fields(
        CARD_ID,
        EXAMPLE_PHASE_ID,
        {"status": "done"},
        required_fields_only=True,
    )

    facade_client.get_phase_fields.assert_awaited_once_with(
        EXAMPLE_PHASE_ID, required_only=True
    )
    facade_client.update_card.assert_not_awaited()
    assert result == {
        "success": True,
        "message": "This phase has no required fields. Nothing was updated.",
        "phase_id": EXAMPLE_PHASE_ID,
        "phase_name": PHASE_NAME,
        "skipped_field_ids": ["status"],
    }


@pytest.mark.anyio
async def test_fill_card_phase_fields_skips_write_when_required_only_fields_are_not_editable(
    facade_client: PipefyClient,
):
    facade_client.get_phase_fields.return_value = _phase_fields(
        [{"id": EXAMPLE_FIELD_INTERNAL_ID, "required": True, "editable": False}]
    )

    result = await facade_client.fill_card_phase_fields(
        CARD_ID,
        EXAMPLE_PHASE_ID,
        {EXAMPLE_FIELD_INTERNAL_ID: "x"},
        required_fields_only=True,
    )

    facade_client.get_phase_fields.assert_awaited_once_with(
        EXAMPLE_PHASE_ID, required_only=True
    )
    facade_client.update_card.assert_not_awaited()
    assert result == {
        "success": True,
        "message": (
            f"Phase '{PHASE_NAME}' has no editable fields; nothing was updated."
        ),
        "phase_id": EXAMPLE_PHASE_ID,
        "phase_name": PHASE_NAME,
        "skipped_field_ids": [EXAMPLE_FIELD_INTERNAL_ID],
    }


@pytest.mark.anyio
async def test_fill_card_phase_fields_no_fields_to_update_when_empty_and_none_editable(
    facade_client: PipefyClient,
):
    facade_client.get_phase_fields.return_value = _phase_fields(NON_EDITABLE_FIELDS)

    result = await facade_client.fill_card_phase_fields(CARD_ID, EXAMPLE_PHASE_ID, {})

    facade_client.get_phase_fields.assert_awaited_once_with(
        EXAMPLE_PHASE_ID, required_only=False
    )
    facade_client.update_card.assert_not_awaited()
    assert result == {
        "success": True,
        "message": "No fields to update.",
        "phase_id": EXAMPLE_PHASE_ID,
        "phase_name": PHASE_NAME,
        "skipped_field_ids": [],
    }


@pytest.mark.anyio
async def test_fill_card_phase_fields_forwards_required_fields_only(
    facade_client: PipefyClient,
):
    await facade_client.fill_card_phase_fields(
        CARD_ID,
        EXAMPLE_PHASE_ID,
        {"status": "done"},
        required_fields_only=True,
    )

    facade_client.get_phase_fields.assert_awaited_once_with(
        EXAMPLE_PHASE_ID, required_only=True
    )


@pytest.mark.anyio
async def test_fill_card_phase_fields_propagates_malformed_field_definition(
    facade_client: PipefyClient,
):
    facade_client.get_phase_fields.side_effect = MALFORMED_PHASE_FIELDS

    with pytest.raises(MalformedFieldDefinitionError, match="return phase fields"):
        await facade_client.fill_card_phase_fields(
            CARD_ID, EXAMPLE_PHASE_ID, {"status": "done"}
        )

    facade_client.get_phase_fields.assert_awaited_once()
    facade_client.update_card.assert_not_awaited()
