from __future__ import annotations

# Typed SDK errors for gradual service-layer migration; not all call sites raise these yet.


class PipefyError(Exception):
    """Base class for Pipefy SDK errors."""


class PipefyAPIError(PipefyError):
    """Raised when the Pipefy GraphQL API returns an error payload."""


class AiAgentConfigureError(PipefyError):
    """Raised when ``create_ai_agent`` created the agent but its configure update failed.

    The agent exists and is disabled when ``disabled_at`` is set. Write its
    behaviors with ``update_ai_agent(agent_uuid, ...)``, which keeps it disabled,
    then activate it with ``toggle_ai_agent_status``; or remove it with
    ``delete_ai_agent``. The update's error is the ``__cause__``.
    """

    def __init__(
        self, *, agent_uuid: str, disabled_at: str | None, reason: str
    ) -> None:
        self.agent_uuid = agent_uuid
        self.disabled_at = disabled_at
        message = (
            f"AI Agent {agent_uuid} was created, but writing its instruction "
            f"and behaviors failed: {reason}"
        )
        if disabled_at is not None:
            message += (
                f" The agent is disabled (disabledAt {disabled_at}). A routine "
                "update_ai_agent keeps it disabled; after a successful update, "
                "call toggle_ai_agent_status to activate it."
            )
        super().__init__(message)


class PortalPermissionError(ValueError):
    """Raised when a portal Interfaces operation fails with PERMISSION_DENIED."""
