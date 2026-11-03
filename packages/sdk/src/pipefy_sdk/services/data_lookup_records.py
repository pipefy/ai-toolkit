"""Fill in the records search targets of data lookup conditions.

The agent searches the source pipe or table by record, and each condition must
name its target as ``fieldUuid`` (a custom field) or ``attribute`` (a fixed
field such as ``title``). Callers usually know only the field slug, so these
pure functions derive the attribute from a fixed slug and map a custom slug to
its uuid from the source's field list. The Pipefy UI writes the same shape.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pipefy_sdk.models.knowledge_base import DataLookupAttribute, DataLookupCondition

RECORDS_SEARCH_QUERY = "records"

FIXED_FIELD_ATTRIBUTES: dict[str, DataLookupAttribute] = {
    "id": DataLookupAttribute.ID,
    "title": DataLookupAttribute.TITLE,
    "created_by": DataLookupAttribute.CREATOR,
    "created_at": DataLookupAttribute.CREATED_AT,
    "due_date": DataLookupAttribute.DUE_DATE,
    "finished_at": DataLookupAttribute.FINISHED_AT,
    "current_phase": DataLookupAttribute.CURRENT_PHASE,
    "labels": DataLookupAttribute.LABELS,
    "assignees": DataLookupAttribute.ASSIGNEES,
}


def _has_target(condition: DataLookupCondition) -> bool:
    return condition.field_uuid is not None or condition.attribute is not None


def needs_field_uuids(conditions: Sequence[DataLookupCondition]) -> bool:
    """True when a condition targets a custom field and has no ``fieldUuid`` yet."""
    return any(
        not _has_target(c) and c.field not in FIXED_FIELD_ATTRIBUTES for c in conditions
    )


def field_uuids_by_slug(source_fields_response: Mapping[str, Any]) -> dict[str, str]:
    """Map each field slug of the source to its uuid.

    Reads the response of ``GET_DATA_LOOKUP_SOURCE_FIELDS_QUERY``: start form
    fields (a table's fields come back here) and the fields of every phase.
    """
    uuids: dict[str, str] = {}
    for source in source_fields_response.get("pipes") or []:
        fields = list(source.get("start_form_fields") or [])
        for phase in source.get("phases") or []:
            fields.extend(phase.get("fields") or [])
        for field in fields:
            slug, uuid = field.get("id"), field.get("uuid")
            if isinstance(slug, str) and isinstance(uuid, str):
                uuids[slug] = uuid
    return uuids


def to_records_conditions(
    conditions: Sequence[DataLookupCondition],
    field_uuids: Mapping[str, str],
    source_repo_id: str,
) -> list[DataLookupCondition]:
    """Return the conditions with ``fieldUuid`` or ``attribute`` set on each one.

    A condition that already names a target is kept as it is. A fixed slug gets
    its attribute, and a custom slug gets its uuid from ``field_uuids``.

    Raises:
        ValueError: When a custom slug is not a field of the source, naming
            every such condition.
    """
    filled: list[DataLookupCondition] = []
    unknown: list[str] = []
    for i, condition in enumerate(conditions):
        if _has_target(condition):
            filled.append(condition)
        elif condition.field in FIXED_FIELD_ATTRIBUTES:
            attribute = FIXED_FIELD_ATTRIBUTES[condition.field]
            filled.append(condition.model_copy(update={"attribute": attribute}))
        elif condition.field in field_uuids:
            uuid = field_uuids[condition.field]
            filled.append(condition.model_copy(update={"field_uuid": uuid}))
        else:
            unknown.append(f"conditions[{i}].field {condition.field!r}")
    if unknown:
        raise ValueError(
            f"{', '.join(unknown)}: no field with this slug in source "
            f"{source_repo_id}. Pass a field slug of the source pipe or table, "
            "or set fieldUuid on the condition."
        )
    return filled
