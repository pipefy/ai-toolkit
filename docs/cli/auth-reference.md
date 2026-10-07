# CLI authentication reference

This page describes how the `pipefy` CLI picks a credential, the `pipefy auth` commands, and how a stored session behaves. [`auth.md`](auth.md) shows how to set up each source and how to fix a failed sign-in.

## Credential precedence

Most-explicit wins. The CLI walks this list top-down and stops at the first source it can resolve:

| # | Source | Identity | Notes |
|---|--------|----------|-------|
| 1 | `--token <bearer>` | Whoever owns the token | Skips OAuth entirely |
| 2 | `PIPEFY_TOKEN` env var | Whoever owns the token | Same path as `--token` |
| 3 | `PIPEFY_SERVICE_ACCOUNT_*` triple | Service account | OAuth2 client-credentials grant |
| 4 | Stored user session | You (the signed-in user) | Eager refresh inside a 60 s leeway window |

Every tier wires the `InternalApiClient` against `<PIPEFY_BASE_URL>/internal_api` (derived from `PIPEFY_BASE_URL`), so features that go through the internal API (AI agent automations, some relation flows) work from any path — not just the service-account one.

If `pipefy auth login` succeeds but a higher-precedence source is set in your shell env, the CLI prints a one-line note so you know your stored session is being shadowed.

## Environment variables

Each variable below feeds one credential tier. [`docs/config.md`](../config.md) gives its default and full effect.

| Key | Tier |
|-----|------|
| `PIPEFY_TOKEN` | 2 |
| `PIPEFY_SERVICE_ACCOUNT_CLIENT_ID`, `PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET` | 3 |
| `PIPEFY_AUTH_URL`, `PIPEFY_AUTH_CLIENT_ID`, `PIPEFY_DISABLE_STORED_SESSION`, `PIPEFY_KEYCHAIN_BACKEND` | 4 |

`PIPEFY_BASE_URL` applies to every tier. The service-account token URL (tier 3) and the OIDC issuer URL (tier 4) are **not** interchangeable: the first is `<base>/oauth/token` for client credentials, and the second is the discovery root for the user login flow.

`--token`, `--base-url`, and `--allow-insecure-urls` override their variables for one process. `pipefy --help` lists them.

## Commands

| Command | Status | Notes |
|---------|--------|-------|
| `pipefy auth login` | Available | Browser-based PKCE login; persists the session in the OS keychain. |
| `pipefy auth status` | Available | Print which auth source is active, identity, and session expiry. |
| `pipefy auth logout` | Available | Revoke the refresh token at the IdP and clear the stored session. |

### `pipefy auth login` flags

| Flag | Default | Effect |
|------|---------|--------|
| `--no-browser` | _off_ | Print the authorization URL to stdout instead of trying to launch a browser. |
| `--callback-timeout <s>` | `180.0` | Seconds to wait for the browser callback (minimum 5). |

### `pipefy auth status` flags

| Flag | Default | Effect |
|------|---------|--------|
| `--json` / `-j` | _off_ | Emit a stable JSON schema instead of human-readable text. |

The command answers four diagnostic questions: am I signed in, as whom, via which precedence tier, and (for stored sessions) when does the access/refresh token expire. It also reports which _other_ credential sources are configured, so a CI failure where `PIPEFY_SERVICE_ACCOUNT_*` masks a stored login is one command away from being obvious.

#### JSON schema

```jsonc
{
  "signed_in": true,
  "identity": {"email": "user@pipefy.com", "name": "Pipefy User"},
  "auth_source": "stored-session",                // or "flag-token" | "env-token" | "service-account" | "none"
  "detected_sources": ["stored-session"],         // every configured source (winner + masked)
  "issuer": "https://signin.pipefy.com/realms/pipefy",
  "state": "active",                              // or "refresh-expired" | "needs-login" | "n/a"
  "access_expires_at": "2026-05-20T22:14:03Z",    // ISO 8601, null for static-bearer
  "refresh_expires_at": "2026-06-19T18:02:00Z",   // ISO 8601; null when not a stored session, or when the IdP advertises no refresh-token expiry (refresh_expires_in: 0)
  "token_rejected": false,                        // true only when the identity `me` query returned 401
  "keychain_backend": "Keyring",                  // null for non-stored-session sources
  "masking_env_vars": []                          // env vars masking a stored session, if any
}
```

