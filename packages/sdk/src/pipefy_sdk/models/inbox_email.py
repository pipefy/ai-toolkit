"""Card inbox email draft: the exact message a send would deliver."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from pipefy_sdk.models.validators import NonBlankStr, PipefyId


class InboxEmailDraft(BaseModel):
    """One email ready to send from a card's inbox (``createAndSendInboxEmail``).

    Holding a draft means it has a card, a sender and at least one recipient,
    so a caller can show it for approval and send it without re-checking.

    Attributes:
        card_id: ID of the card whose inbox sends the email.
        to: Recipient addresses (at least one).
        subject: Email subject.
        body: Email body (plain text).
        from_: Sender address.
        extra: Extra ``CreateAndSendInboxEmailInput`` fields (cc, bcc, html, repoId).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    card_id: PipefyId
    to: tuple[NonBlankStr, ...] = Field(min_length=1)
    subject: str
    body: str
    from_: NonBlankStr
    extra: dict[str, Any] = Field(default_factory=dict)


__all__ = ["InboxEmailDraft"]
