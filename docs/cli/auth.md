# Sign in with the CLI

The `pipefy` CLI accepts a credential from four sources. This page shows how to set up each source and how to fix a failed sign-in. [`auth-reference.md`](auth-reference.md) holds the precedence between the sources, the `pipefy auth` commands, their flags and exit codes, and how a stored session behaves. [`docs/config.md`](../config.md) holds the default and effect of each `PIPEFY_*` variable. To find and remove every credential that this toolkit stored, see [`docs/uninstall.md`](../uninstall.md).

Pick the source by who the commands must act as:

- To act as your own Pipefy user, [sign in as yourself](#sign-in-as-yourself).
- To run in CI, in a script, or in an MCP server, [use a service account](#use-a-service-account).
- To run one command with a token you already hold, [pass a token for one command](#pass-a-token-for-one-command).

## Sign in as yourself

Use this when you want commands to run **as your Pipefy user** — useful for parity with the app's permission model and for AI-automation features that need a real user identity.

```bash
uv run pipefy auth login
```

`PIPEFY_BASE_URL` defaults to `https://app.pipefy.com` (drives the four API endpoints) and `PIPEFY_AUTH_URL` defaults to `https://signin.pipefy.com/realms/pipefy` (the OIDC issuer). Export non-prod values only when targeting a non-prod environment.

This opens your browser, completes an OAuth 2.0 Authorization Code + PKCE flow against the Pipefy identity provider, and writes the resulting session (access token + refresh token + minimal metadata) into your OS keychain.

After login, every other `pipefy <cmd>` invocation transparently reuses that session and refreshes the access token on demand.

## Use a service account

Use this for CI, scripts, MCP servers, and any context where opening a browser isn't an option. Get the client id and secret from **Pipefy Admin → Service Accounts** and put them in `.env` at the repo root:

```env
PIPEFY_SERVICE_ACCOUNT_CLIENT_ID=<SERVICE_ACCOUNT_CLIENT_ID>
PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET=<SERVICE_ACCOUNT_CLIENT_SECRET>
# Non-prod environments only:
# PIPEFY_BASE_URL=https://<your-api-host>
# PIPEFY_AUTH_URL=https://<your-signin-host>/realms/<realm>
```

The CLI loads `.env` from the current working directory; see [`docs/config.md#precedence`](../config.md#precedence) for the full pydantic-settings precedence rules.

## Pass a token for one command

For a single command — or to override the precedence chain on the fly:

```bash
uv run pipefy --token "$MY_BEARER" pipe list
# or
PIPEFY_TOKEN="$MY_BEARER" uv run pipefy pipe list
```

`--token` wins over every other source, including a stored session and `PIPEFY_SERVICE_ACCOUNT_*`.

## Headless / SSH

The PKCE flow needs a loopback HTTP server on `127.0.0.1:<ephemeral>` and a browser that can reach it. SSH sessions and headless boxes break both assumptions.

Options:

1. **Run `pipefy auth login` on your laptop**, then copy `.env` plus the relevant secrets over. The keychain entry itself doesn't transfer between machines.
2. **Use a service account** (`PIPEFY_SERVICE_ACCOUNT_*`) on the headless box — this is the canonical answer for CI and servers.
3. **Static bearer** via `PIPEFY_TOKEN` for short-lived debugging.

## Fix a failed sign-in

Each entry below starts from the message that the CLI prints.

### `Stored Pipefy session could not be refreshed: <reason>`

The keychain has a session but its refresh token won't exchange. Most common causes: the refresh token's absolute lifetime expired, you signed out of the IdP, or the issuer URL changed (e.g. you switched between prod and piporacle without re-logging). Re-run `pipefy auth login`.

### `String should match pattern '<regex>'` (any `PIPEFY_*` env var)

Every `PIPEFY_*` env var is validated against a semantically meaningful regex at settings load — URL env vars (`PIPEFY_BASE_URL`, `PIPEFY_AUTH_URL`) must start with `http(s)://`, credentials must not begin/end with whitespace, `PIPEFY_ORG_ID` must be a numeric string. Empty / blank / specially-charactered values are rejected at construction — there's no overload of `PIPEFY_<NAME>=""` for opt-out semantics. To turn the stored-session tier off without unsetting `PIPEFY_AUTH_URL`, use `PIPEFY_DISABLE_STORED_SESSION=1` (see [Keychain backends](auth-reference.md#keychain-backends)). Otherwise unset the variable to fall back to the prod default (for URLs) or to leave the tier unconfigured (for credentials). The error message names the offending field plus the violated pattern.

> **`VAR= command` is not "unset".** A shell command-prefix assignment (`PIPEFY_AUTH_URL= pipefy auth status`) sets the variable to the empty string for the child process; it does **not** unset it. Pydantic then rejects the empty value and the command exits with a `ValidationError`. To actually unset a variable for a single command, use `env -u VAR command` (POSIX one-shot, leaves the parent shell untouched):
>
> ```sh
> env -u PIPEFY_AUTH_URL pipefy auth status
> ```
>
> To unset for the remainder of the current shell session, `unset PIPEFY_AUTH_URL` (bash / zsh) or `set -e PIPEFY_AUTH_URL` (fish).

### `Login succeeded but the session could not be stored in your keychain (<backend>)`

The login worked but `keyring` couldn't write the entry.

**macOS (Keychain / `Keyring` backend).** OAuth can succeed while persistence fails with `Can't store password on keychain: (-25244, 'Unknown Error')`. That code is `errSecInvalidOwnerEdit` from Security.framework ("Invalid attempt to change the owner of this item") — not `errSecParam` (`-50`). The `keyring` macOS backend deletes any existing item and re-adds it on every write, so a stale entry created by another Python binary (for example a previous `uvx` cache path, or a login from Terminal.app followed by a write from an IDE/agent host) can surface this error. The root cause is not fully pinned; treat the steps below as remediation, not a proven mechanism.

1. Clear the entry with `pipefy auth logout`, which removes a stored entry even when that entry can no longer be parsed. If it fails, remove the entry directly with `security delete-generic-password -s pipefy`.
2. Run `pipefy auth login` again.
3. Prefer running that login from a regular **Terminal.app** session; if macOS prompts for keychain access, click **Always Allow**.
4. If the OS keychain remains unusable, set `PIPEFY_KEYCHAIN_BACKEND=file` (plaintext under the Pipefy config directory) or use a static `PIPEFY_TOKEN`.

Stable installs (`uv tool install` / wheel) keep a stable Python binary path across runs; with `uvx`, a path change after `uvx --refresh` or a uv version bump can recreate a cross-binary ownership mismatch and require clearing the entry again.

**Linux (headless / CI).** Usually no Secret Service daemon — install `gnome-keyring` or `kwallet`, set `PIPEFY_KEYCHAIN_BACKEND=file` for a plaintext file backend under the Pipefy config directory, or use a static `PIPEFY_TOKEN`.

**Windows.** Credential Manager may reject the write (including from non-interactive callers). Run `pipefy auth login` once from an interactive Command Prompt or PowerShell window, or use `PIPEFY_KEYCHAIN_BACKEND=file` / `PIPEFY_TOKEN`.

When `PIPEFY_KEYCHAIN_BACKEND=file` is active the backend reports as `PlaintextKeyring` and the CLI hint switches to a config-directory writability check (the file backend writes to `keyring.cfg` under the resolved config directory).

### `Missing Pipefy authentication. Set PIPEFY_TOKEN, configure PIPEFY_SERVICE_ACCOUNT_*, or run \`pipefy auth login\`.`

No source resolved. Pick one from [Credential precedence](auth-reference.md#credential-precedence). You can also pass `--token <bearer>` for a one-off override.

### `Note: PIPEFY_SERVICE_ACCOUNT_* is set in your environment; other pipefy commands will continue to use it ...`

You ran `pipefy auth login` successfully, but a higher-precedence source is set in your shell. That source will keep being used until you unset it. Common when a `.env` file sets `PIPEFY_SERVICE_ACCOUNT_*` and the user expects the stored session to take over. During the deprecation window the warning fires identically for the legacy `PIPEFY_OAUTH_*` triple, naming whichever form is actually set.

### Identity mismatch (commands run as the wrong user)

Run `whoami`-style queries (e.g. `pipefy graphql exec --query '{ me { email name } }'`) to confirm which identity the CLI is actually using. If you expected your own user but see a service account, check whether `--token`, `PIPEFY_TOKEN`, or a complete `PIPEFY_SERVICE_ACCOUNT_*` triple (or the legacy `PIPEFY_OAUTH_*` form) is set in your environment — any of them outranks the stored session.

### `State mismatch on OAuth callback (possible CSRF)`

The browser came back with a different `state` than the CLI sent. Re-run `pipefy auth login`. If it happens repeatedly, suspect a stale browser tab from a previous login attempt.

---

Found a problem on this page? [Open an issue](https://github.com/pipefy/ai-toolkit/issues/new?template=docs_problem.yml&page=docs/cli/auth.md), or [edit the page](https://github.com/pipefy/ai-toolkit/edit/main/docs/cli/auth.md).
