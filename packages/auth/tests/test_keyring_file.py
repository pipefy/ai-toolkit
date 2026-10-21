"""Strict reads and atomic writes for the file-backed keyrings."""

from __future__ import annotations

import os
import re
import sys
import threading
import time
import types
from collections.abc import Callable, Iterator
from pathlib import Path

import keyring
import keyrings.alt.Windows
import pytest
from keyring.errors import KeyringError, PasswordDeleteError

from pipefy_auth import keyring_file, storage
from pipefy_auth.keyring_file import EncryptedKeyring, PlaintextKeyring
from pipefy_auth.responses import TokenResponse
from pipefy_auth.storage import (
    SessionDeleteError,
    configure_keychain_backend,
    delete_session,
    load_session,
    session_entry_presence,
    store_session,
)

_SERVICE = "pipefy"
_ISSUER = "https://example.test/realms/pipefy"
_CLIENT_ID = "pipefy-cli"
_ACCOUNT = "example.test|pipefy-cli"
_STALE_AGE_S = 3600
_TEMP_NAME = ".keyring.cfg.pipefy-deadbeef.tmp"


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "pipefy" / "keyring.cfg"


def _reverse_bytes(data: bytes, non_interactive: int = 0) -> bytes:
    return bytes(reversed(data))


@pytest.fixture(params=[PlaintextKeyring, EncryptedKeyring], ids=lambda c: c.__name__)
def backend(
    request: pytest.FixtureRequest, store_path: Path, monkeypatch: pytest.MonkeyPatch
) -> PlaintextKeyring:
    if request.param is EncryptedKeyring and sys.platform != "win32":
        # CRYPT32 loads only on Windows; a reversible cipher elsewhere keeps the
        # DPAPI class on the same file I/O as on Windows.
        cipher = types.SimpleNamespace(encrypt=_reverse_bytes, decrypt=_reverse_bytes)
        monkeypatch.setattr(keyrings.alt.Windows, "_win_crypto", cipher, raising=False)
    instance = request.param()
    instance.file_path = str(store_path)
    return instance


@pytest.fixture
def installed(backend: PlaintextKeyring) -> Iterator[PlaintextKeyring]:
    original = keyring.get_keyring()
    keyring.set_keyring(backend)
    yield backend
    keyring.set_keyring(original)


def _token(access: str = "A" * 1514) -> TokenResponse:
    return TokenResponse(access_token=access, refresh_token="R" * 677)


def _leave_file(directory: Path, name: str, *, age_s: float = 0) -> Path:
    path = directory / name
    path.write_text("[pipefy]\nleftover = marker\n", encoding="utf-8")
    if age_s:
        stamp = time.time() - age_s
        os.utime(path, (stamp, stamp))
    return path


@pytest.mark.unit
def test_round_trip_and_new_store_is_private(
    backend: PlaintextKeyring, store_path: Path
) -> None:
    backend.set_password(_SERVICE, _ACCOUNT, "secret")

    assert backend.get_password(_SERVICE, _ACCOUNT) == "secret"
    if sys.platform != "win32":
        assert store_path.stat().st_mode & 0o777 == 0o600


