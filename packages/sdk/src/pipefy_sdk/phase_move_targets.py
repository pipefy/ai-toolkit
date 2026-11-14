"""Build the list of phases a card can move to, for ``updatePhaseJumps``."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pipefy_sdk.phase_inventory import get_phase_not_found_message


def parse_target_phase_ids(
    target_phase_ids: Sequence[str | int], *, replace: bool
) -> tuple[str, ...]:
    """Return the destination ids as strings, in order, each one once.

    An empty list is valid only with ``replace``. It removes every connection.

    Raises:
        ValueError: ``target_phase_ids`` is a string or bytes, an id is blank,
            or the list is empty and ``replace`` is False.
    """
    if isinstance(target_phase_ids, (str, bytes)):
        raise ValueError(
            f"target_phase_ids must be a list of phase ids: received "
            f"{target_phase_ids!r}, expected a list such as ['123']"
        )
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


def merge_phase_move_targets(
    phase_id: str | int,
    allowed_moves: dict[str, Any],
    target_phase_ids: tuple[str, ...],
) -> list[str]:
    """Return the current destinations of ``phase_id`` followed by the new ones.

    ``updatePhaseJumps`` replaces the whole list, so an addition must send the
    destinations that the read returned too. A destination that another client
    saves after that read is not in the list, and the write removes it.

    Args:
        phase_id: Source phase.
        allowed_moves: ``get_phase_allowed_move_targets`` payload for ``phase_id``.
        target_phase_ids: Output of :func:`parse_target_phase_ids`.

    Raises:
        ValueError: The read returned no phase.
    """
    phase = allowed_moves.get("phase")
    if not phase:
        raise ValueError(get_phase_not_found_message(phase_id))
    current = [
        str(row["id"]) for row in phase.get("cards_can_be_moved_to_phases") or []
    ]
    return current + [t for t in target_phase_ids if t not in current]


__all__ = ["merge_phase_move_targets", "parse_target_phase_ids"]
