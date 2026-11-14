"""Tests for ``pipefy pipe`` subcommands."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from pipefy_sdk import PipePhaseSetupError
from pipefy_sdk.graphql_inputs import (
    RepoPreferenceInput,
    UpdatePipeInput,
)

from pipefy_cli.main import app


def test_pipe_start_form_required_only_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("pipe-start-form-req")
    payload = {"start_form_fields": [{"id": "f1", "required": True}]}
    mock_client = MagicMock()
    mock_client.get_start_form_fields = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app, ["pipe", "start-form", "10", "--required-only", "--json"]
        )
    assert result.exit_code == 0
    assert json.loads(result.stdout) == payload
    mock_client.get_start_form_fields.assert_awaited_once_with("10", required_only=True)


def test_pipe_start_form_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("pipe-start-form")
    payload = {"start_form_fields": []}
    mock_client = MagicMock()
    mock_client.get_start_form_fields = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["pipe", "start-form", "10", "--json"])
    assert result.exit_code == 0
    mock_client.get_start_form_fields.assert_awaited_once_with(
        "10", required_only=False
    )


def test_pipe_get_rejects_option_like_positional_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("pipe-get-bad-opt")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["pipe", "get", "--bad", "--json"])
    assert result.exit_code == 2
    mock_client.get_pipe.assert_not_called()


def test_table_delete_accepts_leading_hyphen_table_id(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("table-del-hyphen")
    mock_client = MagicMock()
    mock_client.delete_table = AsyncMock(
        return_value={"deleteTable": {"success": True}}
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["table", "delete", "-ZocGcM0", "--yes", "--json"],
        )
    assert result.exit_code == 0, result.stderr
    mock_client.delete_table.assert_awaited_once_with("-ZocGcM0")


def test_pipe_get_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("pipe-get")
    payload = {"pipe": {"id": "10", "name": "P"}}
    mock_client = MagicMock()
    mock_client.get_pipe = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["pipe", "get", "10", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == payload
    mock_client.get_pipe.assert_awaited_once_with("10")


def test_pipe_get_json_includes_phase_cards_count(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("pipe-get-inventory")
    payload = {
        "pipe": {
            "id": "10",
            "name": "P",
            "startFormPhaseId": "100",
            "phases": [{"id": "200", "name": "Done", "cards_count": 3}],
        }
    }
    mock_client = MagicMock()
    mock_client.get_pipe = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["pipe", "get", "10", "--json"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["pipe"]["phases"][0]["cards_count"] == 3


def test_pipe_list_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("pipe-list")
    payload = {"organizations": []}
    mock_client = MagicMock()
    mock_client.search_pipes = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["pipe", "list", "--name", "Invoices", "--max-per-org", "50", "--json"],
        )
    assert result.exit_code == 0
    mock_client.search_pipes.assert_awaited_once_with(
        "Invoices",
        max_pipes_per_org=50,
    )


def test_pipe_create_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("pipe-create")
    payload = {"createPipe": {"pipe": {"id": "301234567"}}}
    mock_client = MagicMock()
    mock_client.create_pipe = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["pipe", "create", "My Pipe", "--org", "555", "--json"],
        )
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"createPipe": {"pipe": {"id": "301234567"}}}
    mock_client.create_pipe.assert_awaited_once_with(
        "My Pipe", "555", phases=None, start_form_fields=None, labels=None
    )


def test_pipe_create_passes_phases_start_form_fields_and_labels(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("pipe-create-phases")
    phases = [{"name": "Triage"}, {"name": "Approved", "done": True}]
    fields = [{"label": "Amount", "type_id": "currency", "required": True}]
    labels = [{"name": "Urgent", "color": "#f00"}]
    mock_client = MagicMock()
    mock_client.create_pipe = AsyncMock(
        return_value={"createPipe": {"pipe": {"id": "1"}}}
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "pipe",
                "create",
                "Purchases",
                "--org",
                "555",
                "--phases",
                json.dumps(phases),
                "--start-form-fields",
                json.dumps(fields),
                "--labels",
                json.dumps(labels),
                "--json",
            ],
        )
    assert result.exit_code == 0
    mock_client.create_pipe.assert_awaited_once_with(
        "Purchases", "555", phases=phases, start_form_fields=fields, labels=labels
    )


def test_pipe_create_phases_not_a_json_array_of_objects_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("pipe-create-bad-phases")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["pipe", "create", "P", "--org", "1", "--phases", '["Triage"]'],
        )
    assert result.exit_code == 2
    mock_client.create_pipe.assert_not_called()


def test_pipe_create_unknown_phase_key_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("pipe-create-phase-key")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "pipe",
                "create",
                "P",
                "--org",
                "1",
                "--phases",
                '[{"name": "Triage", "index": 1}]',
            ],
        )
    assert result.exit_code == 2
    mock_client.create_pipe.assert_not_called()


def test_pipe_create_phase_setup_error_names_the_pipe_exit_1(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("pipe-create-setup-error")
    mock_client = MagicMock()
    mock_client.create_pipe = AsyncMock(
        side_effect=PipePhaseSetupError(
            pipe_id="1", created_phases=[], reason="Phase not saved"
        )
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["pipe", "create", "P", "--org", "1", "--phases", '[{"name": "A"}]'],
        )
    assert result.exit_code == 1
    assert "Pipe 1 was created" in result.stderr


def test_pipe_create_whitespace_name_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("pipe-bad-name")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["pipe", "create", "   ", "--org", "1", "--json"])
    assert result.exit_code == 2
    mock_client.create_pipe.assert_not_called()


def test_pipe_update_preferences_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("pipe-upd")
    payload = {"updatePipe": {"pipe": {"id": "10"}}}
    mock_client = MagicMock()
    mock_client.update_pipe = AsyncMock(return_value=payload)
    # A real RepoPreferenceInput field: the typed input rejects anything else
    # by name, which is what Pipefy does with the payload anyway.
    prefs = {"findable": True}
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "pipe",
                "update",
                "10",
                "--preferences",
                json.dumps(prefs),
                "--json",
            ],
        )
    assert result.exit_code == 0
    mock_client.update_pipe.assert_awaited_once_with(
        UpdatePipeInput(id="10", preferences=RepoPreferenceInput(findable=True))
    )


def test_pipe_update_no_attributes_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("pipe-upd-none")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["pipe", "update", "10", "--json"])
    assert result.exit_code == 2
    mock_client.update_pipe.assert_not_called()


def test_pipe_delete_yes(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("pipe-del")
    payload = {"deletePipe": {"success": True}}
    mock_client = MagicMock()
    mock_client.delete_pipe = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["pipe", "delete", "10", "--yes", "--json"])
    assert result.exit_code == 0
    mock_client.delete_pipe.assert_awaited_once_with("10")


def test_pipe_clone_with_org(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("pipe-clone")
    payload = {"clonePipes": {}}
    mock_client = MagicMock()
    mock_client.clone_pipe = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["pipe", "clone", "301", "--org", "777", "--json"],
        )
    assert result.exit_code == 0
    mock_client.clone_pipe.assert_awaited_once_with(
        "301",
        organization_id="777",
    )


def test_pipe_clone_without_org_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("pipe-clone-no-org")
    payload = {"clonePipes": {}}
    mock_client = MagicMock()
    mock_client.clone_pipe = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["pipe", "clone", "301", "--json"])
    assert result.exit_code == 0
    mock_client.clone_pipe.assert_awaited_once_with(
        "301",
        organization_id=None,
    )


def test_pipe_update_preferences_empty_object_bad_parameter(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("pipe-upd-empty-pref")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["pipe", "update", "10", "--preferences", "{}", "--json"],
        )
    assert result.exit_code == 2
    mock_client.update_pipe.assert_not_called()


def test_phase_targets_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("ph-targets")
    payload = {
        "phase": {
            "id": "342182335",
            "name": "Doing",
            "cards_can_be_moved_to_phases": [{"id": "200", "name": "Done"}],
        }
    }
    mock_client = MagicMock()
    mock_client.get_phase_allowed_move_targets = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["phase", "targets", "342182335", "--json"],
        )
    assert result.exit_code == 0
    assert json.loads(result.stdout) == payload
    mock_client.get_phase_allowed_move_targets.assert_awaited_once_with("342182335")
    mock_client.set_phase_move_targets.assert_not_called()


def _invoke_phase_targets(runner, mock_client, args):
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        return runner.invoke(app, ["phase", "targets", "5001", *args])


def test_phase_targets_add_keeps_the_current_connections(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("ph-targets-add")
    payload = {
        "phase": {
            "id": "5001",
            "name": "Doing",
            "cards_can_be_moved_to_phases": [
                {"id": "200", "name": "Done"},
                {"id": "300", "name": "Rejected"},
            ],
        }
    }
    mock_client = MagicMock()
    mock_client.set_phase_move_targets = AsyncMock(return_value=payload)

    result = _invoke_phase_targets(
        runner, mock_client, ["--add", "300", "--add", "400", "--json"]
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout) == payload
    mock_client.set_phase_move_targets.assert_awaited_once_with(
        "5001", ["300", "400"], replace=False
    )


def test_phase_targets_set_replaces_the_connections(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("ph-targets-set")
    mock_client = MagicMock()
    mock_client.set_phase_move_targets = AsyncMock(return_value={"phase": {}})

    result = _invoke_phase_targets(runner, mock_client, ["--set", "300", "--json"])

    assert result.exit_code == 0
    mock_client.set_phase_move_targets.assert_awaited_once_with(
        "5001", ["300"], replace=True
    )


def test_phase_targets_rejects_add_with_set(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("ph-targets-both")
    mock_client = MagicMock()
    mock_client.set_phase_move_targets = AsyncMock()

    result = _invoke_phase_targets(
        runner, mock_client, ["--add", "300", "--set", "400"]
    )

    assert result.exit_code == 2
    assert "only one of" in result.stderr
    mock_client.set_phase_move_targets.assert_not_called()


def test_phase_targets_clear_removes_every_connection(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("ph-targets-clear")
    mock_client = MagicMock()
    mock_client.set_phase_move_targets = AsyncMock(return_value={"phase": {}})

    result = _invoke_phase_targets(runner, mock_client, ["--clear", "--json"])

    assert result.exit_code == 0
    mock_client.set_phase_move_targets.assert_awaited_once_with(
        "5001", [], replace=True
    )


def test_phase_targets_rejects_clear_with_add(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("ph-targets-clear-add")
    mock_client = MagicMock()
    mock_client.set_phase_move_targets = AsyncMock()

    result = _invoke_phase_targets(runner, mock_client, ["--clear", "--add", "300"])

    assert result.exit_code == 2
    assert "only one of" in result.stderr
    mock_client.set_phase_move_targets.assert_not_called()


def test_phase_targets_value_error_exits_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("ph-targets-blank")
    mock_client = MagicMock()
    mock_client.set_phase_move_targets = AsyncMock(
        side_effect=ValueError("target_phase_ids is empty")
    )

    result = _invoke_phase_targets(runner, mock_client, ["--add", " "])

    assert result.exit_code == 2
    assert "target_phase_ids is empty" in result.stderr


def test_phase_count_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("ph-count")
    payload = {
        "phase_id": "342182335",
        "phase_name": "Doing",
        "cards_count": 7,
    }
    mock_client = MagicMock()
    mock_client.get_phase = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["phase", "count", "342182335", "--json"],
        )
    assert result.exit_code == 0
    assert json.loads(result.stdout) == payload
    mock_client.get_phase.assert_awaited_once_with("342182335")


def test_phase_count_not_found_exit_2(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("ph-count-missing")
    mock_client = MagicMock()
    mock_client.get_phase = AsyncMock(
        side_effect=ValueError("phase.cards_count missing from response")
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["phase", "count", "999", "--json"],
        )
    assert result.exit_code == 2
    assert "not found" in result.stderr.lower()
    mock_client.get_phase.assert_awaited_once_with("999")


def test_phase_cards_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("ph-cards-list")
    payload = {
        "phase": {
            "id": "342182335",
            "cards": {
                "edges": [{"node": {"id": "1", "title": "A"}}],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "totalCount": 1,
            },
        }
    }
    mock_client = MagicMock()
    mock_client.get_phase_cards = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["phase", "cards", "342182335", "--first", "50", "--after", "c1", "--json"],
        )
    assert result.exit_code == 0
    assert json.loads(result.stdout) == payload
    mock_client.get_phase_cards.assert_awaited_once_with(
        "342182335",
        first=50,
        after="c1",
        include_fields=False,
    )


def test_phase_cards_first_out_of_range_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    # Help promises 1-500; the shared validate_cards_page_size clamp must reject
    # an out-of-range --first before any API call (parity with `card list`).
    oauth_env("ph-cards-bad-first")
    mock_client = MagicMock()
    mock_client.get_phase_cards = AsyncMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["phase", "cards", "342182335", "--first", "501", "--json"],
        )
    assert result.exit_code == 2
    mock_client.get_phase_cards.assert_not_called()
