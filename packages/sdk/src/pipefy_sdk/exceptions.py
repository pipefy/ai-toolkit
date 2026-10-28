from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Typed SDK errors for gradual service-layer migration; not all call sites raise these yet.


class PipefyError(Exception):
    """Base class for Pipefy SDK errors."""


class PipefyAPIError(PipefyError):
    """Raised when the Pipefy GraphQL API returns an error payload."""


class PipefyRequestTimeoutError(PipefyError, TimeoutError):
    """Raised when a GraphQL request exceeds the SDK's request timeout.

    Both gql's per-execute timer and the httpx transport are bounded by
    ``GraphQLEndpoint.GRAPHQL_REQUEST_TIMEOUT_SECONDS``. When that bound fires gql
    raises a bare :class:`TimeoutError` with an empty message, so a caller — and
    the MCP error layer that reads ``str(exc)`` — cannot tell a timeout from any
    other blank error, nor how long the call waited. The executor translates that
    bare timeout into this error, whose message names the limit and its value.

    It subclasses :class:`TimeoutError` as well as :class:`PipefyError` so the two
    contracts hold at once: existing ``except TimeoutError`` handlers keep catching
    a timed-out request, and it is also catchable as the SDK root like every other
    SDK error. ``timeout_seconds`` carries the bound that fired.
    """

    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Pipefy GraphQL request timed out after {timeout_seconds} s "
            f"(GraphQLEndpoint.GRAPHQL_REQUEST_TIMEOUT_SECONDS). "
            "A mutation can still have been applied. Read the state back before you retry."
        )


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


class PipePhaseSetupError(PipefyError):
    """Raised when ``create_pipe`` created the pipe but setting up its phases failed.

    The pipe exists. Some default phases can remain, and of the requested phases
    only ``created_phases`` exist. Read the pipe with ``get_pipe`` and fix its
    phases, or remove it with ``delete_pipe``. The failed call's error is the
    ``__cause__``.
    """

    def __init__(
        self, *, pipe_id: str, created_phases: list[dict[str, Any]], reason: str
    ) -> None:
        self.pipe_id = pipe_id
        self.created_phases = created_phases
        names = ", ".join(phase["name"] for phase in created_phases) or "none"
        super().__init__(
            f"Pipe {pipe_id} was created, but setting up its phases failed: "
            f"{reason.strip().rstrip('.')}. Requested phases created: {names}. Read the "
            "pipe with get_pipe, then fix its phases or delete it with delete_pipe."
        )


def _text_or_none(value: object) -> str | None:
    """Read a blank or non-text value as absent."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


@dataclass(frozen=True)
class HtmlViolation:
    """One rule an interface's HTML broke, as the API reports it.

    ``code`` and ``message`` are non-empty. ``selector`` names the offending tag
    and ``attribute`` the offending attribute on it; each is ``None`` or
    non-empty, and both are ``None`` for a violation of the whole document, such
    as its size.
    """

    code: str
    message: str
    selector: str | None
    attribute: str | None

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError("An HTML violation needs a non-empty code and message.")
        if self.selector == "" or self.attribute == "":
            raise ValueError(
                "An HTML violation's selector and attribute are None or non-empty."
            )

    @classmethod
    def from_extension(cls, raw: dict[str, Any]) -> HtmlViolation | None:
        """Parse one ``extensions.violations`` entry; ``None`` without a code and message."""
        code = _text_or_none(raw.get("code"))
        message = _text_or_none(raw.get("message"))
        if code is None or message is None:
            return None
        return cls(
            code=code,
            message=message,
            selector=_text_or_none(raw.get("selector")),
            attribute=_text_or_none(raw.get("attribute")),
        )


class HtmlValidationError(PipefyError):
    """Raised when an HTML interface write fails validation (``HTML_VALIDATION_FAILED``).

    Nothing was stored. ``violations`` lists every rule the HTML broke, at least
    one, so a caller can fix them all before writing again.
    """

    def __init__(self, violations: tuple[HtmlViolation, ...]) -> None:
        if not violations:
            raise ValueError("HtmlValidationError needs at least one violation.")
        self.violations = violations
        super().__init__(
            "HTML validation failed: "
            + " ".join(violation.message for violation in violations)
        )


PORTAL_PERMISSION_MESSAGE = (
    "Permission denied. The account the toolkit signs in as needs the "
    "organization permission `create_portal` or `manage_portals` (request it "
    "from your organization admin) and, to write to an existing portal, the "
    "admin role on that portal. An organization admin is still denied on a "
    "portal they have not joined, even one they created: that account must join "
    "it once through the Interfaces `joinAsAdmin` mutation, which the toolkit "
    "does not expose."
)


class PortalPermissionError(ValueError):
    """Raised when a portal Interfaces operation fails with PERMISSION_DENIED.

    The default message names both grants a portal write needs: the
    organization permission and the admin role on the target portal.
    """

    def __init__(self, message: str = PORTAL_PERMISSION_MESSAGE) -> None:
        super().__init__(message)
