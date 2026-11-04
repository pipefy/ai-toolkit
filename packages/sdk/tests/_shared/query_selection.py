"""Read the field names a ``gql()`` query selects at a given path."""

from __future__ import annotations

from typing import Any


def selected_field_names(query: Any, *path: str) -> set[str]:
    """Names selected under ``path`` in the query's first operation."""
    node = query.document.definitions[0]
    for name in path:
        node = next(s for s in node.selection_set.selections if s.name.value == name)
    return {s.name.value for s in node.selection_set.selections}
