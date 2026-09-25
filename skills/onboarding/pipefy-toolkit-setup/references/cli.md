# CLI reference

## Local toolkit and CLI setup

Read the canonical README blocks verbatim; do not invent alternate commands.

| Path | README section | Outcome |
|------|----------------|---------|
| Local toolkit | [Quick install](https://github.com/pipefy/ai-toolkit/blob/main/README.md#3-quick-install-script) | `install.sh` → local server + CLI, including tools that read local files |
| CLI only | [CLI](https://github.com/pipefy/ai-toolkit/blob/main/README.md#4-cli-only) | `pipefy` on PATH; no MCP |

A local toolkit requires a shell that can run `curl`; `install.sh` can install `uv`.

## Authentication and verification

For local/plugin/CLI installs, run `pipefy auth login` or the Claude Code `/pipefy:pipefy-login` command (see README). Verify the shell installation with `pipefy --version`. Service accounts: [`docs/config.md`](https://github.com/pipefy/ai-toolkit/blob/main/docs/config.md).

| Operation | Command | Read-only |
|-----------|---------|-----------|
| `list_organizations` | `pipefy org list` | Yes |
| `get_organization` | `pipefy org get` | Yes |

If `pipefy: command not found`, use `/pipefy:install` or README [CLI](https://github.com/pipefy/ai-toolkit/blob/main/README.md#4-cli-only); check `$HOME/.local/bin`. On macOS, `errSecInvalidOwnerEdit` is a keychain write error; see [`packages/mcp/README.md`](https://github.com/pipefy/ai-toolkit/blob/main/packages/mcp/README.md).

The Cursor Marketplace plugin installs no CLI. Do not use `pipefy auth login` or `pipefy --version` for that path. The Quick install fallback uses `--client cursor` and installs the local CLI and server; explain that change before offering it.

For any local MCP registration, follow the registration scan and switching rules in [MCP setup](mcp.md). CLI-only should have no MCP registration.
