"""Pure helpers for filtering card field values against phase/start-form definitions."""

from __future__ import annotations

from typing import Any


def filter_editable_field_definitions(
    field_definitions: list[Any],
) -> list[dict[str, Any]]:
    """Return editable field definitions; missing ``editable`` defaults to True."""
    editable_fields: list[dict[str, Any]] = []
    for field_def in field_definitions:
        if not isinstance(field_def, dict):
            continue
        if field_def.get("editable", True):
            editable_fields.append(field_def)
    return editable_fields


def filter_fields_by_definitions(
    fields: dict[str, Any] | None,
    field_definitions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Keep only ``fields`` keys that match an ``id`` in ``field_definitions``."""
    if not fields:
        return {}
    editable_ids = {
        field_id for field_def in field_definitions if (field_id := field_def.get("id"))
    }
    return {
        field_id: value
        for field_id, value in fields.items()
        if field_id in editable_ids
    }


def skipped_field_ids(
    fields: dict[str, Any],
    kept_fields: dict[str, Any],
) -> list[str]:
    """Field ids present in ``fields`` but dropped by ``filter_fields_by_definitions``."""
    return [field_id for field_id in fields if field_id not in kept_fields]


def phase_fill_no_write_result(
    phase_fields_result: dict[str, Any],
    fields: dict[str, Any] | None,
    field_data: dict[str, Any],
    *,
    phase_id: str | int,
    required_fields_only: bool,
    include_skipped_field_ids: bool = True,
) -> dict[str, Any]:
    """Envelope for a phase fill that will not call ``update_card``.

    Callers pass an empty ``field_data``. ``include_skipped_field_ids`` is false
    when an accepted form already replaced the caller's keys.
    """
    expected_fields = filter_editable_field_definitions(
        phase_fields_result.get("fields", [])
    )
    phase_name = phase_fields_result.get("phase_name") or f"Phase {phase_id}"
    given_fields = fields or {}
    if expected_fields:
        message = (
            "No field values were collected, so nothing was updated. "
            f"Phase '{phase_name}' has {len(expected_fields)} editable "
            "field(s); pass 'fields' keyed by the IDs from "
            "get_phase_fields(phase_id)."
        )
    else:
        read_message = phase_fields_result.get("message")
        if required_fields_only and read_message:
            message = f"{read_message} Nothing was updated."
        elif given_fields:
            message = (
                f"Phase '{phase_name}' has no editable fields; nothing was updated."
            )
        else:
            message = "No fields to update."
    result: dict[str, Any] = {
        "success": True,
        "message": message,
        "phase_id": phase_id,
        "phase_name": phase_name,
    }
    if include_skipped_field_ids:
        result["skipped_field_ids"] = skipped_field_ids(given_fields, field_data)
    return result
