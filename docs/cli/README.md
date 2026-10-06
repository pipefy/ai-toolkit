# CLI documentation

Material here describes **`pipefy-cli`** (Typer): terminal workflows, flags, and patterns that are not duplicated in the MCP tool docs.

## Contents

| Path | Description |
|------|-------------|
| [`auth.md`](auth.md) | Credential precedence, `pipefy auth login`, env vars, and troubleshooting for the four supported auth sources |
| [`self-healing.md`](self-healing.md) | Discover GraphQL operations with `pipefy introspect`, then run `pipefy graphql exec` (mutations require `--yes`) |

## Quick conventions

- **Output:** commands default to Rich tables/text; add **`--json`** for machine-readable stdout.
- **Destructive actions:** a command that deletes asks for confirmation, and **`--yes`** skips the prompt.
- **Configuration:** same **`PIPEFY_*`** keys as the MCP server; see **[`../config.md`](../config.md)**.
- **Flags:** `pipefy <command> --help` documents each command's arguments and flags.

Parity with MCP tools: **[`../parity.md`](../parity.md)**.
