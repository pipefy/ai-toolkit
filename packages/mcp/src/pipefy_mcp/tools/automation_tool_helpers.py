"""Payload builders and GraphQL error mapping for traditional automation MCP tools."""

from __future__ import annotations

from typing import Any, Literal, cast

from mcp.server.mcpserver import Context
from pipefy_sdk import (
    AutomationActionRow,
    AutomationEventRow,
    AutomationRuleRecord,
    AutomationRuleSummary,
    SimulationOutputWarning,
)
from typing_extensions import NotRequired, TypedDict

from pipefy_mcp.core.tool_error_envelope import ToolErrorDetail, tool_error
from pipefy_mcp.tools.graphql_error_helpers import (
    extract_error_strings,
    extract_graphql_correlation_id,
    extract_graphql_error_codes,
    try_enrich_graphql_error,
    with_debug_suffix,
)
from pipefy_mcp.tools.pagination_helpers import PaginationInfo

AutomationReadToolData = (
    AutomationRuleRecord
    | list[AutomationRuleSummary]
    | list[AutomationActionRow]
    | list[AutomationEventRow]
)


class AutomationReadSuccessPayload(TypedDict):
    success: Literal[True]
    message: str
    data: AutomationReadToolData
    pagination: NotRequired[PaginationInfo]


class AutomationMutationSuccessPayload(TypedDict):
    success: Literal[True]
    message: str
    automation: dict[str, Any]


class _AutomationSimulationPayload(TypedDict):
    success: Literal[True]
    message: str
    simulation_id: str
    automation_simulation: dict[str, Any]
    warnings: list[SimulationOutputWarning]


class AutomationSimulationSuccessPayload(_AutomationSimulationPayload):
    field_ids: list[str]


class AutomationSimulationReadPayload(_AutomationSimulationPayload):
    waited_seconds: float


class AutomationToolErrorPayload(TypedDict):
    success: Literal[False]
    error: ToolErrorDetail


_AUTOMATION_REQUEST_FAILED = "Automation request failed."


def build_automation_mutation_success_payload(
    automation: dict[str, Any],
    action: str,
) -> AutomationMutationSuccessPayload:
    """``success`` plus labeled ``message`` and raw ``automation`` dict.

    Args:
        automation: ``automation`` key from the mutation (possibly empty for delete).
        action: Verb for the canned label (``created`` / ``updated`` / ``deleted`` / other).
    """
    labels = {
        "created": "Automation created.",
        "updated": "Automation updated.",
        "deleted": "Automation deleted.",
    }
    message = labels.get(action, f"Automation {action}.")
    return {
        "success": True,
        "message": message,
        "automation": automation,
    }


def build_automation_simulation_success_payload(
    simulation_id: str,
    automation_simulation: dict[str, Any],
    warnings: list[SimulationOutputWarning],
    field_ids: list[str],
) -> AutomationSimulationSuccessPayload:
    """Success payload with full ``automationSimulation`` row and the mutation ``simulationId``."""

    return {
        "success": True,
        "message": _simulation_message(
            "Automation simulation completed.",
            simulation_id,
            automation_simulation,
            field_ids,
        ),
        "simulation_id": simulation_id,
        "automation_simulation": automation_simulation,
        "warnings": warnings,
        "field_ids": field_ids,
    }


def build_automation_simulation_read_payload(
    simulation_id: str,
    automation_simulation: dict[str, Any],
    warnings: list[SimulationOutputWarning],
    waited_seconds: float,
    field_ids: list[str] | None,
) -> AutomationSimulationReadPayload:
    """Success payload for ``get_automation_simulation``, with the time it waited."""

    return {
        "success": True,
        "message": _simulation_message(
            "Automation simulation read.",
            simulation_id,
            automation_simulation,
            field_ids,
        ),
        "simulation_id": simulation_id,
        "automation_simulation": automation_simulation,
        "warnings": warnings,
        "waited_seconds": waited_seconds,
    }


def _simulation_message(
    final_message: str,
    simulation_id: str,
    automation_simulation: dict[str, Any],
    field_ids: list[str] | None,
) -> str:
    if automation_simulation.get("status") != "processing":
        return final_message
    pending = "The simulation is still processing. Read it again with"
    same_ids = "Send the same field_ids on each read while the status is processing."
    if field_ids is None:
        return (
            f"{pending} get_automation_simulation(simulation_id={simulation_id!r}), "
            f"and send the fieldIds of the prompt as field_ids. {same_ids}"
        )
    if not field_ids:
        return f"{pending} get_automation_simulation(simulation_id={simulation_id!r})."
    return (
        f"{pending} get_automation_simulation(simulation_id={simulation_id!r}, "
        f"field_ids={field_ids!r}). {same_ids}"
    )


