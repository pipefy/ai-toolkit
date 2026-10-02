"""Tests for ``pipefy relation`` and ``pipefy member`` subcommands."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from pipefy_cli.main import app


def test_relation_table_relations_list_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("rel-tbl")
    payload = {"table_relations": []}
    mock_client = MagicMock()
    mock_client.get_table_relations = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app, ["relation", "table", "list", "--ids", "10,20", "--json"]
        )
    assert result.exit_code == 0
    mock_client.get_table_relations.assert_awaited_once_with(["10", "20"])


def test_relation_table_relations_list_empty_ids_bad_parameter(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("rel-tbl-bad")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app, ["relation", "table", "list", "--ids", ",", "--json"]
        )
    assert result.exit_code == 2
    mock_client.get_table_relations.assert_not_called()


def test_relation_pipe_list_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("rel-p")
    payload = {"pipe": {"relations": []}}
    mock_client = MagicMock()
    mock_client.get_pipe_relations = AsyncMock(return_value=payload)
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(app, ["relation", "pipe", "list", "10", "--json"])
    assert result.exit_code == 0
    mock_client.get_pipe_relations.assert_awaited_once_with("10")


def test_member_invite_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("mem-inv")
    mock_client = MagicMock()
    mock_client.invite_members = AsyncMock(return_value={"inviteMembers": {}})
    members = json.dumps([{"email": "a@b.com", "role_name": "admin"}])
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["member", "invite", "--pipe", "1", "--members", members, "--json"],
        )
    assert result.exit_code == 0
    mock_client.invite_members.assert_awaited_once_with(
        "1", [{"email": "a@b.com", "role_name": "admin"}]
    )


def test_member_add_service_account_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("mem-sa")
    mock_client = MagicMock()
    mock_client.add_service_account_to_pipe = AsyncMock(
        return_value={"inviteMembers": {}}
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "member",
                "add-service-account",
                "--pipe",
                "1",
                "--email",
                "svc@x.com",
                "--role",
                "admin",
                "--json",
            ],
        )
    assert result.exit_code == 0
    mock_client.add_service_account_to_pipe.assert_awaited_once_with(
        "1", "svc@x.com", "admin"
    )


def test_member_add_service_account_defaults_to_admin_role(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("mem-sa-def")
    mock_client = MagicMock()
    mock_client.add_service_account_to_pipe = AsyncMock(
        return_value={"inviteMembers": {}}
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["member", "add-service-account", "--pipe", "1", "--email", "svc@x.com"],
        )
    assert result.exit_code == 0
    mock_client.add_service_account_to_pipe.assert_awaited_once_with(
        "1", "svc@x.com", "admin"
    )


def test_member_add_service_account_blank_email_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("mem-sa-bad")
    mock_client = MagicMock()
    mock_client.add_service_account_to_pipe = AsyncMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "member",
                "add-service-account",
                "--pipe",
                "1",
                "--email",
                "   ",
            ],
        )
    assert result.exit_code == 2
    mock_client.add_service_account_to_pipe.assert_not_called()


def test_member_remove_happy_path_json(runner, clean_pipefy_env, saved_cwd, oauth_env):
    oauth_env("mem-rm-ok")
    mock_client = MagicMock()
    mock_client.remove_member_from_pipe = AsyncMock(
        return_value={"data": {"removeMembersFromPipe": {}}, "warning": None}
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "member",
                "remove",
                "--pipe",
                "1",
                "--user-ids",
                "u1,u2",
                "--yes",
                "--json",
            ],
        )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "warning" in payload
    assert payload["warning"] is None
    assert payload["data"] == {"removeMembersFromPipe": {}}
    mock_client.remove_member_from_pipe.assert_awaited_once_with("1", ["u1", "u2"])


def test_member_remove_prints_warning_when_present(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("mem-rm-warn")
    warning = (
        "API returned success but member(s) [u1] are still present in the pipe. "
        "They may have org-level permissions that override pipe-level removal."
    )
    mock_client = MagicMock()
    mock_client.remove_member_from_pipe = AsyncMock(
        return_value={"data": {"removeMembersFromPipe": {}}, "warning": warning}
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["member", "remove", "--pipe", "1", "--user-ids", "u1", "--yes"],
        )
    assert result.exit_code == 0
    compact = " ".join(result.stdout.split())
    assert "still present in the pipe" in compact
    assert "org-level permissions" in compact
    mock_client.remove_member_from_pipe.assert_awaited_once_with("1", ["u1"])


def test_member_invite_members_missing_role_bad_parameter(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("mem-inv-bad")
    mock_client = MagicMock()
    members = json.dumps([{"email": "a@b.com"}])
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            ["member", "invite", "--pipe", "1", "--members", members, "--json"],
        )
    assert result.exit_code == 2
    mock_client.invite_members.assert_not_called()


def test_relation_pipe_create_empty_name_exit_2(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("rel-pc-empty")
    mock_client = MagicMock()
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "relation",
                "pipe",
                "create",
                "--parent",
                "1",
                "--child",
                "2",
                "--name",
                "   ",
                "--json",
            ],
        )
    assert result.exit_code == 2
    mock_client.create_pipe_relation.assert_not_called()


def test_relation_card_delete_internal_api_json(
    runner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("rel-cc-del")
    mock_client = MagicMock()
    mock_client.delete_card_relation = AsyncMock(
        return_value={"deleteCardRelation": {}}
    )
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        result = runner.invoke(
            app,
            [
                "relation",
                "card",
                "delete",
                "--child",
                "1",
                "--parent",
                "2",
                "--source",
                "3",
                "--yes",
                "--json",
            ],
        )
    assert result.exit_code == 0
    mock_client.delete_card_relation.assert_awaited_once_with("1", "2", "3")
