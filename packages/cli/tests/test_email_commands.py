"""CLI tests for ``pipefy email`` send commands."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pipefy_sdk import InboxEmailDraft
from typer.testing import CliRunner

from pipefy_cli.main import app

INBOX_SEND = [
    "email",
    "inbox",
    "send",
    "--card",
    "12",
    "--to",
    "a@x.com, b@x.com",
    "--subject",
    "Hello",
    "--body",
    "Hi there",
    "--from-email",
    "s@x.com",
]
TEMPLATE_SEND = ["email", "template", "send", "--card", "12", "--template", "42"]
SENT = {"createAndSendInboxEmail": {"emailSent": True, "errors": []}}


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.send_inbox_email_draft = AsyncMock(return_value=SENT)
    client.send_email_with_template = AsyncMock(return_value=SENT)
    client.draft_email_from_template = AsyncMock(
        return_value=InboxEmailDraft(
            card_id="12",
            to=["margaret@example.com"],
            subject="Your request",
            body="",
            from_="pipe1@inbox.example.com",
            extra={"repoId": "7"},
        )
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=client,
    ):
        yield client


def test_email_inbox_send_without_yes_previews_and_sends_nothing(
    runner: CliRunner, clean_pipefy_env, saved_cwd, oauth_env, mock_client
):
    oauth_env("em")

    r = runner.invoke(app, [*INBOX_SEND, "--extra", '{"cc": ["c@x.com"]}', "--json"])

    assert r.exit_code == 2
    mock_client.send_inbox_email_draft.assert_not_called()
    assert json.loads(r.stdout) == {
        "card_id": "12",
        "to": ["a@x.com", "b@x.com"],
        "subject": "Hello",
        "body": "Hi there",
        "from_": "s@x.com",
        "extra": {"cc": ["c@x.com"]},
    }
    assert "Nothing was sent" in r.stderr


def test_email_inbox_send_with_yes_sends(
    runner: CliRunner, clean_pipefy_env, saved_cwd, oauth_env, mock_client
):
    oauth_env("em")

    r = runner.invoke(app, [*INBOX_SEND, "--yes", "--json"])

    assert r.exit_code == 0, r.output
    mock_client.send_inbox_email_draft.assert_awaited_once_with(
        InboxEmailDraft(
            card_id="12",
            to=["a@x.com", "b@x.com"],
            subject="Hello",
            body="Hi there",
            from_="s@x.com",
        )
    )
    assert json.loads(r.stdout) == SENT


def test_email_template_send_without_yes_previews_the_resolved_email(
    runner: CliRunner, clean_pipefy_env, saved_cwd, oauth_env, mock_client
):
    oauth_env("em")

    r = runner.invoke(app, [*TEMPLATE_SEND, "--json"])

    assert r.exit_code == 2
    mock_client.draft_email_from_template.assert_awaited_once_with(
        "12", "42", to=None, from_=None
    )
    mock_client.send_email_with_template.assert_not_called()
    preview = json.loads(r.stdout)
    assert preview["to"] == ["margaret@example.com"]
    assert preview["body"] == ""
    assert "Nothing was sent" in r.stderr


def test_email_template_send_with_yes_sends(
    runner: CliRunner, clean_pipefy_env, saved_cwd, oauth_env, mock_client
):
    oauth_env("em")

    r = runner.invoke(
        app, [*TEMPLATE_SEND, "--to", "o@x.com", "--extra", '{"cc": ["c@x.com"]}', "-y"]
    )

    assert r.exit_code == 0, r.output
    mock_client.send_email_with_template.assert_awaited_once_with(
        "12", "42", to=["o@x.com"], from_=None, cc=["c@x.com"]
    )
    mock_client.draft_email_from_template.assert_not_called()


def test_email_template_send_preview_reports_an_unresolvable_template(
    runner: CliRunner, clean_pipefy_env, saved_cwd, oauth_env, mock_client
):
    oauth_env("em")
    mock_client.draft_email_from_template.side_effect = ValueError(
        "Template has no toEmail and no to override; provide recipients."
    )

    r = runner.invoke(app, TEMPLATE_SEND)

    assert r.exit_code == 2
    assert "no toEmail" in r.stderr
    assert "Nothing was sent" not in r.stderr
    mock_client.send_email_with_template.assert_not_called()


def test_email_inbox_send_rejects_a_blank_sender_before_sending(
    runner: CliRunner, clean_pipefy_env, saved_cwd, oauth_env, mock_client
):
    oauth_env("em")
    args = [*INBOX_SEND[:-1], "   ", "--yes"]

    r = runner.invoke(app, args)

    assert r.exit_code == 2
    mock_client.send_inbox_email_draft.assert_not_called()
