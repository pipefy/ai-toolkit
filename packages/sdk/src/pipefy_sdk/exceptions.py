from __future__ import annotations

# Typed SDK errors for gradual service-layer migration; not all call sites raise these yet.


class PipefyError(Exception):
    """Base class for Pipefy SDK errors."""


class PipefyAPIError(PipefyError):
    """Raised when the Pipefy GraphQL API returns an error payload."""


class PortalPermissionError(ValueError):
    """Raised when a portal Interfaces operation fails with PERMISSION_DENIED."""


class PartialCardUpdateError(PipefyAPIError):
    """``updateFieldsValues`` rejected part of a batch after applying the rest.

    The mutation reports one ``success`` flag for the whole batch while
    validating each entry in ``values`` on its own, so a batch with one bad
    entry can come back ``success: false`` with the remaining entries already
    written. Retrying the same call is unsafe on ``operation: "ADD"``, which
    appends rather than replaces.

    ``applied_field_ids`` is read back from the card after the mutation, not
    derived from ``updatedNode``: that block has been observed omitting a field
    whose value a follow-up read showed had persisted.

    Attributes:
        card_id: Card the batch targeted.
        applied_field_ids: Requested field ids confirmed written by the re-read.
        rejected: One ``{"field_id": str, "message": str}`` per rejected entry,
            carrying the API's own text for that field.
        verified: Whether the re-read succeeded. When False,
            ``applied_field_ids`` is empty because nothing could be confirmed,
            which is not the same as nothing having been written.
    """

    def __init__(
        self,
        *,
        card_id: str,
        applied_field_ids: list[str],
        rejected: list[dict[str, str]],
        verified: bool = True,
    ) -> None:
        self.card_id = card_id
        self.applied_field_ids = applied_field_ids
        self.rejected = rejected
        self.verified = verified
        super().__init__(
            _partial_card_update_message(card_id, applied_field_ids, rejected, verified)
        )


def _partial_card_update_message(
    card_id: str,
    applied_field_ids: list[str],
    rejected: list[dict[str, str]],
    verified: bool,
) -> str:
    """One line naming what landed, what did not, and why."""
    parts: list[str] = []
    for entry in rejected:
        field_id = entry.get("field_id") or ""
        message = entry.get("message") or ""
        if field_id:
            parts.append(f"{field_id}: {message}")
        elif message:
            parts.append(message)
    detail = "; ".join(parts) if parts else "no per-field detail returned"
    if not verified:
        return (
            f"Card {card_id} update partly rejected ({detail}). Could not re-read the "
            f"card to confirm which fields were written. Retry only the rejected "
            f"fields; do not resend an ADD operation for any other requested id."
        )
    if applied_field_ids:
        applied = ", ".join(applied_field_ids)
        return (
            f"Card {card_id} update partly applied. Written: {applied}. "
            f"Rejected: {detail}. Retry only the rejected fields; resending the "
            f"written ones with operation ADD appends duplicates."
        )
    return (
        f"Card {card_id} update rejected and nothing was written. Rejected: {detail}."
    )
