"""Tests for InboxEmailDraft."""

import pytest
from pydantic import ValidationError

from pipefy_sdk import InboxEmailDraft


@pytest.mark.unit
def test_draft_strips_recipients_and_sender():
    draft = InboxEmailDraft(
        card_id=12,
        to=[" a@x.com "],
        subject="Hi",
        body="",
        from_=" s@x.com ",
    )

    assert draft.card_id == "12"
    assert draft.to == ("a@x.com",)
    assert draft.from_ == "s@x.com"


@pytest.mark.unit
@pytest.mark.parametrize(
    "overrides",
    [
        {"to": []},
        {"to": ["  "]},
        {"from_": ""},
        {"card_id": ""},
    ],
)
def test_draft_rejects_missing_card_sender_or_recipients(overrides):
    fields = {
        "card_id": "1",
        "to": ["a@x.com"],
        "subject": "Hi",
        "body": "Body",
        "from_": "s@x.com",
    }
    with pytest.raises(ValidationError):
        InboxEmailDraft(**{**fields, **overrides})


@pytest.mark.unit
def test_draft_is_frozen():
    draft = InboxEmailDraft(
        card_id="1", to=["a@x.com"], subject="Hi", body="", from_="s@x.com"
    )
    with pytest.raises(ValidationError):
        draft.subject = "changed"
