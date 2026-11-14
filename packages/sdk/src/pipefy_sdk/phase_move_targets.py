"""Build the ``updatePhase`` input that sets the phases a card can move to."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pipefy_sdk.graphql_inputs import UpdatePhaseInput
from pipefy_sdk.phase_inventory import get_phase_not_found_message


def parse_target_phase_ids(
    target_phase_ids: Sequence[str | int], *, replace: bool
) -> tuple[str, ...]:
    """Return the destination ids as strings, in order, each one once.

    An empty list is valid only with ``replace``. It removes every connection.

    Raises:
        ValueError: An id is blank, or the list is empty and ``replace`` is False.
    """
    parsed: dict[str, None] = {}
    for index, raw in enumerate(target_phase_ids):
        phase_id = str(raw).strip()
        if not phase_id:
            raise ValueError(
                f"target_phase_ids[{index}] is blank: received {raw!r}, "
                "expected a phase id"
            )
        parsed[phase_id] = None
    if not parsed and not replace:
        raise ValueError(
            "target_phase_ids is empty: pass at least one destination phase id. "
            "To remove every connection, send an empty list with replace."
        )
    return tuple(parsed)


def plan_phase_move_targets(
    phase_id: str | int,
    allowed_moves: dict[str, Any],
    target_phase_ids: tuple[str, ...],
    *,
    replace: bool,
) -> UpdatePhaseInput:
    """Build the input that gives ``phase_id`` its new outgoing connections.

    ``updatePhase`` replaces the whole ``jumpTargetIds`` list and requires
    ``name``. The input therefore repeats the current name. Unless ``replace``
    is True, it also keeps the current destinations before the new ones.

    Args:
        phase_id: Source phase.
        allowed_moves: ``get_phase_allowed_move_targets`` payload for ``phase_id``.
        target_phase_ids: Output of :func:`parse_target_phase_ids`.
        replace: Send ``target_phase_ids`` as the complete list.

    Raises:
        ValueError: The read returned no phase.
    """
    phase = allowed_moves.get("phase")
    if not phase:
        raise ValueError(get_phase_not_found_message(phase_id))
    jump_target_ids = list(target_phase_ids)
    if not replace:
        current = [
            str(row["id"]) for row in phase.get("cards_can_be_moved_to_phases") or []
        ]
        jump_target_ids = current + [t for t in target_phase_ids if t not in current]
    return UpdatePhaseInput(
        id=str(phase_id),
        name=phase["name"],
        jumpTargetIds=jump_target_ids,
    )


__all__ = ["parse_target_phase_ids", "plan_phase_move_targets"]
