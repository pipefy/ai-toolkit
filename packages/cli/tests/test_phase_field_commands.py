"""Tests for ``pipefy phase`` and ``pipefy field`` subcommands."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click import unstyle
from pipefy_sdk.graphql_inputs import (
    CreatePhaseFieldInput,
    UpdatePhaseFieldInput,
    UpdatePhaseInput,
)
from pipefy_sdk.transition_hints import TRANSITION_RULES_HINT

from pipefy_cli.main import app


def test_phase_get_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("ph-get")
    payload = {"phase_id": "1", "phase_name": "Backlog", "fields": []}
    mock_client = MagicMock()
    mock_client.get_phase_fields = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["phase", "get", "1", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == payload
    mock_client.get_phase_fields.assert_awaited_once_with("1", required_only=False)


def test_phase_create_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("ph-cr")
    payload = {"createPhase": {}}
    mock_client = MagicMock()
    mock_client.create_phase = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["phase", "create", "--pipe", "9", "--name", "Review", "--json"],
        )
    assert result.exit_code == 0
    mock_client.create_phase.assert_awaited_once_with(
        "9", "Review", done=False, index=None, description=None
    )
    # Hint prints on success, on stderr so it never pollutes --json stdout.
    assert TRANSITION_RULES_HINT in result.stderr
    assert result.stdout.strip() != ""
    json.loads(result.stdout)


def test_phase_update_resolves_name_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("ph-upd")
    mock_client = MagicMock()
    mock_client.get_phase_fields = AsyncMock(
        return_value={"phase_name": "Todo", "fields": []}
    )
    mock_client.update_phase = AsyncMock(return_value={"updatePhase": {}})
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["phase", "update", "3", "--description", "x", "--json"],
        )
    assert result.exit_code == 0
    mock_client.update_phase.assert_awaited_once_with(
        UpdatePhaseInput(id="3", description="x", name="Todo")
    )
    assert TRANSITION_RULES_HINT in result.stderr
    json.loads(result.stdout)


@pytest.mark.parametrize(
    "args",
    [
        [
            "field",
            "update",
            "priority",
            "--extra",
            '{"id": "other_field", "label": "L"}',
        ],
        [
            "phase",
            "update",
            "original",
            "--extra",
            '{"id": "other_phase", "name": "N"}',
        ],
        [
            "phase",
            "update",
            "original",
            "--extra",
            '{"id": "other_phase", "description": "D"}',
        ],
    ],
)
@pytest.mark.parametrize("colored", [False, True])
def test_update_rejects_extra_id_before_client_creation(
    runner, clean_pipefy_env, saved_cwd, oauth_env, monkeypatch, args, colored
):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color" if colored else "dumb")
    monkeypatch.setenv("FORCE_COLOR" if colored else "NO_COLOR", "1")
    oauth_env("update-reserved")
    mock_client = MagicMock()
    mock_client.get_phase_fields = AsyncMock(return_value={"phase_name": "Original"})
    mock_client.update_phase = AsyncMock(return_value={"updatePhase": {}})
    mock_client.update_phase_field = AsyncMock(return_value={"updatePhaseField": {}})
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ) as get_client:
        result = runner.invoke(app, args)
    assert result.exit_code == 2
    if colored:
        assert "\x1b[" in result.stderr
    error_text = " ".join(unstyle(result.stderr).replace("│", " ").split())
    assert "--extra" in error_text
    assert "'id'" in error_text
    assert "dedicated argument" in error_text
    get_client.assert_not_called()
    mock_client.get_phase_fields.assert_not_awaited()
    mock_client.update_phase.assert_not_awaited()
    mock_client.update_phase_field.assert_not_awaited()


def test_phase_delete_yes(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("ph-del")
    mock_client = MagicMock()
    mock_client.delete_phase = AsyncMock(return_value={"deletePhase": {}})
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["phase", "delete", "3", "--yes", "--json"])
    assert result.exit_code == 0
    mock_client.delete_phase.assert_awaited_once_with("3")


def test_field_list_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("fld-list")
    payload = {"phase_id": "1", "fields": []}
    mock_client = MagicMock()
    mock_client.get_phase_fields = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["field", "list", "--phase", "1", "--json"])
    assert result.exit_code == 0
    mock_client.get_phase_fields.assert_awaited_once_with("1", required_only=False)


@pytest.mark.parametrize(
    ("reserved_key", "value"),
    [("phase_id", "999"), ("label", "Unexpected label"), ("type", "number")],
)
def test_field_create_rejects_reserved_extra_keys(
    runner, clean_pipefy_env, saved_cwd, oauth_env, reserved_key, value
):
    oauth_env("fld-reserved")
    mock_client = MagicMock()
    mock_client.create_phase_field = AsyncMock(return_value={"createPhaseField": {}})
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ) as get_client:
        result = runner.invoke(
            app,
            [
                "field",
                "create",
                "--phase",
                "2",
                "--label",
                "Owner",
                "--type",
                "assignee_select",
                "--extra",
                json.dumps({reserved_key: value}),
            ],
        )
    assert result.exit_code == 2
    assert reserved_key in result.stderr
    get_client.assert_not_called()
    mock_client.create_phase_field.assert_not_awaited()


def test_field_create_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("fld-cr")
    mock_client = MagicMock()
    mock_client.create_phase_field = AsyncMock(return_value={"createPhaseField": {}})
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "field",
                "create",
                "--phase",
                "2",
                "--label",
                "Owner",
                "--type",
                "assignee_select",
                "--json",
            ],
        )
    assert result.exit_code == 0
    mock_client.create_phase_field.assert_awaited_once_with(
        CreatePhaseFieldInput(phase_id="2", label="Owner", type="assignee_select")
    )


def test_field_create_type_completion_offers_field_type_ids(runner):
    result = runner.invoke(
        app,
        [],
        prog_name="pipefy",
        env={
            "_PIPEFY_COMPLETE": "complete_zsh",
            "_TYPER_COMPLETE_ARGS": "pipefy field create --type checklist",
        },
    )
    assert result.exit_code == 0
    assert '"checklist_horizontal"' in result.output
    assert '"checklist_vertical"' in result.output
    assert "short_text" not in result.output


@pytest.mark.parametrize(
    ("hints", "phase_id", "pipe_id"),
    [
        ({"phase_id": "343162749"}, "343162749", None),
        ({"pipe_id": "pipe-context"}, None, "pipe-context"),
        (
            {"phase_id": "343162749", "pipe_id": "pipe-context"},
            "343162749",
            "pipe-context",
        ),
    ],
)
def test_field_update_forwards_extra_hints_for_slug_resolution(
    runner, clean_pipefy_env, saved_cwd, oauth_env, hints, phase_id, pipe_id
):
    """Field resolution hints reach the SDK without entering the mutation input."""
    oauth_env("fld-upd")
    mock_client = MagicMock()
    mock_client.update_phase_field = AsyncMock(
        return_value={"updatePhaseField": {"phase_field": {"id": "429358624"}}}
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "field",
                "update",
                "priority",
                "--extra",
                json.dumps({"label": "Priority", **hints}),
                "--json",
            ],
        )
    assert result.exit_code == 0, result.stdout
    mock_client.update_phase_field.assert_awaited_once_with(
        UpdatePhaseFieldInput(id="priority", label="Priority"),
        phase_id=phase_id,
        pipe_id=pipe_id,
    )


def test_field_delete_yes(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("fld-del")
    mock_client = MagicMock()
    mock_client.delete_phase_field = AsyncMock(return_value={"deletePhaseField": {}})
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["field", "delete", "fid-1", "--yes", "--json"],
        )
    assert result.exit_code == 0
    mock_client.delete_phase_field.assert_awaited_once_with("fid-1", pipe_uuid=None)
