"""Uncaught errors in the ``pipefy`` CLI must not print frame locals."""

from __future__ import annotations

import sys

import pytest
import typer
from conftest import InMemoryKeyring
from pipefy_auth import flow
from pipefy_auth.responses import TokenResponse

from pipefy_cli.commands import auth as auth_module
from pipefy_cli.main import app as cli_app

# Short enough to print whole under rich's 80-character locals cap.
FAKE_ACCESS_TOKEN = "FAKEACCESS" + "A" * 11
FAKE_REFRESH_TOKEN = "FAKEREFRESH" + "R" * 11


def test_uncaught_error_traceback_does_not_print_locals(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fake_keyring: InMemoryKeyring,
    clean_pipefy_env,
    saved_cwd,
) -> None:
    # CliRunner swallows the exception before the excepthook runs, so the test
    # calls the app directly and then hands the exception to Typer's hook,
    # which is what the console script does.
    monkeypatch.setenv("PIPEFY_AUTH_URL", "https://x.test/realms/foo")
    monkeypatch.setenv("PIPEFY_AUTH_CLIENT_ID", "pipefy-cli")
    monkeypatch.delenv("_TYPER_STANDARD_TRACEBACK", raising=False)
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)

    def _fake_run_login(**_kwargs: object) -> flow.LoginResult:
        return flow.LoginResult(
            issuer="https://x.test/realms/foo",
            token=TokenResponse(
                access_token=FAKE_ACCESS_TOKEN,
                refresh_token=FAKE_REFRESH_TOKEN,
                expires_in=300,
            ),
        )

    def _store_session_fails(*, issuer, client_id, token):
        raise RuntimeError("boom")

    monkeypatch.setattr(auth_module, "run_login", _fake_run_login)
    monkeypatch.setattr(auth_module, "store_session", _store_session_fails)

    with pytest.raises(RuntimeError) as info:
        cli_app(["auth", "login", "--no-browser"])
    typer.main.except_hook(info.type, info.value, info.tb)

    err = capsys.readouterr().err
    assert "RuntimeError" in err
    assert "boom" in err
    assert "FAKEACCESS" not in err
    assert "FAKEREFRESH" not in err
