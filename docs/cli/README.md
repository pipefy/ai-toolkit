# CLI documentation

Material here describes **`pipefy-cli`** (Typer): terminal workflows, flags, and patterns that are not duplicated in the MCP tool docs.

## Contents

| Path | Description |
|------|-------------|
| [`reference.md`](reference.md) | Every command with its arguments and options, generated from the code |
| [`auth.md`](auth.md) | Set up each of the four credential sources, and fix a failed sign-in |
| [`auth-reference.md`](auth-reference.md) | Credential precedence, the `pipefy auth` commands with their flags and exit codes, and session behavior |
| [`self-healing.md`](self-healing.md) | Discover GraphQL operations with `pipefy introspect`, then run `pipefy graphql exec` (mutations require `--yes`) |

## Quick conventions

- **Output:** commands default to Rich tables/text; add **`--json`** for machine-readable stdout.
- **Destructive actions:** a command that deletes asks for confirmation, and **`--yes`** skips the prompt.
- **Configuration:** same **`PIPEFY_*`** keys as the MCP server; see **[`../config.md`](../config.md)**.
- **Flags:** [`reference.md`](reference.md) lists each command's arguments and flags, and `pipefy <command> --help` prints the same text.

Parity with MCP tools: **[`../parity.md`](../parity.md)**.

---

Found a problem on this page? [Open an issue](https://github.com/pipefy/ai-toolkit/issues/new?template=docs_problem.yml&page=docs/cli/README.md), or [edit the page](https://github.com/pipefy/ai-toolkit/edit/main/docs/cli/README.md).
