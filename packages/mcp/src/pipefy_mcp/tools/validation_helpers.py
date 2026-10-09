"""Shared validation helpers for MCP tool boundaries (IDs, optional dict args)."""

from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError

from pipefy_mcp.core.tool_error_envelope import tool_error

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def valid_repo_id(value: object) -> bool:
    """Return True if ``value`` looks like a Pipefy repo identifier (Pipe/Table ID).

    GraphQL ``RepoTypes`` cover Pipe and Table; tools accept a non-empty string slug
    or a positive integer. Other types are rejected without raising.
    """
    if isinstance(value, int):
        return value > 0
    if isinstance(value, str):
        return bool(value.strip())
    return False


def _is_non_positive_numeric(s: str) -> bool:
    """True when ``s`` is a numeric string representing zero or a negative number."""
    stripped = s.strip()
    if stripped.startswith("-") and stripped[1:].isdigit():
        return True
    return bool(stripped.isdigit() and int(stripped) <= 0)


def validate_tool_id(
    value: str | int,
    label: str = "id",
) -> tuple[str | None, dict[str, object] | None]:
    """Validate and normalize a Pipefy ID at the tool boundary.

    Returns ``(cleaned_id, None)`` on success or ``(None, error_payload)`` on
    failure.  Handles empty strings, booleans, zero, and negative numbers.

    Callers should **rebind** the parameter to the cleaned value::

        param, err = validate_tool_id(param, "param")

    Discarding the cleaned value (``_, err = ...``) defeats whitespace
    stripping and int→str normalization.

    Args:
        value: Raw ID value from the MCP tool parameter.
        label: Parameter name for the error message (e.g. ``card_id``).
    """
    if isinstance(value, bool) or not valid_repo_id(value):
        return None, tool_error(
            f"Invalid '{label}': provide a non-empty string or positive integer."
        )
    s = str(value).strip() if isinstance(value, int) else value.strip()
    if not s:
        return None, tool_error(f"Invalid '{label}': provide a non-empty ID.")
    if _is_non_positive_numeric(s):
        return None, tool_error(f"Invalid '{label}': provide a positive integer.")
    return s, None


def validate_optional_tool_id(
    value: str | int | None,
    label: str = "id",
) -> tuple[bool, str | None, dict[str, object] | None]:
    """Validate an optional Pipefy ID.  ``None`` passes through.

    Returns ``(ok, cleaned_id_or_none, error_payload_or_none)``.

    Args:
        value: Optional raw ID value.
        label: Parameter name for the error message.
    """
    if value is None:
        return True, None, None
    cleaned, err = validate_tool_id(value, label)
    if err is not None:
        return False, None, err
    return True, cleaned, None


def validate_optional_tool_id_list(
    values: list[str | int] | None,
    label: str = "ids",
) -> tuple[list[str] | None, dict[str, object] | None]:
    """Validate an optional list of Pipefy IDs at the tool boundary.

    ``None`` passes through as ``(None, None)``; a present list must be non-empty
    and every element pass :func:`validate_tool_id`. Returns
    ``(cleaned_ids, error_payload)``.
    """
    if values is None:
        return None, None
    if not values:
        return None, tool_error(
            f"Invalid '{label}': when provided, it must contain at least one ID."
        )
    cleaned: list[str] = []
    for value in values:
        cleaned_id, err = validate_tool_id(value, label)
        if cleaned_id is None:
            return None, err
        cleaned.append(cleaned_id)
    return cleaned, None


def mutation_error_if_not_optional_dict(
    value: Any,
    *,
    arg_name: str,
) -> dict[str, Any] | None:
    """Return a mutation error payload if ``value`` is present but not a mapping.

    MCP callers may send malformed JSON (e.g. list or string); tools should not
    raise ``AttributeError`` from ``.items()`` on those values.

    Args:
        value: Optional ``extra_input``-style argument from the tool boundary.
        arg_name: Parameter name for the error message (e.g. ``extra_input``).

    Returns:
        Error payload dict when validation fails; ``None`` when the value is
        omitted or is already a ``dict``.
    """
    if value is not None and not isinstance(value, dict):
        return tool_error(
            f"Invalid '{arg_name}': provide a JSON object (dict) when supplied."
        )
    return None


def format_validation_error_message(exc: ValidationError) -> str:
    """Render a :class:`~pydantic.ValidationError` as a single agent-friendly line.

    Each error becomes one short clause and the clauses are joined with ``"; "``.
    The output never contains the Pydantic model name, an ``input_value=`` echo of
    the arguments (which may hold secrets), nor an ``errors.pydantic.dev`` URL, so
    it is safe to return to an agent or write to a log. Returns ``""`` when ``exc``
    reports no errors.

    This is the shared renderer behind the MCP tools' argument-validation errors;
    callers wrap the result in their own error-payload builder (and may prefix it,
    e.g. ``Invalid 'condition': ...``).
    """
    clauses: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", ()))
        err_type = err.get("type", "")
        msg = err.get("msg", "")
        if err_type == "value_error":
            # Pydantic renders a custom validator's ValueError as "Value error, <text>";
            # the raw text is in ctx["error"]. Use it so that prefix does not leak, the
            # same way portal_element_validation_error does.
            ctx = err.get("ctx") or {}
            inner = ctx.get("error")
            if inner is not None:
                msg = str(inner)
        if err_type == "missing":
            clauses.append(f"missing required argument '{loc}'")
        elif err_type == "extra_forbidden":
            clauses.append(f"unknown argument '{loc}'")
        elif loc:
            clauses.append(f"{loc}: {msg}")
        else:
            clauses.append(msg)
    return "; ".join(clause for clause in clauses if clause)


__all__ = [
    "UUID_RE",
    "format_validation_error_message",
    "mutation_error_if_not_optional_dict",
    "valid_repo_id",
    "validate_optional_tool_id",
    "validate_tool_id",
]
