"""CLI tests for ``pipefy automation simulation``."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from pipefy_cli.main import app

_READ = {
    "simulation_id": "sim-1",
    "automation_simulation": {
        "status": "success",
        "details": None,
        "simulationResult": {},
    },
    "warnings": [{"field_id": "101", "kind": "empty", "text": ""}],
    "waited_seconds": 4.0,
}


def _invoke(runner, mock_client, args):
    with patch(
        "pipefy_cli.commands._common.get_authenticated_client",
        return_value=mock_client,
    ):
        return runner.invoke(app, ["automation", "simulation", *args])


def test_simulation_reads_with_timeout_and_field_ids(
    runner: CliRunner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("sim-read")
    mock_client = MagicMock()
    mock_client.get_automation_simulation = AsyncMock(return_value=_READ)

    r = _invoke(
        runner,
        mock_client,
        [
            "sim-1",
            "--timeout",
            "10",
            "--field-id",
            "101",
            "--field-id",
            "102",
            "--json",
        ],
    )

    assert r.exit_code == 0
    assert json.loads(r.stdout) == _READ
    mock_client.get_automation_simulation.assert_awaited_once_with(
        "sim-1", timeout_seconds=10, field_ids=["101", "102"]
    )


def test_simulation_defaults_to_thirty_seconds_and_no_field_ids(
    runner: CliRunner, clean_pipefy_env, saved_cwd, oauth_env
):
    oauth_env("sim-default")
    mock_client = MagicMock()
    mock_client.get_automation_simulation = AsyncMock(return_value=_READ)

    r = _invoke(runner, mock_client, ["sim-1", "--json"])

    assert r.exit_code == 0
    mock_client.get_automation_simulation.assert_awaited_once_with(
        "sim-1", timeout_seconds=30, field_ids=None
    )


@pytest.mark.parametrize("timeout", ["-1", "61"])
def test_simulation_rejects_a_timeout_out_of_range(
    runner: CliRunner, clean_pipefy_env, saved_cwd, oauth_env, timeout
):
    oauth_env("sim-range")
    mock_client = MagicMock()
    mock_client.get_automation_simulation = AsyncMock(return_value=_READ)

    r = _invoke(runner, mock_client, ["sim-1", "--timeout", timeout, "--json"])

    assert r.exit_code == 2
    mock_client.get_automation_simulation.assert_not_called()
