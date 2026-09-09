"""Native Windows DPAPI coverage; all artifacts stay in pytest's temporary dir."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from pipefy_auth.encrypted_file_keyring import EncryptedFileKeyring
from pipefy_auth.keychain_choice import WRAPPING_KEY_BYTES

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI")


@pytest.fixture
def dpapi():
    from pipefy_auth import wrapping_key_windows

    return wrapping_key_windows


def test_native_dpapi_round_trip_uses_user_scope_without_ui(dpapi, mocker):
    protect = mocker.spy(dpapi, "_CryptProtectData")
    unprotect = mocker.spy(dpapi, "_CryptUnprotectData")
    plaintext = b"\x00" + os.urandom(WRAPPING_KEY_BYTES - 2) + b"\x00"

    ciphertext = dpapi.dpapi_protect(plaintext)

    assert ciphertext != plaintext
    assert plaintext not in ciphertext
    assert dpapi.dpapi_unprotect(ciphertext) == plaintext
    # CRYPTPROTECT_UI_FORBIDDEN (1) only: never LOCAL_MACHINE (4), which
    # would make the wrapping key decryptable by other users on the host.
    assert protect.call_args.args[5] == 1
    assert unprotect.call_args.args[5] == 1


def test_native_dpapi_rejects_modified_ciphertext(dpapi):
    protected = dpapi.dpapi_protect(os.urandom(WRAPPING_KEY_BYTES))
    corrupted = protected[:-1] + bytes([protected[-1] ^ 1])

    with pytest.raises(OSError, match="CryptUnprotectData"):
        dpapi.dpapi_unprotect(corrupted)


def test_native_wrapping_key_persists_across_instances(dpapi, tmp_path: Path):
    path = tmp_path / "wrapping.key"
    writer = dpapi.WindowsDpapiWrappingKey(path)
    assert writer.load() is None
    assert not path.exists()

    key = writer.load_or_create()
    protected = path.read_bytes()

    assert len(key) == WRAPPING_KEY_BYTES
    assert key not in protected
    assert dpapi.dpapi_unprotect(protected) == key
    assert dpapi.WindowsDpapiWrappingKey(path).load() == key
    assert dpapi.WindowsDpapiWrappingKey(path).load_or_create() == key
    assert path.read_bytes() == protected


def test_native_wrapping_key_is_unchanged_by_session_rotations(dpapi, tmp_path: Path):
    wrapping_path = tmp_path / "wrapping.key"
    session_path = tmp_path / "session.enc"
    key = dpapi.WindowsDpapiWrappingKey(wrapping_path).load_or_create()
    protected = wrapping_path.read_bytes()

    for generation in range(3):
        token = f"token-{generation}-" + "x" * 8192
        writer = EncryptedFileKeyring(
            session_path, dpapi.WindowsDpapiWrappingKey(wrapping_path)
        )
        writer.set_password("pipefy", "native-dpapi-test", token)
        reader = EncryptedFileKeyring(
            session_path, dpapi.WindowsDpapiWrappingKey(wrapping_path)
        )

        assert reader.get_password("pipefy", "native-dpapi-test") == token
        assert token.encode() not in session_path.read_bytes()
        assert wrapping_path.read_bytes() == protected
        assert dpapi.WindowsDpapiWrappingKey(wrapping_path).load() == key


@pytest.mark.parametrize("operation", ["load", "load_or_create"])
def test_corrupt_dpapi_file_is_not_overwritten_or_cached(
    dpapi, tmp_path: Path, operation: str
):
    path = tmp_path / "wrapping.key"
    key = os.urandom(WRAPPING_KEY_BYTES)
    protected = dpapi.dpapi_protect(key)
    corrupt = protected[: len(protected) // 2]
    path.write_bytes(corrupt)
    store = dpapi.WindowsDpapiWrappingKey(path)

    with pytest.raises(OSError, match="CryptUnprotectData failed"):
        getattr(store, operation)()

    assert path.read_bytes() == corrupt
    assert store._cached is None
    path.write_bytes(protected)
    assert getattr(store, operation)() == key


@pytest.mark.parametrize("operation", ["load", "load_or_create"])
def test_native_dpapi_rejects_wrong_length_wrapping_key(
    dpapi, tmp_path: Path, operation: str
):
    path = tmp_path / "wrapping.key"
    protected = dpapi.dpapi_protect(b"short")
    path.write_bytes(protected)
    store = dpapi.WindowsDpapiWrappingKey(path)

    with pytest.raises(OSError, match="expected 32"):
        getattr(store, operation)()

    assert path.read_bytes() == protected
    assert store._cached is None
