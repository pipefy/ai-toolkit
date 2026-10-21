"""Remediation text for session-store failures in ``pipefy auth login`` and ``logout``.

A file store (``keyring.cfg``, ``keyring-dpapi.cfg``) is repaired by fixing or
deleting the file, so its messages name the file; an OS keychain is repaired
through the keychain itself.
"""

from __future__ import annotations

import platform

from pipefy_infra.config import config_dir

from pipefy_cli._docs import DOCS_CLI_AUTH_REF

_KEYCHAIN_SERVICE = "pipefy"

_FILE_STORE_REMEDY = "fix its permissions or delete the file"

_ESCAPE_HATCH = (
    f"Alternatively set PIPEFY_KEYCHAIN_BACKEND=file (plaintext on disk) or "
    f"use a static PIPEFY_TOKEN. See {DOCS_CLI_AUTH_REF}."
)

_LINUX_HINT = (
    "On headless Linux, ensure a Secret Service daemon "
    "(gnome-keyring, kwallet) is running. "
    f"{_ESCAPE_HATCH}"
)

_MACOS_HINT = (
    "macOS Keychain rejected the write (often errSecInvalidOwnerEdit, -25244: "
    "invalid attempt to change the owner of this item). Clear the entry with "
    "`pipefy auth logout`; if that fails, remove it directly with "
    "`security delete-generic-password -s pipefy`. Then run "
    "`pipefy auth login` again from Terminal.app and click Always Allow if "
    f"prompted. {_ESCAPE_HATCH}"
)

_GENERIC_HINT = (
    f"Run `pipefy auth status` to inspect the active backend, or see "
    f"{DOCS_CLI_AUTH_REF} for keychain troubleshooting."
)


def keychain_store_failure_hint(*, backend: str, store_path: str | None = None) -> str:
    """Return a remediation hint after ``store_session`` fails post-login.

    Args:
        backend: Class name of the active keyring backend.
        store_path: The file store's path when the backend is a file store
            (see ``pipefy_auth.keychain_store_path``), else ``None``.
    """
    if backend == "PlaintextKeyring":
        return (
            f"Ensure the config directory is writable ({config_dir()}), "
            f"or use a static PIPEFY_TOKEN. {_unreadable_store_hint(store_path)}"
            f"See {DOCS_CLI_AUTH_REF}."
        )
    if backend == "EncryptedKeyring":
        return (
            f"Ensure the config directory is writable ({config_dir()}) and "
            f"that DPAPI is available for this Windows account (some service "
            f"accounts have no user profile). {_unreadable_store_hint(store_path)}"
            f"{_ESCAPE_HATCH}"
        )
    return _keychain_hint_for_platform()


def logout_delete_failure_message(*, cause: str, store_path: str | None) -> str:
    """Return the ``pipefy auth logout`` error for a delete the backend rejected."""
    if store_path is None:
        remedy = (
            "The stored credential may still be present; remove it manually "
            f"via your OS keychain (service: '{_KEYCHAIN_SERVICE}')."
        )
    else:
        remedy = (
            f"The stored credential may still be present in {store_path}; "
            f"{_FILE_STORE_REMEDY}."
        )
    return (
        f"Could not delete local session from the keychain: {cause}. {remedy} "
        f"See {DOCS_CLI_AUTH_REF}."
    )


def logout_presence_unknown_message(*, issuer: str, store_path: str | None) -> str:
    """Return the ``pipefy auth logout`` error when presence could not be read."""
    if store_path is None:
        remedy = (
            "A credential may still be present; check for it manually via your "
            f"OS keychain (service: '{_KEYCHAIN_SERVICE}')."
        )
    else:
        remedy = (
            f"A credential may still be present in {store_path}; {_FILE_STORE_REMEDY}."
        )
    return (
        "Could not read the keychain to check for a stored session "
        f"({issuer}), and no entry was removed. {remedy} See {DOCS_CLI_AUTH_REF}."
    )


def _unreadable_store_hint(store_path: str | None) -> str:
    if store_path is None:
        return ""
    return (
        f"If {store_path} exists but cannot be read or parsed, {_FILE_STORE_REMEDY}, "
        "then run `pipefy auth login` again. "
    )


def _keychain_hint_for_platform() -> str:
    system = platform.system()
    if system == "Darwin":
        return _MACOS_HINT
    if system == "Linux":
        return _LINUX_HINT
    return _GENERIC_HINT


__all__ = [
    "keychain_store_failure_hint",
    "logout_delete_failure_message",
    "logout_presence_unknown_message",
]
