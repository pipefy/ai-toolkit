"""Payload builders and error mappers for portal MCP tools.

``unpublish_sub_portal`` uses internal_api ``updateSubPortalElement`` with
``subPortalUuid: null`` (not ``deleteSubPortalElement``): live integration
confirms ``get_portal`` -> ``subPortals[].published`` flips to false. CLI
``sub-portal detach`` calls ``deleteSubPortalElement`` to remove wiring only.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pipefy_sdk import PipefyGraphQLError
from pipefy_sdk.exceptions import (
    HtmlValidationError,
    HtmlViolation,
    PortalPermissionError,
)
from pipefy_sdk.models.portal import DeletePortalElementInput
from pydantic import ValidationError

from pipefy_mcp.core.tool_error_envelope import tool_error
from pipefy_mcp.tools.destructive_confirmation_token import digest_identity_value
from pipefy_mcp.tools.graphql_error_helpers import (
    ensure_non_empty_error_message,
    extract_error_strings,
    extract_graphql_error_codes,
)
from pipefy_mcp.tools.introspection_tool_helpers import (
    build_error_payload,
    build_success_payload,
)
from pipefy_mcp.tools.validation_helpers import validate_tool_id

_PORTAL_PERMISSION_GUIDANCE = (
    "Permission denied. Request organization permissions such as "
    "`create_portal` or `manage_portals` from your admin."
)
_PORTAL_OPERATION_FAILED = (
    "Portal operation failed. Re-read portal state before retrying; do not blind-retry."
)


def _html_violation_line(violation: HtmlViolation) -> str:
    """One violation as ``- CODE at selector[attribute]: message``."""
    location = violation.selector or ""
    if violation.attribute:
        location += f"[{violation.attribute}]"
    location_clause = f" at {location}" if location else ""
    return f"- {violation.code}{location_clause}: {violation.message}"


def _html_validation_message(exc: HtmlValidationError) -> str:
    count = len(exc.violations)
    noun = "violation" if count == 1 else "violations"
    lines = [
        f"The HTML was not saved: it has {count} {noun}. "
        "Fix every one, then write the whole document again.",
        *(_html_violation_line(violation) for violation in exc.violations),
    ]
    return "\n".join(lines)


def map_portal_error_to_message(
    exc: BaseException,
    *,
    not_found_message: str | None = None,
    empty_fallback: str = _PORTAL_OPERATION_FAILED,
) -> str:
    """Map portal SDK/GraphQL failures to agent-friendly messages.

    Args:
        exc: Exception raised by ``PipefyClient`` portal methods or GraphQL transport.
        not_found_message: Message naming what the call was given, returned in
            place of the API's own not-found text (not fit to show). Omit to
            leave a not-found error unmapped, as every caller does today.
        empty_fallback: Non-empty message when ``str(exc)`` is blank after strip.
            Writes keep the default write-style fallback; reads pass a plain
            read-domain string.

    Returns:
        User-visible error string; permission failures mention ``create_portal``
        and ``manage_portals``, and HTML validation failures list every violation.
    """
    if isinstance(exc, HtmlValidationError):
        return _html_validation_message(exc)

    if isinstance(exc, PortalPermissionError):
        return ensure_non_empty_error_message(
            str(exc).strip(), _PORTAL_PERMISSION_GUIDANCE
        )

    text = str(exc).strip()
    lowered = text.lower()

    codes = extract_graphql_error_codes(exc)
    errors = getattr(exc, "errors", None)
    if isinstance(errors, list):
        for err in errors:
            if not isinstance(err, dict):
                continue
            extensions = err.get("extensions") or {}
            code = extensions.get("code")
            if isinstance(code, str):
                codes.append(code)

    if not_found_message is not None and (
        _NOT_FOUND_CODES.intersection(codes) or lowered.startswith("couldn't find")
    ):
        return not_found_message

    if "PERMISSION_DENIED" in codes or "permission denied" in lowered:
        return _PORTAL_PERMISSION_GUIDANCE

    if isinstance(exc, PipefyGraphQLError):
        messages = extract_error_strings(exc)
        if messages:
            return "; ".join(messages)

    return ensure_non_empty_error_message(text, empty_fallback)


_NOT_FOUND_CODES = frozenset({"RECORD_NOT_FOUND", "RESOURCE_NOT_FOUND"})
_SOURCE_ACCESS_DENIED = (
    "Permission denied for a data source: you can bind only the pipes and tables "
    "list_interface_repos returns for this interface."
)


def map_interface_source_error_to_message(
    exc: BaseException,
    *,
    not_found_message: str,
    empty_fallback: str = _PORTAL_OPERATION_FAILED,
) -> str:
    """Map failures of the interface data source tools to agent-friendly messages.

    The API's text for an unknown repo or interface uuid is not fit to show, so a
    not-found error becomes ``not_found_message``. A ``Permission denied`` with no
    error code is the API refusing a source's repo, not the interface.

    Args:
        exc: Exception raised by a ``PipefyClient`` interface source method.
        not_found_message: Message naming the ids the call was given.
        empty_fallback: Message for any other error whose text is blank.
    """
    if not isinstance(exc, PipefyGraphQLError):
        return map_portal_error_to_message(exc, empty_fallback=empty_fallback)
    codes = extract_graphql_error_codes(exc)
    lowered = str(exc).strip().lower()
    if _NOT_FOUND_CODES.intersection(codes) or lowered.startswith("couldn't find"):
        return not_found_message
    if not codes and lowered == "permission denied":
        return _SOURCE_ACCESS_DENIED
    return map_portal_error_to_message(exc, empty_fallback=empty_fallback)


def interface_sources_validation_error(exc: ValidationError) -> dict[str, object]:
    """Map an ``InterfaceDataSources`` validation error to ``INVALID_ARGUMENTS``.

    Each problem reads ``data_sources[index].key: message``; a rule over the whole
    list (a repeated ``id`` or ``name``) keeps its own message.
    """
    clauses: list[str] = []
    for err in exc.errors(include_url=False):
        inner = (err.get("ctx") or {}).get("error")
        if err.get("type") == "value_error" and inner is not None:
            message = str(inner)
        else:
            message = str(err.get("msg", ""))
        where = "data_sources" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in err.get("loc", ())
        )
        clauses.append(f"{where}: {message}")
    return tool_error("; ".join(clauses), code="INVALID_ARGUMENTS")


def validate_tool_ids(
    raw: dict[str, str],
) -> tuple[dict[str, str] | None, dict[str, object] | None]:
    """Validate multiple Pipefy IDs at the MCP tool boundary.

    Args:
        raw: Map of parameter name to raw ID string.

    Returns:
        ``(cleaned_ids, None)`` on success, or ``(None, error_payload)`` on the
        first invalid ID.
    """
    cleaned: dict[str, str] = {}
    for name, value in raw.items():
        ok, err = validate_tool_id(value, name)
        if err is not None:
            return None, err
        cleaned[name] = ok
    return cleaned, None


def finalize_internal_api_mutation(
    result: dict[str, Any],
    mutation_key: str,
    failure_message: str,
) -> dict[str, object]:
    """Map an Internal API mutation result to MCP success or failure payloads.

    Args:
        result: Raw GraphQL response dict from the SDK.
        mutation_key: Top-level mutation field name (e.g. ``updateSubPortalElement``).
        failure_message: User-visible message when ``success`` is not true.

    Returns:
        Success or error envelope for the MCP tool caller.
    """
    payload = result.get(mutation_key) or {}
    if payload.get("success"):
        return build_success_payload(result, include_parsed=True)
    return build_error_payload(failure_message)


async def run_sub_portal_internal_api_tool(
    *,
    ids: dict[str, str],
    debug_message: str,
    ctx_debug: Callable[[str], Awaitable[None]],
    invoke: Callable[[dict[str, str]], Awaitable[dict[str, Any]]],
    mutation_key: str,
    failure_message: str,
) -> dict[str, object]:
    """Shared shell for sub-portal Internal API write tools.

    Args:
        ids: Tool ID parameters to validate (name -> raw value).
        debug_message: Message passed to ``ctx.debug``.
        ctx_debug: Async debug hook from the MCP tool context.
        invoke: Callable receiving validated IDs and calling ``PipefyClient``.
        mutation_key: Top-level mutation field in the GraphQL response.
        failure_message: User-visible message when ``success`` is not true.

    Returns:
        MCP tool result envelope.
    """
    cleaned, err = validate_tool_ids(ids)
    if err is not None or cleaned is None:
        return err or build_error_payload("Invalid tool IDs.")
    await ctx_debug(debug_message.format(**cleaned))
    try:
        result = await invoke(cleaned)
    except Exception as exc:  # noqa: BLE001
        return build_error_payload(map_portal_error_to_message(exc))
    return finalize_internal_api_mutation(
        result,
        mutation_key,
        failure_message.format(**cleaned),
    )


def validate_portal_optional_string(
    value: str | None,
    field: str,
) -> tuple[str | None, dict[str, object] | None]:
    """Validate optional portal string fields at the MCP tool boundary.

    Args:
        value: Raw string from the tool parameter, or ``None`` when omitted.
        field: Parameter name for error messages (e.g. ``name``).

    Returns:
        ``(stripped_value, None)`` on success, ``(None, error_payload)`` when
        a non-empty string was required but missing or whitespace-only.
    """
    if value is None:
        return None, None
    if not isinstance(value, str) or not value.strip():
        return None, tool_error(
            f"Invalid '{field}': when provided, must be a non-empty string.",
            code="INVALID_ARGUMENTS",
        )
    return value.strip(), None


def validate_portal_page_index(
    index: int | None,
) -> dict[str, object] | None:
    """Reject negative or non-integer sort index at the MCP tool boundary.

    Args:
        index: Optional page sort index from the tool parameter.

    Returns:
        ``None`` when valid or omitted; otherwise an ``INVALID_ARGUMENTS`` envelope.
    """
    if index is None:
        return None
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        return tool_error(
            "Invalid 'index': must be a non-negative integer.",
            code="INVALID_ARGUMENTS",
        )
    return None


def validate_sort_page_ids_no_duplicates(
    page_ids: list[str],
) -> dict[str, object] | None:
    """Reject duplicate entries in an ordered ``page_ids`` list.

    Args:
        page_ids: Cleaned page identifiers after per-item validation.

    Returns:
        ``None`` when all entries are unique; otherwise an ``INVALID_ARGUMENTS`` envelope.
    """
    if len(set(page_ids)) != len(page_ids):
        return tool_error(
            "Invalid 'page_ids': must not contain duplicate page UUIDs.",
            code="INVALID_ARGUMENTS",
        )
    return None


def portal_element_validation_error(exc: ValidationError) -> dict[str, object]:
    """Map SDK portal element model validation to an MCP ``INVALID_ARGUMENTS`` envelope.

    Args:
        exc: Raised by a portal element input model (create, update, or delete).

    Returns:
        Tool failure payload with an actionable ``error.message`` (no Pydantic URLs).
    """
    clauses: list[str] = []
    for err in exc.errors():
        err_type = err.get("type", "")
        if err_type == "value_error":
            ctx = err.get("ctx") or {}
            inner = ctx.get("error")
            if inner is not None:
                clauses.append(str(inner))
                continue
        loc = ".".join(str(part) for part in err.get("loc", ()))
        msg = str(err.get("msg", ""))
        if loc == "type" and err_type == "literal_error":
            clauses.append(
                "Invalid 'type': must be a supported InterfacePageElementType value."
            )
        elif loc:
            clauses.append(f"{loc}: {msg}")
        elif msg:
            clauses.append(msg)
    message = "; ".join(clause for clause in clauses if clause)
    if not message:
        message = "Invalid portal element arguments."
    return tool_error(message, code="INVALID_ARGUMENTS")


@dataclass(frozen=True)
class PortalElementDeleteConfirmation:
    """Preview descriptor and token identity for ``delete_portal_element``."""

    resource_descriptor: str
    resource_identity: dict[str, str]


def plan_portal_element_delete_confirmation(
    validated: DeletePortalElementInput,
) -> PortalElementDeleteConfirmation:
    """Name a layout rewrite in the preview and bind its exact rows into the token.

    Without ``layout`` the identity is element + page only. With it, a token minted
    for no layout or for other rows does not verify.
    """
    descriptor = (
        f"portal element (UUID: {validated.element_id}) "
        f"on page (UUID: {validated.page_id})"
    )
    identity = {"element_id": validated.element_id, "page_id": validated.page_id}
    if validated.layout is None:
        return PortalElementDeleteConfirmation(descriptor, identity)
    rows = [row.model_dump() for row in validated.layout]
    identity["layout"] = digest_identity_value(rows)
    noun = "row" if len(rows) == 1 else "rows"
    return PortalElementDeleteConfirmation(
        f"{descriptor}, replacing that page's layout ({len(rows)} {noun} sent)",
        identity,
    )


__all__ = [
    "PortalElementDeleteConfirmation",
    "finalize_internal_api_mutation",
    "interface_sources_validation_error",
    "map_interface_source_error_to_message",
    "map_portal_error_to_message",
    "plan_portal_element_delete_confirmation",
    "portal_element_validation_error",
    "run_sub_portal_internal_api_tool",
    "validate_portal_optional_string",
    "validate_portal_page_index",
    "validate_sort_page_ids_no_duplicates",
    "validate_tool_ids",
]