@pytest.mark.unit
def test_reader_during_a_write_sees_the_previous_session(
    installed: PlaintextKeyring,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The store is replaced in one step, so a read racing a write never sees
    a truncated file."""
    previous = store_session(issuer=_ISSUER, client_id=_CLIENT_ID, token=_token())
    seen_mid_write: list[object] = []
    real_replace = os.replace

    def _read_then_replace(source: str, destination: str) -> None:
        seen_mid_write.append(load_session(issuer=_ISSUER, client_id=_CLIENT_ID))
        real_replace(source, destination)

    monkeypatch.setattr(keyring_file.os, "replace", _read_then_replace)
    store_session(issuer=_ISSUER, client_id=_CLIENT_ID, token=_token("B" * 1514))

    assert seen_mid_write == [previous]
    loaded = load_session(issuer=_ISSUER, client_id=_CLIENT_ID)
    assert loaded is not None
    assert loaded.token.access_token == "B" * 1514


@pytest.mark.unit
def test_failed_write_keeps_the_previous_session_and_no_temp_file(
    installed: PlaintextKeyring,
    store_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous = store_session(issuer=_ISSUER, client_id=_CLIENT_ID, token=_token())

    def _disk_full(source: str, destination: str) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(keyring_file.os, "replace", _disk_full)
    with pytest.raises(OSError, match="No space left"):
        store_session(issuer=_ISSUER, client_id=_CLIENT_ID, token=_token("B" * 1514))

    assert load_session(issuer=_ISSUER, client_id=_CLIENT_ID) == previous
    assert sorted(p.name for p in store_path.parent.iterdir()) == ["keyring.cfg"]


@pytest.mark.unit
def test_replace_retries_while_another_process_holds_the_store(
    installed: PlaintextKeyring,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows refuses os.replace onto a file another process has open."""
    store_session(issuer=_ISSUER, client_id=_CLIENT_ID, token=_token())
    real_replace = os.replace
    refusals = [PermissionError(13, "in use"), PermissionError(13, "in use")]

    def _busy_then_free(source: str, destination: str) -> None:
        if refusals:
            raise refusals.pop()
        real_replace(source, destination)

    monkeypatch.setattr(keyring_file.os, "replace", _busy_then_free)
    monkeypatch.setattr(keyring_file.time, "sleep", lambda _s: None)
    store_session(issuer=_ISSUER, client_id=_CLIENT_ID, token=_token("B" * 1514))

    loaded = load_session(issuer=_ISSUER, client_id=_CLIENT_ID)
    assert loaded is not None
    assert loaded.token.access_token == "B" * 1514


@pytest.mark.unit
def test_replace_gives_up_after_the_retry_budget(
    installed: PlaintextKeyring,
    store_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous = store_session(issuer=_ISSUER, client_id=_CLIENT_ID, token=_token())
    attempts: list[str] = []

    def _always_busy(source: str, destination: str) -> None:
        attempts.append(destination)
        if len(attempts) > 50:
            raise AssertionError("os.replace retried without a bound")
        raise PermissionError(13, "in use")

    monkeypatch.setattr(keyring_file.os, "replace", _always_busy)
    monkeypatch.setattr(keyring_file.time, "sleep", lambda _s: None)
    with pytest.raises(PermissionError, match="in use"):
        store_session(issuer=_ISSUER, client_id=_CLIENT_ID, token=_token("B" * 1514))

    assert len(attempts) > 1
    assert load_session(issuer=_ISSUER, client_id=_CLIENT_ID) == previous
    assert sorted(p.name for p in store_path.parent.iterdir()) == ["keyring.cfg"]


@pytest.mark.unit
def test_remove_retries_while_another_process_holds_the_store(
    installed: PlaintextKeyring,
    store_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows refuses to delete a file another process has open."""
    store_session(issuer=_ISSUER, client_id=_CLIENT_ID, token=_token())
    real_remove = os.remove
    refusals = [PermissionError(13, "in use"), PermissionError(13, "in use")]

    def _busy_then_free(path: str) -> None:
        if refusals:
            raise refusals.pop()
        real_remove(path)

    monkeypatch.setattr(keyring_file.os, "remove", _busy_then_free)
    monkeypatch.setattr(keyring_file.time, "sleep", lambda _s: None)

    assert delete_session(issuer=_ISSUER, client_id=_CLIENT_ID) is True
    assert not store_path.exists()


@pytest.mark.unit
@pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0,
    reason="needs POSIX permissions enforced for this user",
)
def test_unreadable_store_is_unknown_not_absent(
    installed: PlaintextKeyring, store_path: Path
) -> None:
    store_session(issuer=_ISSUER, client_id=_CLIENT_ID, token=_token())
    store_path.chmod(0)
    try:
        assert session_entry_presence(issuer=_ISSUER, client_id=_CLIENT_ID) == (
            "unknown"
        )
        assert load_session(issuer=_ISSUER, client_id=_CLIENT_ID) is None
    finally:
        store_path.chmod(0o600)


@pytest.mark.unit
@pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0,
    reason="needs POSIX permissions enforced for this user",
)
def test_unreadable_directory_is_unknown_not_absent(
    installed: PlaintextKeyring, store_path: Path
) -> None:
    """A directory the user cannot search hides the store from os.path.exists."""
    store_session(issuer=_ISSUER, client_id=_CLIENT_ID, token=_token())
    store_path.parent.chmod(0o600)
    try:
        assert session_entry_presence(issuer=_ISSUER, client_id=_CLIENT_ID) == (
            "unknown"
        )
        assert load_session(issuer=_ISSUER, client_id=_CLIENT_ID) is None
    finally:
        store_path.parent.chmod(0o700)


@pytest.mark.unit
def test_store_that_is_not_ini_raises_keyring_error(
    backend: PlaintextKeyring, store_path: Path
) -> None:
    store_path.parent.mkdir(parents=True)
    store_path.write_text("not an ini file\n", encoding="utf-8")

    with pytest.raises(KeyringError, match="not a valid INI store"):
        backend.get_password(_SERVICE, _ACCOUNT)


@pytest.mark.unit
def test_store_that_is_not_utf8_raises_keyring_error(
    installed: PlaintextKeyring, store_path: Path
) -> None:
    store_path.parent.mkdir(parents=True)
    store_path.write_bytes("[pipefy]\nx = 1\n".encode("utf-16"))

    with pytest.raises(KeyringError, match="UnicodeDecodeError"):
        installed.get_password(_SERVICE, _ACCOUNT)
    with pytest.raises(SessionDeleteError):
        delete_session(issuer=_ISSUER, client_id=_CLIENT_ID)


@pytest.mark.unit
def test_parse_error_message_does_not_quote_the_store(
    backend: PlaintextKeyring, store_path: Path
) -> None:
    store_path.parent.mkdir(parents=True)
    store_path.write_text(
        "[pipefy]\nkey = value\nSYNTHETICSECRETLINE\n", encoding="utf-8"
    )

    with pytest.raises(KeyringError) as raised:
        backend.get_password(_SERVICE, _ACCOUNT)

    message = str(raised.value)
    assert repr(str(store_path)) in message
    assert "ParsingError" in message
    assert "SYNTHETICSECRETLINE" not in message


@pytest.mark.unit
def test_deleting_the_last_entry_removes_the_file(
    backend: PlaintextKeyring, store_path: Path
) -> None:
    backend.set_password(_SERVICE, _ACCOUNT, "secret")
    backend.set_password(_SERVICE, "other|client", "other")

    backend.delete_password(_SERVICE, _ACCOUNT)
    assert store_path.exists()
    assert backend.get_password(_SERVICE, "other|client") == "other"

    backend.delete_password(_SERVICE, "other|client")
    assert not store_path.exists()


@pytest.mark.unit
def test_deleting_a_missing_entry_raises_password_delete_error(
    backend: PlaintextKeyring,
) -> None:
    with pytest.raises(PasswordDeleteError):
        backend.delete_password(_SERVICE, _ACCOUNT)


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need privileges")
def test_write_and_delete_go_through_a_symlinked_store(
    backend: PlaintextKeyring, store_path: Path, tmp_path: Path
) -> None:
    target = tmp_path / "dotfiles" / "keyring.cfg"
    target.parent.mkdir()
    store_path.parent.mkdir()
    store_path.symlink_to(target)
    reader_of_target = type(backend)()
    reader_of_target.file_path = str(target)

    backend.set_password(_SERVICE, _ACCOUNT, "first")
    backend.set_password(_SERVICE, _ACCOUNT, "second")

    assert store_path.is_symlink()
    assert reader_of_target.get_password(_SERVICE, _ACCOUNT) == "second"
    assert sorted(p.name for p in store_path.parent.iterdir()) == ["keyring.cfg"]

    backend.delete_password(_SERVICE, _ACCOUNT)

    assert store_path.is_symlink()
    assert not target.exists()


@pytest.mark.unit
def test_write_names_its_temp_file_after_the_store(
    backend: PlaintextKeyring, store_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """uninstall.sh matches leftovers by this name, so it is a contract."""
    temp_names: list[str] = []
    real_replace = os.replace

    def _record_source(source: str, destination: str) -> None:
        temp_names.append(os.path.basename(source))
        real_replace(source, destination)

    monkeypatch.setattr(keyring_file.os, "replace", _record_source)
    backend.set_password(_SERVICE, _ACCOUNT, "secret")

    assert len(temp_names) == 1
    assert re.fullmatch(r"\.keyring\.cfg\.pipefy-[a-z0-9_]{8}\.tmp", temp_names[0])


@pytest.mark.unit
def test_stale_temp_files_are_removed_by_the_next_write_and_by_delete(
    backend: PlaintextKeyring, store_path: Path
) -> None:
    """A write killed before its rename leaves a temp file holding a session."""
    store_path.parent.mkdir(parents=True)
    _leave_file(store_path.parent, _TEMP_NAME, age_s=_STALE_AGE_S)

    backend.set_password(_SERVICE, _ACCOUNT, "secret")
    assert sorted(p.name for p in store_path.parent.iterdir()) == ["keyring.cfg"]

    _leave_file(store_path.parent, _TEMP_NAME, age_s=_STALE_AGE_S)
    backend.delete_password(_SERVICE, _ACCOUNT)
    assert list(store_path.parent.iterdir()) == []


@pytest.mark.unit
def test_logout_without_a_store_still_removes_a_stale_temp_file(
    installed: PlaintextKeyring, store_path: Path
) -> None:
    """A first login killed before its rename leaves no store, only the temp."""
    store_path.parent.mkdir(parents=True)
    _leave_file(store_path.parent, _TEMP_NAME, age_s=_STALE_AGE_S)

    assert delete_session(issuer=_ISSUER, client_id=_CLIENT_ID) is False
    assert list(store_path.parent.iterdir()) == []


@pytest.mark.unit
def test_a_recent_temp_file_is_kept_for_the_write_that_may_own_it(
    backend: PlaintextKeyring, store_path: Path
) -> None:
    """Another process may be between writing its temp file and renaming it."""
    store_path.parent.mkdir(parents=True)
    in_flight = _leave_file(store_path.parent, _TEMP_NAME)

    backend.set_password(_SERVICE, _ACCOUNT, "secret")
    backend.delete_password(_SERVICE, _ACCOUNT)

    assert in_flight.exists()


@pytest.mark.unit
@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need privileges")
def test_sweep_keeps_files_in_a_symlink_target_directory_it_did_not_write(
    backend: PlaintextKeyring, store_path: Path, tmp_path: Path
) -> None:
    """The target directory belongs to the user, who may keep other files there."""
    dotfiles = tmp_path / "dotfiles"
    dotfiles.mkdir()
    store_path.parent.mkdir()
    store_path.symlink_to(dotfiles / "credentials")
    not_ours = [
        ".credentials.backup.tmp",
        ".credentials.other.abcdefgh.tmp",
        ".credentials.other.pipefy-abcdefgh.tmp",
        ".credentials.pipefy-abcdefgh.tmp.bak",
        ".credentials.pipefy-abcdefghi.tmp",
        ".credentials.pipefy-ABCDEFGH.tmp",
    ]
    for name in not_ours:
        _leave_file(dotfiles, name, age_s=_STALE_AGE_S)
    _leave_file(dotfiles, ".credentials.pipefy-k3x9_2ab.tmp", age_s=_STALE_AGE_S)

    backend.set_password(_SERVICE, _ACCOUNT, "secret")
    backend.delete_password(_SERVICE, _ACCOUNT)

    assert sorted(p.name for p in dotfiles.iterdir()) == sorted(not_ours)


@pytest.mark.unit
def test_sweep_matches_a_store_name_with_pattern_characters_literally(
    backend: PlaintextKeyring, tmp_path: Path
) -> None:
    directory = tmp_path / "store"
    directory.mkdir()
    backend.file_path = str(directory / "key[ring]+(1).cfg")
    other_stores_temps = [
        ".keyr+(1).cfg.pipefy-abcdefgh.tmp",
        ".keyring1.cfg.pipefy-abcdefgh.tmp",
    ]
    for name in other_stores_temps:
        _leave_file(directory, name, age_s=_STALE_AGE_S)
    _leave_file(directory, ".key[ring]+(1).cfg.pipefy-abcdefgh.tmp", age_s=_STALE_AGE_S)

    backend.set_password(_SERVICE, _ACCOUNT, "secret")

    assert sorted(p.name for p in directory.iterdir()) == sorted(
        [*other_stores_temps, "key[ring]+(1).cfg"]
    )


@pytest.mark.unit
def test_file_choice_installs_the_atomic_plaintext_keyring(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    original = keyring.get_keyring()
    try:
        configure_keychain_backend("file")
        assert isinstance(keyring.get_keyring(), PlaintextKeyring)
    finally:
        keyring.set_keyring(original)


@pytest.mark.unit
def test_auto_choice_on_windows_installs_the_atomic_dpapi_keyring(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(storage, "sys", types.SimpleNamespace(platform="win32"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    original = keyring.get_keyring()
    try:
        configure_keychain_backend("auto")
        selected = keyring.get_keyring()
        assert isinstance(selected, EncryptedKeyring)
        assert selected.file_path == str(tmp_path / "pipefy" / "keyring-dpapi.cfg")
    finally:
        keyring.set_keyring(original)


_SHARING_WAIT_S = 10


def _run_while_a_reader_holds_the_store(
    store_path: Path, operation: Callable[[], None]
) -> None:
    """Run ``operation`` with the store open; close the reader only after the
    OS refused the replace or delete once.

    Without a retry the refused call is the last one, so the operation fails.
    """
    refused = threading.Event()
    errors: list[BaseException] = []

    def _signal_refusal(real: Callable[..., None]) -> Callable[..., None]:
        def _call(*paths: str) -> None:
            try:
                real(*paths)
            except PermissionError:
                refused.set()
                raise

        return _call

    def _record_errors() -> None:
        try:
            operation()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(keyring_file.os, "replace", _signal_refusal(os.replace))
        patch.setattr(keyring_file.os, "remove", _signal_refusal(os.remove))
        reader = store_path.open(encoding="utf-8")
        worker = threading.Thread(target=_record_errors)
        try:
            worker.start()
            assert refused.wait(timeout=_SHARING_WAIT_S), (
                "the operation never hit a sharing violation",
                errors,
            )
        finally:
            reader.close()
            worker.join(timeout=_SHARING_WAIT_S)
    assert not worker.is_alive()
    assert errors == []


@pytest.mark.unit
@pytest.mark.skipif(sys.platform != "win32", reason="Windows file-sharing semantics")
def test_write_and_delete_wait_for_a_reader_holding_the_store_open(
    backend: PlaintextKeyring, store_path: Path
) -> None:
    """On Windows, os.replace and os.remove fail while another handle has the
    store open."""
    backend.set_password(_SERVICE, _ACCOUNT, "old")

    _run_while_a_reader_holds_the_store(
        store_path, lambda: backend.set_password(_SERVICE, _ACCOUNT, "new")
    )
    assert backend.get_password(_SERVICE, _ACCOUNT) == "new"

    _run_while_a_reader_holds_the_store(
        store_path, lambda: backend.delete_password(_SERVICE, _ACCOUNT)
    )
    assert not store_path.exists()
