"""Persist the refresh-token-bearing session through ``keyring``.

The active backend is the OS keychain, or a file store: the DPAPI-encrypted
``keyring-dpapi.cfg`` that ``auto`` selects on Windows, or the plaintext
``keyring.cfg`` that ``PIPEFY_KEYCHAIN_BACKEND=file`` selects.

Single active session per ``(issuer_host, client_id)`` tuple. The stored entry
holds a small JSON blob (refresh + access token + minimal metadata). The
short-lived access token is included so a single login is usable immediately;
the long-lived refresh token is the durable credential.

``keyring`` is imported lazily inside each function so that merely importing
this module (which happens at CLI startup via the ``auth`` subcommand) does not
pay the ~30-80ms backend-discovery cost on every ``pipefy`` invocation.
"""

from __future__ import annotations

import sys
import time
from typing import Annotated, Any, Literal
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    StrictInt,
    StrictStr,
    ValidationError,
    model_serializer,
    model_validator,
)

from pipefy_auth.responses import TokenResponse

_SERVICE = "pipefy"
_KEYRING_FILENAME = "keyring.cfg"
_DPAPI_KEYRING_FILENAME = "keyring-dpapi.cfg"
_TOKEN_FIELDS: frozenset[str] = frozenset(TokenResponse.model_fields.keys())


KeychainBackendPlan = Literal["os-keyring", "plaintext-file", "dpapi-file"]


def plan_keychain_backend(
    choice: Literal["auto", "file"], *, platform: str
) -> KeychainBackendPlan:
    """Map the ``keychain_backend`` setting and ``sys.platform`` to a backend.

    ``"auto"`` keeps the OS keyring, except on Windows: Credential Manager caps
    an entry at 2560 bytes and a Pipefy session is larger, so ``"auto"`` there
    selects a DPAPI-encrypted file instead. ``"file"`` selects the plaintext
    file on every platform.
    """
    if choice == "file":
        return "plaintext-file"
    if platform == "win32":
        return "dpapi-file"
    return "os-keyring"


def configure_keychain_backend(choice: Literal["auto", "file"]) -> None:
    """Apply the requested keyring backend before any session read or write.

    Idempotent: safe to call multiple times; a second call replaces the
    previous file backend with one pointing at the same path.

    Args:
        choice: ``"auto"`` preserves ``keyring``'s built-in backend discovery
            (macOS Keychain, Secret Service) except on Windows, where it swaps
            to :class:`keyrings.alt.Windows.EncryptedKeyring` writing under
            ``pipefy_infra.config.config_dir() / "keyring-dpapi.cfg"``; DPAPI
            encrypts each entry with the Windows user's credentials.
            ``"file"`` swaps to :class:`keyrings.alt.file.PlaintextKeyring`
            writing under ``config_dir() / "keyring.cfg"``; the file stores
            credentials in plaintext on disk and is intended for headless
            Linux or CI runners where the OS keychain is unavailable.
    """
    plan = plan_keychain_backend(choice, platform=sys.platform)
    if plan == "os-keyring":
        return
    import keyring
    from keyring.backend import KeyringBackend
    from pipefy_infra.config import config_dir

    backend: KeyringBackend
    if plan == "dpapi-file":
        from keyrings.alt.Windows import EncryptedKeyring

        backend = EncryptedKeyring()
        backend.file_path = str(config_dir() / _DPAPI_KEYRING_FILENAME)
    else:
        from keyrings.alt.file import PlaintextKeyring

        backend = PlaintextKeyring()
        backend.file_path = str(config_dir() / _KEYRING_FILENAME)
    keyring.set_keyring(backend)


class SessionDeleteError(RuntimeError):
    """Keychain backend rejected the delete (distinct from "entry absent")."""


