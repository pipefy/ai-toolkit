"""Optional live CLI smoke tests (one read per domain when env IDs are present)."""

from __future__ import annotations

import json
import os
import re
import uuid

import pytest
from _shared.live_settings import require_live_creds
from typer.testing import CliRunner

from pipefy_cli.main import app


def _pipe_id() -> str | None:
    return os.environ.get("PIPE_BUILDING_LIVE_PIPE_ID")


def _phase_id() -> str | None:
    return os.environ.get("PIPE_FIELD_CONDITION_LIVE_PHASE_ID")


# Tests do not chdir to ``tmp_path`` and do not override ``env=`` on
# ``runner.invoke`` so the CLI loads ``.env`` from the repo root via
# ``PipefySettings`` — the same source ``require_live_creds`` reads.


@pytest.mark.integration
def test_cli_live_card_list_skips_without_pipe_id():
    require_live_creds()
    if not _pipe_id():
        pytest.skip("Set PIPE_BUILDING_LIVE_PIPE_ID for card list live smoke.")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        ["card", "list", "--pipe", _pipe_id(), "--first", "1", "--json"],
    )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")


@pytest.mark.integration
def test_cli_live_pipe_get_skips_without_pipe_id():
    require_live_creds()
    if not _pipe_id():
        pytest.skip("Set PIPE_BUILDING_LIVE_PIPE_ID for pipe get live smoke.")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["pipe", "get", _pipe_id(), "--json"])
    assert result.exit_code == 0, result.stdout + (result.stderr or "")


@pytest.mark.integration
def test_cli_live_pipe_list_requires_only_oauth():
    require_live_creds()
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["pipe", "list", "--max-per-org", "1", "--json"])
    assert result.exit_code == 0, result.stdout + (result.stderr or "")


@pytest.mark.integration
def test_cli_live_label_list_skips_without_pipe_id():
    require_live_creds()
    if not _pipe_id():
        pytest.skip("Set PIPE_BUILDING_LIVE_PIPE_ID for label list live smoke.")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["label", "list", "--pipe", _pipe_id(), "--json"])
    assert result.exit_code == 0, result.stdout + (result.stderr or "")


@pytest.mark.integration
def test_cli_live_webhook_list_skips_without_pipe_id():
    require_live_creds()
    if not _pipe_id():
        pytest.skip("Set PIPE_BUILDING_LIVE_PIPE_ID for webhook list live smoke.")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["webhook", "list", "--pipe", _pipe_id(), "--json"])
    assert result.exit_code == 0, result.stdout + (result.stderr or "")


@pytest.mark.integration
def test_cli_live_member_list_skips_without_pipe_id():
    require_live_creds()
    if not _pipe_id():
        pytest.skip("Set PIPE_BUILDING_LIVE_PIPE_ID for member list live smoke.")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["member", "list", "--pipe", _pipe_id(), "--json"])
    assert result.exit_code == 0, result.stdout + (result.stderr or "")


@pytest.mark.integration
def test_cli_live_relation_pipe_list_skips_without_pipe_id():
    require_live_creds()
    if not _pipe_id():
        pytest.skip("Set PIPE_BUILDING_LIVE_PIPE_ID for relation pipe list live smoke.")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["relation", "pipe", "list", _pipe_id(), "--json"])
    assert result.exit_code == 0, result.stdout + (result.stderr or "")


@pytest.mark.integration
def test_cli_live_table_list_requires_only_oauth():
    require_live_creds()
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["table", "list", "--first", "1", "--json"])
    assert result.exit_code == 0, result.stdout + (result.stderr or "")


@pytest.mark.integration
def test_cli_live_phase_get_skips_without_phase_id():
    require_live_creds()
    if not _phase_id():
        pytest.skip("Set PIPE_FIELD_CONDITION_LIVE_PHASE_ID for phase get live smoke.")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["phase", "get", _phase_id(), "--json"])
    assert result.exit_code == 0, result.stdout + (result.stderr or "")


@pytest.mark.integration
def test_cli_live_field_list_skips_without_phase_id():
    require_live_creds()
    if not _phase_id():
        pytest.skip("Set PIPE_FIELD_CONDITION_LIVE_PHASE_ID for field list live smoke.")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["field", "list", "--phase", _phase_id(), "--json"])
    assert result.exit_code == 0, result.stdout + (result.stderr or "")


@pytest.mark.integration
def test_cli_live_record_find_skips_without_table_id():
    require_live_creds()
    table_id = os.environ.get("CLI_LIVE_TABLE_ID")
    if not table_id:
        pytest.skip("Set CLI_LIVE_TABLE_ID for record find live smoke.")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        ["record", "find", "--table", table_id, "--first", "1", "--json"],
    )
    assert result.exit_code == 0, result.stdout + (result.stderr or "")


@pytest.mark.integration
def test_cli_live_html_interface_create_round_trips():
    """The new html-interface sub-app, exercised against a real backend.

    Unit tests mock the client, so they cannot see whether the create/get/delete
    chain actually works end to end over the real Interfaces API.
    """
    require_live_creds()
    org_uuid = os.environ.get("PIPEFY_PORTAL_ORG_UUID")
    if not org_uuid:
        pytest.skip("Set PIPEFY_PORTAL_ORG_UUID for html-interface create live smoke.")
    runner = CliRunner(mix_stderr=False)
    name = f"cli-html-create-smoke-{uuid.uuid4().hex[:8]}"
    create_result = runner.invoke(
        app,
        [
            "portal",
            "html-interface",
            "create",
            "--organization-uuid",
            org_uuid,
            "--name",
            name,
            "--html",
            "<div>cli smoke</div>",
            "--json",
        ],
    )
    if create_result.exit_code == 2 and "Permission denied" in (
        create_result.stderr or ""
    ):
        pytest.skip(f"Token lacks manage_portals on org {org_uuid}")
    # Even when create's second call (write_html_document) fails, the interface
    # itself was already created with a blank page; the CLI's own guidance names
    # its uuid in stderr. Capture it either way so a write-phase failure still
    # gets cleaned up, instead of only running the finally on a full success.
    interface_uuid: str | None = None
    if create_result.exit_code == 0:
        interface_uuid = json.loads(create_result.stdout)["uuid"]
    else:
        match = re.search(
            r"The interface \(([^)]+)\) was already created",
            create_result.stderr or "",
        )
        if match is not None:
            interface_uuid = match.group(1)
    try:
        assert create_result.exit_code == 0, create_result.stdout + (
            create_result.stderr or ""
        )
        get_result = runner.invoke(
            app, ["portal", "html-interface", "get", interface_uuid, "--json"]
        )
        assert get_result.exit_code == 0, get_result.stdout + (get_result.stderr or "")
        interface = json.loads(get_result.stdout)
        assert interface["uuid"] == interface_uuid
        content = interface["pages"][0]["elements"][0]["htmlDocument"]["content"]
        assert content == "<div>cli smoke</div>"
    finally:
        if interface_uuid is not None:
            runner.invoke(app, ["portal", "delete", interface_uuid, "--yes"])
