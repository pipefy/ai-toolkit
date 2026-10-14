from __future__ import annotations

import platform
import types

import keyring
import pytest
from pipefy_auth import storage

from pipefy_cli.commands import _auth_keychain_hints as hints


@pytest.mark.parametrize(
    ("system", "required", "forbidden"),
    [
        (
            "Darwin",
            [
                "errSecInvalidOwnerEdit",
                "pipefy auth logout",
                "security delete-generic-password -s pipefy",
                "Terminal.app",
                "Always Allow",
                "PIPEFY_KEYCHAIN_BACKEND=file",
                "PIPEFY_TOKEN",
                "docs/cli/auth.md",
            ],
            ["Secret Service", "errSecParam"],
        ),
        (
            "Linux",
            [
                "Secret Service",
                "PIPEFY_KEYCHAIN_BACKEND=file",
                "PIPEFY_TOKEN",
                "docs/cli/auth.md",
            ],
            ["Terminal.app", "Credential Manager"],
        ),
        (
            "Windows",
            ["pipefy auth status", "docs/cli/auth.md"],
            ["Credential Manager", "Secret Service", "Terminal.app"],
        ),
        ("FreeBSD", ["pipefy auth status", "docs/cli/auth.md"], []),
    ],
)
def test_keychain_hint_for_platform(
    monkeypatch: pytest.MonkeyPatch,
    system: str,
    required: list[str],
    forbidden: list[str],
) -> None:
    monkeypatch.setattr(platform, "system", lambda: system)
    hint = hints.keychain_store_failure_hint(backend="Keyring")
    for fragment in required:
        assert fragment in hint
    for fragment in forbidden:
        assert fragment not in hint


@pytest.mark.parametrize(
    ("system", "backend"),
    [("Darwin", "PlaintextKeyring"), ("Windows", "EncryptedKeyring")],
)
def test_file_backend_hint_ignores_platform(
    monkeypatch: pytest.MonkeyPatch,
    system: str,
    backend: str,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: system)
    hint = hints.keychain_store_failure_hint(backend=backend)
    assert "config directory is writable" in hint
    assert "errSecInvalidOwnerEdit" not in hint
    assert "Credential Manager" not in hint
    assert "docs/cli/auth.md" in hint


def test_dpapi_backend_hint_names_dpapi_and_the_plaintext_escape_hatch() -> None:
    hint = hints.keychain_store_failure_hint(backend="EncryptedKeyring")
    assert "DPAPI" in hint
    assert "PIPEFY_KEYCHAIN_BACKEND=file (plaintext on disk)" in hint


_STORE = "/home/someone/.config/pipefy/keyring.cfg"
_FILE_STORE_REMEDY = "fix its permissions or delete the file"


@pytest.mark.parametrize("backend", ["PlaintextKeyring", "EncryptedKeyring"])
def test_file_backend_hint_without_a_store_path_does_not_name_a_file(
    backend: str,
) -> None:
    hint = hints.keychain_store_failure_hint(backend=backend)
    assert "cannot be read or parsed" not in hint
    assert "delete the file" not in hint


@pytest.mark.parametrize("backend", ["PlaintextKeyring", "EncryptedKeyring"])
def test_file_backend_hint_says_to_repair_or_delete_the_named_store(
    backend: str,
) -> None:
    hint = hints.keychain_store_failure_hint(backend=backend, store_path=_STORE)
    assert (
        f"If {_STORE} exists but cannot be read or parsed, {_FILE_STORE_REMEDY}, "
        "then run `pipefy auth login` again." in hint
    )
    assert "config directory is writable" in hint
    assert "docs/cli/auth.md" in hint


def test_os_keychain_logout_delete_failure_points_at_the_keychain() -> None:
    message = hints.logout_delete_failure_message(cause="locked", store_path=None)
    assert "remove it manually via your OS keychain (service: 'pipefy')" in message
    assert "delete the file" not in message


def test_file_store_logout_delete_failure_names_the_file() -> None:
    message = hints.logout_delete_failure_message(cause="denied", store_path=_STORE)
    assert message.startswith(
        "Could not delete local session from the keychain: denied."
    )
    assert f"may still be present in {_STORE}; {_FILE_STORE_REMEDY}." in message
    assert "auth login" not in message
    assert "OS keychain" not in message


def test_os_keychain_presence_unknown_points_at_the_keychain() -> None:
    message = hints.logout_presence_unknown_message(issuer="iss", store_path=None)
    assert "check for it manually via your OS keychain (service: 'pipefy')" in message


def test_file_store_presence_unknown_names_the_file() -> None:
    message = hints.logout_presence_unknown_message(issuer="iss", store_path=_STORE)
    assert "Could not read the keychain to check for a stored session (iss)" in message
    assert f"may still be present in {_STORE}; {_FILE_STORE_REMEDY}." in message
    assert "auth login" not in message
    assert "OS keychain" not in message


@pytest.mark.parametrize(
    ("choice", "platform_name", "expected_name", "expected_fragment"),
    [
        ("file", "darwin", "PlaintextKeyring", "config directory is writable"),
        ("auto", "win32", "EncryptedKeyring", "DPAPI"),
    ],
)
def test_installed_file_backends_report_the_names_the_hint_dispatches_on(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    choice: str,
    platform_name: str,
    expected_name: str,
    expected_fragment: str,
) -> None:
    """The hint matches on the class name, so a renamed class (even with an
    alias kept under the old name) would fall through to the OS keychain hint."""
    monkeypatch.setattr(storage, "sys", types.SimpleNamespace(platform=platform_name))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    original = keyring.get_keyring()
    try:
        storage.configure_keychain_backend(choice)
        name = storage.keychain_backend_name()
    finally:
        keyring.set_keyring(original)

    assert name == expected_name
    assert expected_fragment in hints.keychain_store_failure_hint(backend=name)
