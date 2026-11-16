"""Shared copy for phase transition rules: how phases get connected and how to read them."""

from __future__ import annotations

TRANSITION_RULES_HINT = (
    "Phase transition rules (Pipe settings -> Phase -> Connections) set where a card "
    "can move. create_phase connects a new phase to the phases beside it. "
    "Use get_phase_allowed_move_targets on the source phase to list valid destinations "
    "(GraphQL field phase.cards_can_be_moved_to_phases). A new connection applies to "
    "every card in the source phase. Add one only when the user asks for it or the "
    "process design needs it, with set_phase_move_targets (CLI: pipefy phase targets "
    "--add). If the session does not have that tool, ask a pipe admin to add the "
    "connection."
)


def format_allowed_destinations_phrase(allowed_phases: list[dict]) -> str:
    """Human-readable list of phase names and IDs for error messages.

    Args:
        allowed_phases: Items with ``id`` and optional ``name`` (GraphQL Phase rows).
    """
    if not allowed_phases:
        return "(none configured)"
    parts: list[str] = []
    for p in allowed_phases:
        pid = p.get("id")
        name = p.get("name") or ""
        if name and pid is not None:
            parts.append(f"{name} ({pid})")
        elif pid is not None:
            parts.append(str(pid))
    return ", ".join(parts) if parts else "(none configured)"


__all__ = [
    "TRANSITION_RULES_HINT",
    "format_allowed_destinations_phrase",
]