def build_automation_read_success_payload(
    data: AutomationReadToolData,
    label: str,
    *,
    pagination: PaginationInfo | None = None,
) -> AutomationReadSuccessPayload:
    """``success``, ``message``, typed read ``data``, and ``pagination`` for paged listings.

    Args:
        data: Record, summary list, or catalog rows from the API.
        label: Shown as ``message``.
        pagination: Top-level page block for paged listings; omitted when ``None``.
    """
    payload: AutomationReadSuccessPayload = {
        "success": True,
        "message": label,
        "data": data,
    }
    if pagination is not None:
        payload["pagination"] = pagination
    return payload


def build_automations_listed_message(listed: int, total: int, *, has_more: bool) -> str:
    """``message`` for ``get_automations``: rows in this page vs total, plus how to continue.

    Args:
        listed: Rows in this page.
        total: ``totalCount`` of the connection.
        has_more: ``pageInfo.hasNextPage``; when false the message names the last page
            so a short page is not read as a missing remainder.
    """
    message = f"Automations listed: {listed} of {total}."
    if has_more:
        return (
            f"{message} More rules exist; call again with after=pagination.end_cursor. "
            "The listing is incomplete until pagination.has_more is false."
        )
    return f"{message} This is the last page."


def build_automation_error_payload(
    message: str,
    debug: str | None = None,
    *,
    code: str | None = None,
) -> AutomationToolErrorPayload:
    """``success: False``; optional ``debug`` suffix in brackets.

    Args:
        message: Primary error text.
        debug: Extra detail appended as ``… [debug]`` when set.
        code: Optional machine-readable code (e.g. GraphQL ``extensions.code``).
    """
    text = message if not debug else f"{message} [{debug}]"
    return cast(AutomationToolErrorPayload, tool_error(text, code=code))


async def handle_automation_tool_graphql_error(
    exc: BaseException,
    ctx: Context,
    debug: bool,
    *,
    resource_kind: str | None = None,
    resource_id: str | None = None,
    invalid_args_hint: str | None = None,
) -> AutomationToolErrorPayload:
    """Format ``exc`` as ``build_automation_error_payload``; optional MCP debug log.

    Mirrors :func:`handle_tool_graphql_error` enrichment precedence so automation
    tools surface the same discovery hints as other domains.

    Args:
        exc: Root exception from gql/httpx.
        ctx: MCP context for ``ctx.debug`` when ``debug`` is True.
        debug: Log raw exception and append codes / ``correlation_id`` to the message.
        resource_kind: Optional canonical kind; opts into NOT_FOUND enrichment.
        resource_id: Optional resource id; surfaced in the enriched message.
        invalid_args_hint: Optional tool-specific hint for BAD_USER_INPUT errors.
    """
    if debug:
        await ctx.debug(f"automation GraphQL error: {exc!r}")

    codes = extract_graphql_error_codes(exc)
    first_code = codes[0] if codes else None
    cid = extract_graphql_correlation_id(exc) if debug else None

    enriched_result = try_enrich_graphql_error(
        exc,
        codes=codes,
        debug=debug,
        correlation_id=cid,
        resource_kind=resource_kind,
        resource_id=resource_id,
        invalid_args_hint=invalid_args_hint,
    )
    if enriched_result is not None:
        message, code = enriched_result
        return build_automation_error_payload(message=message, code=code)

    msgs = extract_error_strings(exc)
    base = "; ".join(msgs) if msgs else _AUTOMATION_REQUEST_FAILED
    if not base.strip():
        base = _AUTOMATION_REQUEST_FAILED
    base = with_debug_suffix(base, debug=debug, codes=codes, correlation_id=cid)
    return build_automation_error_payload(message=base, code=first_code)


__all__ = [
    "AutomationMutationSuccessPayload",
    "AutomationReadSuccessPayload",
    "AutomationReadToolData",
    "AutomationSimulationReadPayload",
    "AutomationSimulationSuccessPayload",
    "AutomationToolErrorPayload",
    "build_automation_error_payload",
    "build_automation_mutation_success_payload",
    "build_automation_read_success_payload",
    "build_automation_simulation_read_payload",
    "build_automation_simulation_success_payload",
    "handle_automation_tool_graphql_error",
]
