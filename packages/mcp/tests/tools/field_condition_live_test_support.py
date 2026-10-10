"""Field-condition live-test lifecycle, including partial-create cleanup."""

from tools.conftest import extract_tool_payload
from tools.destructive_confirm_test_support import confirm_after_preview


async def exercise_field_condition_lifecycle(session, arguments):
    """Create a condition, delete it, then report the create verification result."""
    condition_id = None
    try:
        result = await session.call_tool("create_field_condition", arguments)
        created = extract_tool_payload(result)
        details = (created.get("error") or {}).get("details") or {}
        condition_id = created.get("condition_id") or details.get("condition_id")
    finally:
        if condition_id:
            deleted = await confirm_after_preview(
                session,
                "delete_field_condition",
                {"condition_id": condition_id, "debug": True},
            )
            assert deleted.get("success") is True, deleted
    assert result.is_error is False, created
    assert condition_id, created
    assert created.get("success") is True, created
    assert created.get("verified") is True, created
    return created
