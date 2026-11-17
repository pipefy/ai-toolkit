"""Pure decisions for reading an AI automation simulation: when to read again, what to warn about."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any, Literal, TypedDict

SIMULATION_PROCESSING_STATUS = "processing"
SIMULATION_SUCCESS_STATUS = "success"
SIMULATION_POLL_INTERVAL_SECONDS = 2.0
SIMULATION_DEFAULT_WAIT_SECONDS = 30
SIMULATION_MAX_WAIT_SECONDS = 60

# A link label is followed by "(", so "[text](url)" never matches.
_BRACKET_PLACEHOLDER = re.compile(r"\[([^\[\]\n]{1,60})\](?!\()")
_CHECKBOX_MARKS = frozenset({"x", "X"})

SimulationWarningKind = Literal["placeholder", "empty"]


class SimulationOutputWarning(TypedDict):
    """A part of the simulated output that the caller should check before it trusts the prompt.

    ``placeholder``: ``text`` is a bracket placeholder such as ``[Your Name]``.
    ``empty``: the simulation wrote no value to a requested field; ``text`` is empty.
    """

    field_id: str
    kind: SimulationWarningKind
    text: str


def parse_simulation_wait_seconds(timeout_seconds: int) -> int:
    """Return ``timeout_seconds`` when it is a whole number from 0 to 60."""
    in_range = 0 <= timeout_seconds <= SIMULATION_MAX_WAIT_SECONDS
    if isinstance(timeout_seconds, bool) or not in_range:
        raise ValueError(
            f"Invalid timeout_seconds={timeout_seconds!r}: expected a whole number "
            f"from 0 to {SIMULATION_MAX_WAIT_SECONDS}."
        )
    return timeout_seconds


def next_simulation_poll_delay(
    status: str | None, *, waited_seconds: float, timeout_seconds: int
) -> float | None:
    """Seconds to wait before the next read, or ``None`` when the read loop must stop."""
    if status != SIMULATION_PROCESSING_STATUS:
        return None
    remaining = timeout_seconds - waited_seconds
    if remaining <= 0:
        return None
    return min(SIMULATION_POLL_INTERVAL_SECONDS, remaining)


def requested_simulation_field_ids(
    action_params: Mapping[str, Any] | None,
) -> list[str]:
    """The ``aiParams.fieldIds`` of a ``generate_with_ai`` simulation input, as strings."""
    ai_params = (action_params or {}).get("aiParams")
    if not isinstance(ai_params, Mapping):
        return []
    field_ids = ai_params.get("fieldIds")
    if not isinstance(field_ids, list):
        return []
    return [str(field_id) for field_id in field_ids]


def simulation_output_warnings(
    automation_simulation: Mapping[str, Any],
    requested_field_ids: Iterable[str | int] | None = None,
) -> list[SimulationOutputWarning]:
    """Bracket placeholders in the output, then requested fields with no output.

    Only a ``success`` simulation has output to check; other statuses give no warning.
    The API leaves a field out of ``simulationResult`` when the run wrote no value to it.
    """
    if automation_simulation.get("status") != SIMULATION_SUCCESS_STATUS:
        return []
    result = automation_simulation.get("simulationResult") or {}
    warnings = [
        SimulationOutputWarning(field_id=str(field_id), kind="placeholder", text=text)
        for field_id, entry in result.items()
        for text in _placeholders_in(entry)
    ]
    for field_id in _unique_ids(requested_field_ids or ()):
        if field_id not in result:
            warnings.append(
                SimulationOutputWarning(field_id=field_id, kind="empty", text="")
            )
    return warnings


def _placeholders_in(entry: Any) -> list[str]:
    value = entry.get("value") if isinstance(entry, Mapping) else None
    texts = value if isinstance(value, list) else [value]
    matches = (
        match.group(0)
        for text in texts
        if isinstance(text, str)
        for match in _BRACKET_PLACEHOLDER.finditer(text)
        if _is_placeholder(match.group(1))
    )
    return list(dict.fromkeys(matches))


def _is_placeholder(inner: str) -> bool:
    stripped = inner.strip()
    return stripped not in _CHECKBOX_MARKS and any(ch.isalpha() for ch in stripped)


def _unique_ids(field_ids: Iterable[str | int]) -> list[str]:
    cleaned = (str(field_id).strip() for field_id in field_ids)
    return list(dict.fromkeys(field_id for field_id in cleaned if field_id))


__all__ = [
    "SIMULATION_DEFAULT_WAIT_SECONDS",
    "SIMULATION_MAX_WAIT_SECONDS",
    "SIMULATION_POLL_INTERVAL_SECONDS",
    "SimulationOutputWarning",
    "next_simulation_poll_delay",
    "parse_simulation_wait_seconds",
    "requested_simulation_field_ids",
    "simulation_output_warnings",
]
