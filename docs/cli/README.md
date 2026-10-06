# CLI documentation

Material here describes **`pipefy-cli`** (Typer): terminal workflows, flags, and patterns that are not duplicated in the MCP tool docs.

## Contents

| Path | Description |
|------|-------------|
| [`auth.md`](auth.md) | Set up each of the four credential sources, and fix a failed sign-in |
| [`auth-reference.md`](auth-reference.md) | Credential precedence, the `pipefy auth` commands with their flags and exit codes, and session behavior |
| [`self-healing.md`](self-healing.md) | Discover GraphQL operations with `pipefy introspect`, then run `pipefy graphql exec` (mutations require `--yes`) |

## Quick conventions

- **Output:** commands default to Rich tables/text; add **`--json`** for machine-readable stdout.
- **Destructive actions:** a command that deletes asks for confirmation, and **`--yes`** skips the prompt.
- **Configuration:** same **`PIPEFY_*`** keys as the MCP server; see **[`../config.md`](../config.md)**.
- **Flags:** `pipefy <command> --help` documents each command's arguments and flags.

Parity with MCP tools: **[`../parity.md`](../parity.md)**.
