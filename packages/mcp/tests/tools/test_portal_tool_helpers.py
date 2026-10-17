"""Tests for portal MCP tool helpers."""

from __future__ import annotations

import pytest
from pipefy_sdk import PipefyGraphQLError
from pipefy_sdk.exceptions import PortalPermissionError
from pipefy_sdk.models.portal import DeletePortalElementInput

from pipefy_mcp.tools.portal_tool_helpers import (
    finalize_internal_api_mutation,
    map_portal_error_to_message,
    plan_portal_element_delete_confirmation,
    validate_portal_page_index,
    validate_sort_page_ids_no_duplicates,
)

_PORTAL_PERMISSION_MSG = (
    "Permission denied. Request organization permissions such as "
    "`create_portal` or `manage_portals` from your admin. If you already have "
    "them, writing to an existing portal also needs you to be its admin: join it "
    "once with the Interfaces `joinAsAdmin` mutation, which the toolkit does not "
    "expose."
)


@pytest.mark.unit
def test_map_portal_error_returns_portal_permission_message() -> None:
    """Pre-mapped SDK permission errors are returned without substring heuristics."""
    exc = PortalPermissionError(_PORTAL_PERMISSION_MSG)
    assert map_portal_error_to_message(exc) == _PORTAL_PERMISSION_MSG


@pytest.mark.unit
def test_map_portal_error_blank_permission_message_uses_fallback():
    message = map_portal_error_to_message(PortalPermissionError("  "))
    assert "create_portal" in message
    assert "manage_portals" in message
    assert "joinAsAdmin" in message
    assert "Try again" not in message


@pytest.mark.unit
def test_map_portal_error_permission_denied_code_points_to_join_as_admin():
    """An unmapped PERMISSION_DENIED gets the same guidance as the SDK's message."""
    exc = PipefyGraphQLError(
        [{"message": "denied", "extensions": {"code": "PERMISSION_DENIED"}}]
    )
    message = map_portal_error_to_message(exc)
    assert "manage_portals" in message
    assert "joinAsAdmin" in message


@pytest.mark.unit
def test_map_portal_error_preserves_non_blank_permission_message():
    assert (
        map_portal_error_to_message(PortalPermissionError("real permission text"))
        == "real permission text"
    )


@pytest.mark.unit
def test_map_portal_error_blank_transport_uses_write_fallback_by_default() -> None:
    message = map_portal_error_to_message(RuntimeError("  "))
    assert "Portal operation failed." in message
    assert "do not blind-retry" in message


@pytest.mark.unit
def test_map_portal_error_blank_transport_honors_read_empty_fallback() -> None:
    message = map_portal_error_to_message(
        RuntimeError(""), empty_fallback="Portal request failed."
    )
    assert message == "Portal request failed."
    assert "do not blind-retry" not in message


@pytest.mark.unit
@pytest.mark.parametrize("exc_message", ["", "   "])
def test_map_portal_error_whitespace_permission_denied_uses_guidance(
    exc_message: str,
) -> None:
    exc = PipefyGraphQLError(
        [
            {
                "message": exc_message,
                "extensions": {"code": "PERMISSION_DENIED"},
            }
        ]
    )
    message = map_portal_error_to_message(exc, empty_fallback="Portal request failed.")
    assert "create_portal" in message
    assert "manage_portals" in message


@pytest.mark.unit
def test_map_portal_error_whitespace_graphql_message_uses_empty_fallback() -> None:
    """Whitespace-only GraphQL messages must not bypass empty_fallback.

    Empty ``message`` is already substituted to ``Unknown error`` when
    ``PipefyGraphQLError`` is constructed; whitespace stays truthy there and
    used to leak through ``extract_error_strings`` before the strip fix.
    """
    message = map_portal_error_to_message(
        PipefyGraphQLError([{"message": "   "}]),
        empty_fallback="Portal request failed.",
    )
    assert message == "Portal request failed."


