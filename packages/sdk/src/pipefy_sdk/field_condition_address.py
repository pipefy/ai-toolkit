"""Field slugs in a field-condition ``field_address`` and their ``internal_id``.

Pipefy saves a field slug in a field-condition ``field_address`` as sent, while
the schema says it resolves it. A rule saved that way makes card moves in the
pipe fail with a generic error, so the SDK sends the ``internal_id`` instead.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_PATH_SEPARATOR = "."


def _slug_head(field_address: object) -> str | None:
    """Return the first path segment of ``field_address`` when it is not numeric."""
    if not isinstance(field_address, str):
        return None
    head = field_address.strip().split(_PATH_SEPARATOR, 1)[0]
    if not head or head.isdigit():
        return None
    return head


def _expressions(condition: Mapping[str, Any] | None) -> list[Any]:
    expressions = (condition or {}).get("expressions")
    return expressions if isinstance(expressions, list) else []


def field_address_slug_heads(condition: Mapping[str, Any] | None) -> set[str]:
    """Return the non-numeric first segments of the condition's ``field_address`` values.

    An empty set means every address is already a numeric id, so no lookup is needed.
    A field slug made only of digits counts as an id and is sent as is.
    """
    heads: set[str] = set()
    for expression in _expressions(condition):
        if not isinstance(expression, Mapping):
            continue
        head = _slug_head(expression.get("field_address"))
        if head:
            heads.add(head)
    return heads


def internal_ids_by_field_slug(pipe: Mapping[str, Any]) -> dict[str, set[str]]:
    """Map each field slug of a ``get_pipe`` ``pipe`` to the ``internal_id`` values that use it."""
    fields = list(pipe.get("start_form_fields") or [])
    for phase in pipe.get("phases") or []:
        fields.extend(phase.get("fields") or [])
    mapping: dict[str, set[str]] = {}
    for field in fields:
        slug, internal_id = field.get("id"), field.get("internal_id")
        if slug and internal_id is not None:
            mapping.setdefault(str(slug), set()).add(str(internal_id))
    return mapping


def resolve_field_address_slugs(
    condition: Mapping[str, Any], internal_ids_by_slug: Mapping[str, set[str]]
) -> dict[str, Any]:
    """Return a copy of ``condition`` with each field-slug head replaced by its ``internal_id``.

    Only the first segment changes, because the later segments of a connected-field
    path name fields of another pipe. A head that is no field slug of the pipe, such
    as a native card attribute (``title``), stays as sent.

    Raises:
        ValueError: When one slug names more than one field of the pipe.
    """
    expressions = []
    for expression in _expressions(condition):
        head = (
            _slug_head(expression.get("field_address"))
            if isinstance(expression, Mapping)
            else None
        )
        internal_ids = internal_ids_by_slug.get(head or "", set())
        if len(internal_ids) > 1:
            raise ValueError(
                f"field_address slug {head!r} names more than one field "
                f"(internal_id {', '.join(sorted(internal_ids))}); send the "
                "internal_id from get_phase_fields instead of the slug"
            )
        if not internal_ids:
            expressions.append(expression)
            continue
        address = expression["field_address"].strip()
        tail = address[len(head) :]
        expressions.append(
            {**expression, "field_address": f"{next(iter(internal_ids))}{tail}"}
        )
    return {**condition, "expressions": expressions}
