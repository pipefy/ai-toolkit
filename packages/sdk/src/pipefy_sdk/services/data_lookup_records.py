"""Fill in the records search targets of data lookup conditions.

The agent searches the source pipe or table by record, and each condition must
name its target as ``fieldUuid`` (a custom field) or ``attribute`` (a fixed
field such as ``title``). Callers usually know only the field slug, so these
pure functions resolve each slug against the source's field list: a custom
slug gets its uuid and a fixed slug gets its attribute. A slug that names more
than one target fails instead of picking one: Pipefy gives a custom field
labeled "Labels" the fixed slug ``labels``. The Pipefy UI writes the same
shape.
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


def needs_source_fields(conditions: Sequence[DataLookupCondition]) -> bool:
    """True when a condition has neither ``fieldUuid`` nor ``attribute``."""
    return any(not _has_target(c) for c in conditions)


def field_uuids_by_slug(
    source_fields_response: Mapping[str, Any], source_repo_id: str
) -> dict[str, set[str]]:
    """Map each field slug of the source to its uuids.

    Reads the response of ``GET_DATA_LOOKUP_SOURCE_FIELDS_QUERY``: start form
    fields (a table's fields come back here) and the fields of every phase. A
    slug that repeats across phases maps to more than one uuid.

    Raises:
        ValueError: When the response holds no source, so the id is not a pipe
            or table that the credential can read.
    """
    sources = [s for s in source_fields_response.get("pipes") or [] if s]
    if not sources:
        raise ValueError(
            f"source_repo_id {source_repo_id!r}: no pipe or table with this id is "
            "readable with this credential. Pass a numeric pipe ID or a table "
            "internal_id."
        )
    uuids: dict[str, set[str]] = {}
    for source in sources:
        fields = list(source.get("start_form_fields") or [])
        for phase in source.get("phases") or []:
            fields.extend(phase.get("fields") or [])
        for field in fields:
            slug, uuid = field.get("id"), field.get("uuid")
            if slug and uuid:
                uuids.setdefault(slug, set()).add(uuid)
    return uuids


def to_records_conditions(
    conditions: Sequence[DataLookupCondition],
    field_uuids: Mapping[str, set[str]],
    source_repo_id: str,
) -> list[DataLookupCondition]:
    """Return the conditions with ``fieldUuid`` or ``attribute`` set on each one.

    A condition that already names a target is kept as it is. Any other
    condition needs a slug that names exactly one target: a fixed field, or
    one custom field of the source.

    Raises:
        ValueError: When a slug names no target or more than one, naming every
            such condition.
    """
    filled: list[DataLookupCondition] = []
    unknown: list[str] = []
    ambiguous: list[str] = []
    for i, condition in enumerate(conditions):
        label = f"conditions[{i}].field {condition.field!r}"
        uuids = field_uuids.get(condition.field, set())
        attribute = FIXED_FIELD_ATTRIBUTES.get(condition.field)
        if _has_target(condition):
            filled.append(condition)
        elif attribute is not None and uuids:
            ambiguous.append(
                f"{label} is both the fixed field {attribute.value} and a custom field"
            )
        elif len(uuids) > 1:
            ambiguous.append(f"{label} matches {len(uuids)} custom fields")
        elif attribute is not None:
            filled.append(condition.model_copy(update={"attribute": attribute}))
        elif uuids:
            (uuid,) = uuids
            filled.append(condition.model_copy(update={"field_uuid": uuid}))
        else:
            unknown.append(label)
    _raise_for_unresolved(unknown, ambiguous, source_repo_id)
    return filled


def _raise_for_unresolved(
    unknown: list[str], ambiguous: list[str], source_repo_id: str
) -> None:
    problems: list[str] = []
    if unknown:
        problems.append(
            f"{', '.join(unknown)}: no field with this slug in source "
            f"{source_repo_id}. Pass a field slug of the source pipe or table, "
            "or set fieldUuid on the condition."
        )
    if ambiguous:
        problems.append(
            f"{'; '.join(ambiguous)} in source {source_repo_id}. Set fieldUuid on "
            "the condition to pick a custom field, or attribute to pick the "
            "fixed field."
        )
    if problems:
        raise ValueError(" ".join(problems))