@pytest.mark.unit
def test_map_portal_error_permission_denied_transport_query_error() -> None:
    """GraphQL PERMISSION_DENIED codes map to portal permission guidance."""
    exc = PipefyGraphQLError([{"message": "forbidden"}])
    exc.errors = [{"extensions": {"code": "PERMISSION_DENIED"}}]
    assert "create_portal" in map_portal_error_to_message(exc)
    assert "manage_portals" in map_portal_error_to_message(exc)


@pytest.mark.unit
def test_map_portal_error_permission_denied_internal_api() -> None:
    """A PERMISSION_DENIED GraphQL error maps to portal permission guidance."""
    exc = PipefyGraphQLError(
        [
            {
                "message": "User denied",
                "extensions": {
                    "code": "PERMISSION_DENIED",
                    "correlation_id": "abc-123",
                },
            }
        ]
    )
    message = map_portal_error_to_message(exc)
    assert "create_portal" in message or "manage_portals" in message


@pytest.mark.unit
def test_map_portal_error_non_permission_internal_api_returns_clean_message() -> None:
    """A non-permission GraphQL error surfaces its clean message (no markers)."""
    exc = PipefyGraphQLError(
        [
            {
                "message": "Bad request",
                "extensions": {"code": "BAD_REQUEST", "correlation_id": "abc-123"},
            }
        ]
    )
    assert map_portal_error_to_message(exc) == "Bad request"


@pytest.mark.unit
@pytest.mark.parametrize("index", [-1, True])
def test_validate_portal_page_index_rejects_invalid(index: int | bool) -> None:
    err = validate_portal_page_index(index)  # type: ignore[arg-type]
    assert err is not None
    assert err["error"]["code"] == "INVALID_ARGUMENTS"
    assert "index" in str(err["error"]["message"]).lower()


@pytest.mark.unit
def test_validate_portal_page_index_accepts_zero_and_none() -> None:
    assert validate_portal_page_index(None) is None
    assert validate_portal_page_index(0) is None


@pytest.mark.unit
def test_finalize_internal_api_mutation_treats_explicit_null_as_failure() -> None:
    """Explicit null mutation payloads must not raise AttributeError on .get('success')."""
    payload = finalize_internal_api_mutation(
        {"updateSubPortalElement": None},
        "updateSubPortalElement",
        "mutation failed",
    )
    assert payload["success"] is False
    assert "mutation failed" in str(payload["error"]["message"])


@pytest.mark.unit
def test_validate_sort_page_ids_no_duplicates_rejects_dupes() -> None:
    err = validate_sort_page_ids_no_duplicates(["a", "a"])
    assert err is not None
    assert "duplicate" in str(err["error"]["message"]).lower()


def _delete_input(layout=None):
    return DeletePortalElementInput(element_id="el-1", page_id="page-1", layout=layout)


@pytest.mark.unit
def test_delete_confirmation_without_layout_binds_element_and_page_only() -> None:
    plan = plan_portal_element_delete_confirmation(_delete_input())
    assert plan.resource_identity == {"element_id": "el-1", "page_id": "page-1"}
    assert plan.resource_descriptor == (
        "portal element (UUID: el-1) on page (UUID: page-1)"
    )


@pytest.mark.unit
def test_delete_confirmation_with_layout_names_the_grid_rewrite() -> None:
    plan = plan_portal_element_delete_confirmation(
        _delete_input([{"id": "row-1", "type": "row", "children": []}])
    )
    assert "replacing that page's layout (1 row sent)" in plan.resource_descriptor


@pytest.mark.unit
def test_delete_confirmation_binds_the_exact_layout_rows() -> None:
    """A token previewed for one grid must not confirm a delete that writes another."""
    row_a = {"id": "row-1", "type": "row", "children": ["el-2"]}
    row_b = {"id": "row-2", "type": "row", "children": ["el-3"]}
    no_layout = plan_portal_element_delete_confirmation(_delete_input())
    empty = plan_portal_element_delete_confirmation(_delete_input([]))
    ordered = plan_portal_element_delete_confirmation(_delete_input([row_a, row_b]))
    reordered = plan_portal_element_delete_confirmation(_delete_input([row_b, row_a]))
    identities = [
        plan.resource_identity for plan in (no_layout, empty, ordered, reordered)
    ]
    assert len({tuple(sorted(identity.items())) for identity in identities}) == 4