class StoredSession(BaseModel):
    """Persisted session: identity + write timestamp + the token response.

    The token fields are bundled in :class:`TokenResponse` so there is one
    source of truth for the OAuth wire shape. On-disk JSON destructures the
    token attributes into the parent object (legacy flat shape) so existing
    keychain entries continue to load.

    ``extra="forbid"`` because both writer and reader live in this codebase:
    an unknown key on disk indicates corruption or hand-editing, not an IdP
    extension. Unknown keys nested under ``token`` are still ignored
    (see :class:`TokenResponse`).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    issuer: Annotated[StrictStr, Field(min_length=1)]
    client_id: Annotated[StrictStr, Field(min_length=1)]
    obtained_at: StrictInt
    token: TokenResponse

    @model_validator(mode="before")
    @classmethod
    def _accept_flat_blob(cls, data: Any) -> Any:
        """Rebuild a nested ``token`` from a legacy flat on-disk shape.

        Pre-pydantic blobs destructured the token attributes into the parent
        object. If we receive that shape (``"token"`` absent, token-shaped
        keys present), re-nest before field validation. Already-nested input
        passes through untouched.
        """
        if not isinstance(data, dict):
            return data
        if "token" in data:
            return data
        if "access_token" not in data:
            return data
        nested: dict[str, Any] = {}
        outer: dict[str, Any] = {}
        for key, value in data.items():
            if key in _TOKEN_FIELDS:
                nested[key] = value
            else:
                outer[key] = value
        outer["token"] = nested
        return outer

    @model_serializer(mode="wrap")
    def _to_flat_blob(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        """Always serialize to the flat on-disk shape (legacy readers stay green)."""
        nested = handler(self)
        token = nested.pop("token", {})
        return {**nested, **token}


def _issuer_host(issuer_url: str) -> str:
    host = urlparse(issuer_url).hostname
    if not host:
        raise ValueError(f"Cannot derive host from issuer URL: {issuer_url!r}")
    return host.lower()


def keychain_key(issuer_url: str, client_id: str) -> str:
    """Return the keychain account name for this issuer + client tuple."""
    return f"{_issuer_host(issuer_url)}|{client_id}"


def store_session(
    *,
    issuer: str,
    client_id: str,
    token: TokenResponse,
) -> StoredSession:
    """Persist a token response in the active keyring backend. Returns the stored shape.

    Raises:
        KeyringError: When the keychain backend rejects the write. Caller should
            surface a user-facing message (e.g. headless Linux without a Secret
            Service daemon, or Windows Credential Manager refusing a session
            larger than its 2560-byte entry limit).
    """
    import keyring
    from keyring.errors import PasswordSetError

    session = StoredSession(
        issuer=issuer,
        client_id=client_id,
        obtained_at=int(time.time()),
        token=token,
    )
    # keyring's Windows backend lets pywin32-ctypes' error escape. It subclasses
    # neither KeyringError nor OSError, so it is matched as a non-OSError with
    # ``winerror`` (every OSError has that attribute on Windows).
    try:
        keyring.set_password(
            _SERVICE, keychain_key(issuer, client_id), session.model_dump_json()
        )
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, OSError) or not hasattr(exc, "winerror"):
            raise
        raise PasswordSetError(
            f"Windows Credential Manager rejected the session: {exc}"
        ) from exc
    return session


SessionEntryPresence = Literal["present", "absent", "unknown"]


def session_entry_presence(*, issuer: str, client_id: str) -> SessionEntryPresence:
    """Report whether a keychain entry exists, without parsing its contents.

    An entry that exists but cannot be parsed is ``"present"``: a caller whose
    job is to clear the credential needs presence, not readability, and
    :func:`load_session` cannot supply it because it collapses "absent",
    "unreadable" and "backend failed" into ``None``.

    Returns:
        ``"present"`` when the backend returns a blob of any content,
        ``"absent"`` when it returns nothing, and ``"unknown"`` when the
        backend itself fails, including a file-backed store whose entry
        cannot be decrypted or decoded (:func:`delete_session` can still
        remove such an entry). ``"unknown"`` means presence was not
        established: no caller may then report the credential as removed, or
        as never having been there.
    """
    import keyring
    from keyring.errors import KeyringError

    key = keychain_key(issuer, client_id)
    # File-backed keyrings (keyrings.alt) raise OSError on a failed decrypt and
    # binascii.Error, a ValueError, on a damaged entry instead of KeyringError.
    try:
        blob = keyring.get_password(_SERVICE, key)
    except (KeyringError, OSError, ValueError):
        return "unknown"
    return "absent" if blob is None else "present"


def load_session(*, issuer: str, client_id: str) -> StoredSession | None:
    """Return the stored session for this issuer + client, or ``None``.

    ``None`` means "no usable session", which covers three distinct states:
    no entry, an entry that fails validation, and a backend that refused the
    read. Callers that must distinguish them — anything that deletes, or that
    reports the credential as gone — need
    :func:`session_entry_presence` instead.
    """
    import keyring
    from keyring.errors import KeyringError

    key = keychain_key(issuer, client_id)
    try:
        blob = keyring.get_password(_SERVICE, key)
    except (KeyringError, OSError, ValueError):
        return None
    if not blob:
        return None
    try:
        return StoredSession.model_validate_json(blob)
    except ValidationError:
        return None


def delete_session(*, issuer: str, client_id: str) -> bool:
    """Remove the stored session. Returns True if an entry was present.

    Raises:
        SessionDeleteError: When the keychain backend rejects the operation,
            including a file-backed store that cannot rewrite its file
            (distinct from "no entry to delete"). The local credential may
            still exist; callers should surface a user-facing error rather
            than claim a successful sign-out.
    """
    import keyring
    from keyring.errors import KeyringError, PasswordDeleteError

    try:
        keyring.delete_password(_SERVICE, keychain_key(issuer, client_id))
    except PasswordDeleteError:
        return False
    except (KeyringError, OSError) as exc:
        raise SessionDeleteError(str(exc)) from exc
    return True


def keychain_backend_name() -> str:
    """Short identifier for the active keyring backend (diagnostics)."""
    import keyring
    from keyring.errors import KeyringError

    try:
        backend = keyring.get_keyring()
    except KeyringError as exc:
        return f"unavailable ({exc})"
    return backend.__class__.__name__


__all__ = [
    "KeychainBackendPlan",
    "SessionDeleteError",
    "SessionEntryPresence",
    "StoredSession",
    "configure_keychain_backend",
    "delete_session",
    "keychain_backend_name",
    "keychain_key",
    "load_session",
    "plan_keychain_backend",
    "session_entry_presence",
    "store_session",
]
