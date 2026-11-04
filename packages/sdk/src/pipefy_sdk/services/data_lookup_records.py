"""Fill in the records search targets of data lookup conditions.

The agent searches the source pipe or table by record, and each condition must
name its target as ``fieldUuid`` (a custom field) or ``attribute`` (a fixed
field such as ``title``). Callers usually know only the field slug, so these
pure functions resolve each slug against the source's field list: a custom
slug gets its uuid and a fixed slug gets its attribute. A slug that names more
than one target fails instead of picking one: Pipefy gives a custom field
labeled "Labels" the fixed slug ``labels``. The Pipefy UI writes the same
shape.

The operator must also fit the field type. ``contains`` matches an item of a
list field. On a text field it returns no records, so ``ilike`` is the
substring match for every other field. The Pipefy UI applies the same rule.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, NamedTuple

from pipefy_sdk.models.knowledge_base import (
    DataLookupAttribute,
    DataLookupCondition,
    DataLookupOperator,
)

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

LIST_FIELD_TYPES: frozenset[str] = frozenset(
    {
        "assignee_select",
        "checklist_horizontal",
        "checklist_vertical",
        "connector",
        "label_select",
    }
)
LIST_FIELD_ATTRIBUTES: frozenset[DataLookupAttribute] = frozenset(
    {DataLookupAttribute.LABELS, DataLookupAttribute.ASSIGNEES}
)

_ProblemKind = Literal[
    "unknown_slug",
    "unknown_uuid",
    "ambiguous",
    "contains_needs_list_field",
    "list_field_needs_contains",
]

_LIST_FIELDS = "a list field (labels, assignees, checklists, connections)"

# Kind, label separator, message. The message order is the order of this table.
_PROBLEM_MESSAGES: tuple[tuple[_ProblemKind, str, str], ...] = (
    (
        "unknown_slug",
        ", ",
        "{labels}: no field with this slug in source {source}. Pass a field slug "
        "of the source pipe or table, or set fieldUuid on the condition.",
    ),
    (
        "unknown_uuid",
        ", ",
        "{labels}: no field with this uuid in source {source}. Set fieldUuid to "
        "the uuid of a field of the source pipe or table, or remove fieldUuid "
        "and pass the field slug.",
    ),
    (
        "ambiguous",
        "; ",
        "{labels} in source {source}. Set fieldUuid on the condition to pick a "
        "custom field, or attribute to pick the fixed field.",
    ),
    (
        "contains_needs_list_field",
        ", ",
        f"{{labels}}: contains works only on {_LIST_FIELDS}. Use ilike for a "
        "substring match, or eq for an exact value.",
    ),
    (
        "list_field_needs_contains",
        ", ",
        f"{{labels}}: {_LIST_FIELDS} takes only the operator contains.",
    ),
)


@dataclass(frozen=True)
class SourceFields:
    """Custom fields of a data lookup source: the uuids of each slug and the type of each uuid."""

    uuids_by_slug: Mapping[str, set[str]] = field(default_factory=dict)
    type_by_uuid: Mapping[str, str] = field(default_factory=dict)


class _Problem(NamedTuple):
    kind: _ProblemKind
    label: str


def needs_source_fields(conditions: Sequence[DataLookupCondition]) -> bool:
    """True when a condition does not set ``attribute``.

    That condition needs the source's fields: a slug to resolve, or a
    ``fieldUuid`` whose field type decides which operators it takes.
    """
    return any(c.attribute is None for c in conditions)


def source_fields_from_response(
    source_fields_response: Mapping[str, Any], source_repo_id: str
) -> SourceFields:
    """Read the custom fields of the source from ``GET_DATA_LOOKUP_SOURCE_FIELDS_QUERY``.

    Takes start form fields (a table's fields come back here) and the fields of
    every phase. A slug that repeats across phases maps to more than one uuid.

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
    uuids_by_slug: dict[str, set[str]] = {}
    type_by_uuid: dict[str, str] = {}
    for source_field in _all_fields(sources):
        slug, uuid = source_field.get("id"), source_field.get("uuid")
        if slug and uuid:
            uuids_by_slug.setdefault(slug, set()).add(uuid)
            type_by_uuid[uuid] = source_field.get("type") or ""
    return SourceFields(uuids_by_slug=uuids_by_slug, type_by_uuid=type_by_uuid)


def _all_fields(sources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    fields: list[Mapping[str, Any]] = []
    for source in sources:
        fields.extend(source.get("start_form_fields") or [])
        for phase in source.get("phases") or []:
            fields.extend(phase.get("fields") or [])
    return fields


def to_records_conditions(
    conditions: Sequence[DataLookupCondition],
    source: SourceFields,
    source_repo_id: str,
) -> list[DataLookupCondition]:
    """Return the conditions with ``fieldUuid`` or ``attribute`` set on each one.

    A condition that sets ``attribute`` stays as it is. A condition that sets
    ``fieldUuid`` stays when the uuid is a field of the source. Any other
    condition needs a slug that names exactly one target: a fixed field, or
    one custom field of the source. Then the operator must fit the field:
    ``contains`` on a list field, and ``eq``, ``not_eq``, or ``ilike`` on any
    other field.

    Raises:
        ValueError: When a condition breaks a rule, naming every such
            condition by its index.
    """
    filled: list[DataLookupCondition] = []
    problems: list[_Problem] = []
    for i, condition in enumerate(conditions):
        targeted = _with_target(i, condition, source)
        if isinstance(targeted, _Problem):
            problems.append(targeted)
            continue
        filled.append(targeted)
        mismatch = _operator_mismatch(i, targeted, source)
        if mismatch is not None:
            problems.append(mismatch)
    _raise_for_problems(problems, source_repo_id)
    return filled


def _with_target(
    i: int, condition: DataLookupCondition, source: SourceFields
) -> DataLookupCondition | _Problem:
    if condition.attribute is not None:
        return condition
    if condition.field_uuid is not None:
        if condition.field_uuid in source.type_by_uuid:
            return condition
        return _Problem(
            "unknown_uuid", f"conditions[{i}].fieldUuid {condition.field_uuid!r}"
        )
    label = f"conditions[{i}].field {condition.field!r}"
    uuids = source.uuids_by_slug.get(condition.field, set())
    attribute = FIXED_FIELD_ATTRIBUTES.get(condition.field)
    if attribute is not None and uuids:
        return _Problem(
            "ambiguous",
            f"{label} is both the fixed field {attribute.value} and a custom field",
        )
    if len(uuids) > 1:
        return _Problem("ambiguous", f"{label} matches {len(uuids)} custom fields")
    if attribute is not None:
        return condition.model_copy(update={"attribute": attribute})
    if uuids:
        (uuid,) = uuids
        return condition.model_copy(update={"field_uuid": uuid})
    return _Problem("unknown_slug", label)


def _is_list_field(condition: DataLookupCondition, source: SourceFields) -> bool:
    if condition.attribute is not None:
        return condition.attribute in LIST_FIELD_ATTRIBUTES
    return source.type_by_uuid.get(condition.field_uuid or "") in LIST_FIELD_TYPES


def _operator_mismatch(
    i: int, condition: DataLookupCondition, source: SourceFields
) -> _Problem | None:
    on_list_field = _is_list_field(condition, source)
    if on_list_field == (condition.operator == DataLookupOperator.CONTAINS):
        return None
    label = (
        f"conditions[{i}].operator {condition.operator.value!r} "
        f"on field {condition.field!r}"
    )
    if on_list_field:
        return _Problem("list_field_needs_contains", label)
    return _Problem("contains_needs_list_field", label)


def _raise_for_problems(problems: list[_Problem], source_repo_id: str) -> None:
    sentences: list[str] = []
    for kind, separator, message in _PROBLEM_MESSAGES:
        labels = [p.label for p in problems if p.kind == kind]
        if labels:
            sentences.append(
                message.format(labels=separator.join(labels), source=source_repo_id)
            )
    if sentences:
        raise ValueError(" ".join(sentences))
