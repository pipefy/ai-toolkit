from __future__ import annotations

import platform

import pytest

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
