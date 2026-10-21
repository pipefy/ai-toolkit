"""File-backed keyrings that read strictly and replace the store atomically.

keyrings.alt's file backends read with ``ConfigParser.read()``, which skips a
file it cannot open, so an unreadable store looks empty. They also rewrite the
store in place with ``open(path, "w")``, so a reader can see an empty file
during a write and an interrupted write loses every entry. These subclasses
keep keyrings.alt's file format and encryption and change only the file I/O:

- a read raises when the store exists but cannot be opened, decoded, or
  parsed; only a missing file reads as empty;
- a write goes to a temporary file next to the store and replaces the store
  with ``os.replace``, so readers see the old or the new store, never a
  partial one. A symlinked store is resolved first, so the write updates the
  file the link points at and the link stays;
- deleting the last entry removes the file (the link target, for a symlink);
- a write or a delete first removes temporary files that an interrupted write
  left next to the store. Only names this module generates
  (``.<store name>.pipefy-<8 random characters>.tmp``) older than a minute are
  removed, so other files in a symlink target's directory stay. A write still
  in progress keeps its temporary file unless it stalls for more than a
  minute before the rename; it then fails with a filesystem error.

The class names match the keyrings.alt classes they extend because
``pipefy auth status`` and the store-failure hints report the class name.
"""

from __future__ import annotations

import configparser
import os
import re
import tempfile
import time
from base64 import decodebytes
from collections.abc import Callable

from keyring.errors import KeyringError, PasswordDeleteError
from keyrings.alt import Windows as _alt_windows
from keyrings.alt import file as _alt_file
from keyrings.alt.escape import escape as escape_for_ini

_SHARING_RETRY_ATTEMPTS = 5
_SHARING_RETRY_DELAY_S = 0.05
_STORE_FILE_MODE = 0o600
_TEMP_PREFIX_TAG = "pipefy-"
_TEMP_SUFFIX = ".tmp"
# tempfile's random part: 8 characters from this set (CPython _RandomNameSequence).
_TEMP_RANDOM_PART = "[a-z0-9_]{8}"
_STALE_TEMP_AGE_S = 60


class _AtomicFileStore:
    """File I/O shared by both keyrings; mixed in ahead of a keyrings.alt class."""

    file_path: str

    def _store_target(self) -> str:
        return os.path.realpath(self.file_path)

    def _load_store(self) -> configparser.RawConfigParser:
        store = configparser.RawConfigParser()
        try:
            handle = open(self.file_path, encoding="utf-8")
        except FileNotFoundError:
            return store
        with handle:
            try:
                store.read_file(handle)
            except (configparser.Error, UnicodeDecodeError) as exc:
                # The parser's message quotes the offending line, which can be
                # part of a credential.
                raise KeyringError(
                    f"Keyring file {self.file_path!r} is not a valid INI store "
                    f"({type(exc).__name__})"
                ) from exc
        return store

    def _save_store(self, store: configparser.RawConfigParser) -> None:
        target = self._store_target()
        directory = os.path.dirname(target)
        os.makedirs(directory, exist_ok=True)
        _remove_stale_temp_files(target)
        handle = tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=directory,
            prefix=_temp_file_prefix(target),
            suffix=_TEMP_SUFFIX,
            delete=False,
        )
        try:
            with handle:
                os.chmod(handle.name, _STORE_FILE_MODE)
                store.write(handle)
                handle.flush()
                os.fsync(handle.fileno())
            _retry_on_sharing_violation(os.replace, handle.name, target)
        except BaseException:
            _remove_if_present(handle.name)
            raise

    def get_password(self, service: str, username: str) -> str | None:
        assoc = self._generate_assoc(service, username)
        store = self._load_store()
        try:
            encoded = store.get(escape_for_ini(service), escape_for_ini(username))
        except (configparser.NoOptionError, configparser.NoSectionError):
            return None
        return self._decode(encoded, assoc)

    def _decode(self, encoded: str, assoc: bytes) -> str:
        encrypted = decodebytes(encoded.encode())
        try:
            return self.decrypt(encrypted, assoc).decode("utf-8")
        except ValueError:
            return self.decrypt(encrypted).decode("utf-8")

    def _write_config_value(self, service: str, key: str, value: str) -> None:
        store = self._load_store()
        section = escape_for_ini(service)
        if not store.has_section(section):
            store.add_section(section)
        store.set(section, escape_for_ini(key), value)
        self._save_store(store)

    def delete_password(self, service: str, username: str) -> None:
        _remove_stale_temp_files(self._store_target())
        store = self._load_store()
        section = escape_for_ini(service)
        try:
            removed = store.remove_option(section, escape_for_ini(username))
        except configparser.NoSectionError:
            removed = False
        if not removed:
            raise PasswordDeleteError("Password not found")
        if not store.options(section):
            store.remove_section(section)
        if store.sections():
            self._save_store(store)
        else:
            _retry_on_sharing_violation(os.remove, self._store_target())


def _temp_file_prefix(target: str) -> str:
    return f".{os.path.basename(target)}.{_TEMP_PREFIX_TAG}"


def _remove_stale_temp_files(target: str) -> None:
    directory = os.path.dirname(target)
    temp_name = re.compile(
        re.escape(_temp_file_prefix(target))
        + _TEMP_RANDOM_PART
        + re.escape(_TEMP_SUFFIX)
    )
    stale_before = time.time() - _STALE_TEMP_AGE_S
    try:
        names = os.listdir(directory)
    except OSError:
        return
    for name in names:
        if not temp_name.fullmatch(name):
            continue
        leftover = os.path.join(directory, name)
        try:
            if os.lstat(leftover).st_mtime < stale_before:
                os.remove(leftover)
        except OSError:
            pass


def _retry_on_sharing_violation(operation: Callable[..., None], *paths: str) -> None:
    # Windows refuses replace and delete while another process has the file
    # open; readers hold it only for a parse.
    for attempt in range(_SHARING_RETRY_ATTEMPTS):
        try:
            operation(*paths)
            return
        except PermissionError:
            if attempt == _SHARING_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(_SHARING_RETRY_DELAY_S)


def _remove_if_present(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


class PlaintextKeyring(_AtomicFileStore, _alt_file.PlaintextKeyring):
    """Plaintext file store (``PIPEFY_KEYCHAIN_BACKEND=file``)."""


class EncryptedKeyring(_AtomicFileStore, _alt_windows.EncryptedKeyring):
    """DPAPI-encrypted file store (Windows default)."""


__all__ = ["EncryptedKeyring", "PlaintextKeyring"]