The shape is stable across all sources (fields you don't have are `null` rather than absent), so a script can `jq .auth_source` without branching on which tier is active.

#### Exit codes

| Case | Exit |
|------|------|
| `auth_source == "none"` | **2** — same code as a domain command that fails on missing credentials. |
| Stored session present but refresh grant rejected (`state` ∈ {`refresh-expired`, `needs-login`}) | **2** |
| Signed in, but the identity `me` query returned 401 or transport-failed | **1** |
| Signed in, identity fetched successfully | **0** |

### `pipefy auth logout`

POSTs the stored refresh token to the IdP's `end_session_endpoint` (advertised in the OIDC discovery document) and removes the keychain entry. Without server-side revocation the refresh token would remain valid at the IdP until natural expiry — anyone who recovered it from a backup could still mint new access tokens.

Whether there is anything to clear is decided by the **presence** of a keychain entry, not by whether that entry parses: a stale, corrupt, or schema-drifted entry is still a credential on disk and is removed. The command always clears the local entry once it runs, even when the IdP round-trip fails. The non-happy paths surface a stderr warning so the user knows whether server-side revocation succeeded:

- **Revocation network / non-2xx failure** — stderr `Could not revoke refresh token at the IdP: <reason>. Clearing local session anyway; the refresh token may remain valid at the server until natural expiry.`
- **IdP doesn't advertise `end_session_endpoint`** — stderr `Pipefy auth server does not advertise a logout endpoint; the refresh token could not be revoked server-side. Clearing local session only.` (OIDC Discovery 1.0 makes the field optional; Keycloak ships it.)
- **Entry present but unreadable** — revocation needs a readable refresh token, so the entry is delete-only: stdout `Removed an unreadable Pipefy session entry (<issuer>).` and stderr `The stored session entry could not be read, so its refresh token could not be revoked at the IdP; that token remains valid at the server until natural expiry.` Nothing was revoked server-side, so the unrevoked refresh token stays usable at the IdP until it expires on its own.
- **Keychain read failed and nothing was deleted** — presence could not be established, so the command claims neither removal nor a clean machine: stderr `Could not read the keychain to check for a stored session (<issuer>), and no entry was removed. A credential may still be present; check for it manually via your OS keychain (service: 'pipefy').` and exit 1.

When no entry is stored, `pipefy auth logout` prints `Not signed in. Nothing to do.` and exits 0 — idempotent, matching `gh auth logout` and similar CLIs.

#### Exit codes

| Case | Exit |
|------|------|
| `PIPEFY_AUTH_URL=""` (or any other `PIPEFY_*` env var set to empty) | **2** — pydantic rejects empty values at settings load. Unset the var to fall back to the prod default. |
| No entry stored (no-op) | **0** |
| Session cleared (revoke succeeded, failed, or unsupported) | **0** |
| Unreadable entry cleared (no server-side revoke) | **0** |
| Keychain rejected the delete | **1** — the credential may survive; the message names the manual removal step. |
| Keychain read failed and no entry was deleted | **1** — presence unknown, so neither removal nor "nothing to do" can be claimed. |

## Session behavior

[`architecture.md`](../contributing/architecture.md#runtime-view) walks both flows step by step: the browser login, and the credential that every later invocation resolves. This section holds the details that the troubleshooting entries in [`auth.md`](auth.md#fix-a-failed-sign-in) depend on.

### Login (`pipefy auth login`)

The CLI binds the loopback socket on `127.0.0.1:<ephemeral>` **before** it opens the browser, so no other process can take the port mid-flight. It sends a one-time `state` value with the authorization request and refuses a callback that returns a different one, which is what raises [`State mismatch on OAuth callback`](auth.md#state-mismatch-on-oauth-callback-possible-csrf).

The stored shape is keyed by `(issuer_host, client_id)`: one active session per (IdP, client) pair, per machine. Re-running `pipefy auth login` against the same issuer replaces the previous entry.

### Eager refresh

Each `pipefy <cmd>` invocation refreshes the access token before it builds the client, when that token has less than **60 s** of life left. A failure surfaces as `Stored Pipefy session could not be refreshed: ...`, with no fallback to another tier. The precedence chain is evaluated before the refresh, so a user who chose tier 4 gets a hard "re-login" signal rather than a silent service-account swap.

A token revoked mid-session is handled separately, and the eager refresh above never sees it. When an API call answers 401, the CLI forces one refresh and retries the call. When that refresh returns nothing, or returns the same token, the 401 propagates, so you get a "session expired" error rather than a loop.

## Keychain backends

`keyring` selects an OS backend automatically: macOS Keychain on Darwin, Credential Manager on Windows, Secret Service (gnome-keyring / kwallet) on Linux. `pipefy auth login` prints the resolved backend name on success so you can confirm where the entry landed; `pipefy auth status` reports it as `Keychain: <BackendName>`.

### Opting out of the OS keychain

Two env vars (mirrored as TOML keys) override the default behaviour:

- `PIPEFY_DISABLE_STORED_SESSION=1` skips the keychain entirely. `pipefy auth login` refuses with exit 2, tier resolution never probes the backend, and `pipefy auth status` omits the `stored-session` tier. Use when only `PIPEFY_TOKEN` / `PIPEFY_SERVICE_ACCOUNT_*` matter (CI runners, automation) and the cold-start keyring backend-discovery cost (~30-80 ms on Darwin, more on a Linux box with no Secret Service daemon) is undesirable.

- `PIPEFY_KEYCHAIN_BACKEND=file` swaps the active backend to a plaintext on-disk keyring under `config_dir() / "keyring.cfg"` (`~/.config/pipefy/keyring.cfg` on POSIX, `%APPDATA%/pipefy/keyring.cfg` on Windows). Unblocks headless Linux without Secret Service. **The file is plaintext, not OS-secured**: anyone with read access to the file (including a co-tenant on a shared CI runner) reads the refresh token. Opt-in only.

These are independent: `PIPEFY_DISABLE_STORED_SESSION=1` takes precedence (the file backend is never read or written). `pipefy auth status` will reflect the active backend name regardless (`Keyring`, `PlaintextKeyring`, etc.).

Removing `PIPEFY_KEYCHAIN_BACKEND=file` **moves** the store rather than clearing it: the next login writes to the OS keychain while whatever is already in `keyring.cfg` stays there, still signed in and invisible to a keychain-only sweep. `./uninstall.sh --scan` resolves the effective backend and reads both stores regardless of which one is active — see [`docs/uninstall.md`](../uninstall.md).

---

Found a problem on this page? [Open an issue](https://github.com/pipefy/ai-toolkit/issues/new?template=docs_problem.yml&page=docs/cli/auth-reference.md), or [edit the page](https://github.com/pipefy/ai-toolkit/edit/main/docs/cli/auth-reference.md).
