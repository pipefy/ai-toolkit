# pipefy-auth

Shared OAuth + session storage helpers for Pipefy CLI and MCP server.

## What lives here

- **`storage`**: `StoredSession` storage, one entry per `(issuer, client_id)` tuple under the service name `pipefy`, in the OS keychain or in a file store (DPAPI-encrypted by default on Windows, plaintext with `PIPEFY_KEYCHAIN_BACKEND=file` on any platform).
- **`flow`** — OAuth 2.0 Authorization Code with PKCE login flow.
- **`refresh`** — refresh-token grant + eager pre-use freshness check (`ensure_fresh_session`).
- **`discovery`** — OIDC `.well-known/openid-configuration` fetch + validation.
- **`revoke`** — IdP-side token invalidation (RFC 7009).
- **`identity`** — `OidcClient` dataclass + the `DEFAULT_AUTH_CLIENT_ID` constant (the registered Keycloak public client_id).

## Consumers

`pipefy-cli` and `pipefy-mcp-server` both depend on this package and read the same stored session, so a single `pipefy auth login` serves both binaries.
