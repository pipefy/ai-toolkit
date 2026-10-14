"""DPAPI keyring round-trip; runs only on Windows (CI job ``auth-windows``).

The DPAPI backend binds CRYPT32.DLL, so these tests skip on other platforms.
"""

from __future__ import annotations

import base64
import configparser
import os
import sys
from collections.abc import Iterator
from pathlib import Path

import keyring
import pytest

from pipefy_auth.responses import TokenResponse
from pipefy_auth.storage import (
    configure_keychain_backend,
    delete_session,
    load_session,
    session_entry_presence,
    store_session,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(sys.platform != "win32", reason="DPAPI requires Windows"),
]

_ISSUER = "https://example.test/realms/pipefy"
_CLIENT_ID = "pipefy-cli"
_CREDENTIAL_MANAGER_BLOB_LIMIT = 2560


@pytest.fixture
def appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point ``config_dir()`` at ``tmp_path`` and restore the keyring afterwards."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    original = keyring.get_keyring()
    yield tmp_path
    keyring.set_keyring(original)


def _production_sized_token() -> TokenResponse:
    # Lengths measured from a production login (access, refresh, ID token).
    return TokenResponse(
        access_token="A" * 1514,
        refresh_token="R" * 677,
        id_token="I" * 1171,
        expires_in=300,
        refresh_expires_in=0,
        scope="openid offline_access email profile",
    )


def test_auto_backend_on_windows_is_dpapi_file_under_config_dir(appdata: Path) -> None:
    from keyrings.alt.Windows import EncryptedKeyring

    configure_keychain_backend("auto")

    backend = keyring.get_keyring()
    assert isinstance(backend, EncryptedKeyring)
    assert backend.file_path == str(appdata / "pipefy" / "keyring-dpapi.cfg")


def test_session_over_credential_manager_limit_round_trips(appdata: Path) -> None:
    configure_keychain_backend("auto")
    token = _production_sized_token()

    stored = store_session(issuer=_ISSUER, client_id=_CLIENT_ID, token=token)

    blob = stored.model_dump_json()
    assert len(blob.encode("utf-16-le")) > _CREDENTIAL_MANAGER_BLOB_LIMIT
    loaded = load_session(issuer=_ISSUER, client_id=_CLIENT_ID)
    assert loaded == stored


def _stored_value_bytes(appdata: Path) -> bytes:
    # The file backend base64-encodes every value, so plaintext only shows
    # after decoding; assert on the decoded bytes.
    store = configparser.RawConfigParser()
    store.read(appdata / "pipefy" / "keyring-dpapi.cfg", encoding="utf-8")
    (value,) = (v for _, v in store.items("pipefy"))
    return base64.decodebytes(value.encode())


def test_session_is_encrypted_at_rest(appdata: Path) -> None:
    configure_keychain_backend("auto")
    stored = store_session(
        issuer=_ISSUER, client_id=_CLIENT_ID, token=_production_sized_token()
    )

    decoded = _stored_value_bytes(appdata)
    assert b"A" * 64 not in decoded
    assert b'"access_token"' not in decoded
    assert decoded != stored.model_dump_json().encode()


def test_delete_session_removes_the_dpapi_entry(appdata: Path) -> None:
    configure_keychain_backend("auto")
    store_session(issuer=_ISSUER, client_id=_CLIENT_ID, token=_production_sized_token())
    assert session_entry_presence(issuer=_ISSUER, client_id=_CLIENT_ID) == "present"

    assert delete_session(issuer=_ISSUER, client_id=_CLIENT_ID) is True
    assert session_entry_presence(issuer=_ISSUER, client_id=_CLIENT_ID) == "absent"


def test_undecryptable_entry_is_unknown_and_deletable(appdata: Path) -> None:
    """A value DPAPI cannot decrypt (another account, a reset password) must not
    crash reads, and logout must still be able to remove it."""
    configure_keychain_backend("auto")
    store_session(issuer=_ISSUER, client_id=_CLIENT_ID, token=_production_sized_token())
    path = appdata / "pipefy" / "keyring-dpapi.cfg"
    store = configparser.RawConfigParser()
    store.read(path, encoding="utf-8")
    (option,) = store.options("pipefy")
    store.set("pipefy", option, "\n" + base64.encodebytes(os.urandom(64)).decode())
    with path.open("w", encoding="utf-8") as handle:
        store.write(handle)

    assert load_session(issuer=_ISSUER, client_id=_CLIENT_ID) is None
    assert session_entry_presence(issuer=_ISSUER, client_id=_CLIENT_ID) == "unknown"
    assert delete_session(issuer=_ISSUER, client_id=_CLIENT_ID) is True
    assert session_entry_presence(issuer=_ISSUER, client_id=_CLIENT_ID) == "absent"
