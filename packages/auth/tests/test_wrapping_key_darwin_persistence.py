"""Exercise the default ACL using synthetic data in a private macOS Keychain.

Every item query names the temporary keychain explicitly. The default keychain
and search list are never set. Native calls run in a subprocess with Keychain UI
disabled, so this test cannot prompt or alter the pytest process's UI policy.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="Security.framework")


def test_native_wrapping_key_survives_processes_and_session_rotations(tmp_path):
    result = subprocess.run(
        [sys.executable, __file__, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stderr


def _bind(library, name, arguments, result):
    function = getattr(library, name)
    function.argtypes = arguments
    function.restype = result
    return function


def _require(status, action):
    assert status == 0, f"{action} failed with OSStatus {status}"


class _PrivateKeychain:
    def __init__(self, darwin):
        self.darwin = darwin
        pointer = ctypes.c_void_p
        output = ctypes.POINTER(pointer)
        status = ctypes.c_int32
        self.create = _bind(
            darwin._sec,
            "SecKeychainCreate",
            [
                ctypes.c_char_p,
                ctypes.c_uint32,
                pointer,
                ctypes.c_ubyte,
                pointer,
                output,
            ],
            status,
        )
        self.open = _bind(
            darwin._sec, "SecKeychainOpen", [ctypes.c_char_p, output], status
        )
        self.delete = _bind(darwin._sec, "SecKeychainDelete", [pointer], status)
        self.search = _bind(darwin._sec, "SecKeychainCopySearchList", [output], status)
        self.default = _bind(darwin._sec, "SecKeychainCopyDefault", [output], status)
        self.array = _bind(
            darwin._found,
            "CFArrayCreate",
            [pointer, pointer, ctypes.c_long, pointer],
            pointer,
        )
        self.equal = _bind(darwin._found, "CFEqual", [pointer, pointer], ctypes.c_ubyte)
        interaction = _bind(
            darwin._sec,
            "SecKeychainSetUserInteractionAllowed",
            [ctypes.c_ubyte],
            status,
        )
        _require(interaction(False), "disable Keychain UI in this subprocess")

    def snapshot(self):
        search, default = ctypes.c_void_p(), ctypes.c_void_p()
        _require(self.search(ctypes.byref(search)), "read keychain search list")
        status = self.default(ctypes.byref(default))
        if status not in (0, -25307):  # errSecNoDefaultKeychain
            self.darwin.CFRelease(search)
            _require(status, "read default keychain")
        return search, default

    def release_snapshot(self, snapshot):
        for reference in snapshot:
            if reference:
                self.darwin.CFRelease(reference)

    def assert_unchanged(self, before):
        after = self.snapshot()
        try:
            assert self.equal(before[0], after[0]), "keychain search list changed"
            assert bool(before[1]) == bool(after[1]), "default keychain changed"
            if before[1]:
                assert self.equal(before[1], after[1]), "default keychain changed"
        finally:
            self.release_snapshot(after)

    def isolate_queries(self, keychain):
        pointer = ctypes.c_void_p
        keychain_list = self.array(
            None, (pointer * 1)(keychain), 1, self.darwin._found.kCFTypeArrayCallBacks
        )
        original_query = self.darwin._query

        def isolated_query(**values):
            if "kSecValueData" in values:
                values["kSecUseKeychain"] = keychain
            else:
                values["kSecMatchSearchList"] = pointer(keychain_list)
            return original_query(**values)

        return keychain_list, patch.object(self.darwin, "_query", isolated_query)


def _read_and_rotate(darwin, session_path, old_token, new_token):
    from pipefy_auth.encrypted_file_keyring import EncryptedFileKeyring

    store = darwin.DarwinKeychainWrappingKey()
    reader = EncryptedFileKeyring(session_path, store)
    assert reader.get_password("pipefy-native-test", "synthetic-user") == old_token
    key = store.load()
    assert key is not None and len(key) == 32
    ciphertext = session_path.read_bytes()
    with patch.object(
        darwin, "SecItemAdd", side_effect=AssertionError("refresh rewrote Keychain")
    ):
        reader.set_password("pipefy-native-test", "synthetic-user", new_token)
        fresh_store = darwin.DarwinKeychainWrappingKey()
        fresh_reader = EncryptedFileKeyring(session_path, fresh_store)
        assert (
            fresh_reader.get_password("pipefy-native-test", "synthetic-user")
            == new_token
        )
        assert fresh_store.load_or_create() == key
    assert session_path.read_bytes() != ciphertext
    assert new_token.encode() not in session_path.read_bytes()
    return hashlib.sha256(key).hexdigest()


def _exercise(directory, *, rotation=None):
    from pipefy_auth import wrapping_key_darwin as darwin
    from pipefy_auth.encrypted_file_keyring import EncryptedFileKeyring

    native = _PrivateKeychain(darwin)
    before = native.snapshot()
    keychain, keychain_list = ctypes.c_void_p(), None
    keychain_path = directory / "pipefy-test.keychain"
    session_path = directory / "session.enc"
    try:
        if rotation is None:
            password = os.urandom(24).hex().encode()
            _require(
                native.create(
                    os.fsencode(keychain_path),
                    len(password),
                    password,
                    False,
                    None,
                    ctypes.byref(keychain),
                ),
                "create private keychain",
            )
        else:
            _require(
                native.open(os.fsencode(keychain_path), ctypes.byref(keychain)),
                "open private keychain",
            )
        native.assert_unchanged(before)
        keychain_list, isolated_queries = native.isolate_queries(keychain)
        with isolated_queries:
            if rotation is not None:
                return _read_and_rotate(darwin, session_path, *rotation)
            store = darwin.DarwinKeychainWrappingKey()
            assert store.load() is None
            writer = EncryptedFileKeyring(session_path, store)
            with patch.object(darwin, "SecItemAdd", wraps=darwin.SecItemAdd) as add:
                writer.set_password("pipefy-native-test", "synthetic-user", "token-0")
                assert add.call_count == 1
            key = store.load()
            assert key is not None and len(key) == 32
            fingerprint = hashlib.sha256(key).hexdigest()
            for index in range(2):
                result = subprocess.run(
                    [
                        sys.executable,
                        __file__,
                        str(directory),
                        f"token-{index}",
                        f"token-{index + 1}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                assert result.returncode == 0, result.stderr
                assert json.loads(result.stdout) == fingerprint
            assert _read_and_rotate(darwin, session_path, "token-2", "token-3") == (
                fingerprint
            )
    finally:
        if keychain_list:
            darwin.CFRelease(keychain_list)
        if keychain:
            try:
                if rotation is None:
                    _require(native.delete(keychain), "delete private keychain")
            finally:
                darwin.CFRelease(keychain)
        try:
            native.assert_unchanged(before)
        finally:
            native.release_snapshot(before)


if __name__ == "__main__":
    rotation = tuple(sys.argv[2:]) or None
    print(json.dumps(_exercise(Path(sys.argv[1]), rotation=rotation)))
