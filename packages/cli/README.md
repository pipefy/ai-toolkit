# pipefy-cli

Typer-based CLI for Pipefy. Exposes the MCP tool capabilities as terminal commands for people and scripts. Depends on [`pipefy`](../sdk/README.md) for GraphQL calls.

## Install

```sh
uvx --from pipefy-cli pipefy --help
```

Or persistently:

```sh
uv tool install pipefy-cli
```

`pipefy-cli` and its dependencies (`pipefy`, `pipefy-auth`) are published to PyPI, so `uv` resolves the whole set from there. While the toolkit ships only pre-release versions (the 0.x line), `uv` resolves the latest pre-release automatically; once a stable release exists it resolves that instead. Do not pass a global `--prerelease allow`: it also lets transitive dependencies jump to their own pre-releases, which can pull a broken build. The console script is `pipefy`, so `uvx --from pipefy-cli` runs it as `pipefy`.

## Quick start

```bash
# Show all commands
pipefy --help

# Card operations
pipefy card get 12345 --json
pipefy card list --pipe 67890
pipefy card create --pipe 67890 --title "New card"
```

Agent skills are installed separately via [`skills.sh`](https://github.com/vercel-labs/skills); see [`skills/README.md`](../../skills/README.md).

## Configuration

The CLI reads the same `PIPEFY_*` environment variables as `pipefy-mcp-server`, and it loads a `.env` file from the working directory. To sign in from a terminal, run `pipefy auth login`. For unattended use, set `PIPEFY_SERVICE_ACCOUNT_CLIENT_ID` and `PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET`, or `PIPEFY_TOKEN`.

[`docs/cli/auth.md`](../../docs/cli/auth.md) explains the credential precedence and the troubleshooting steps. [`docs/config.md`](../../docs/config.md) is the reference for every variable.

## Output modes

Every command defaults to **Rich-formatted** human output. Add `--json` for machine-readable JSON to stdout.

```bash
pipefy card get 12345 --json | jq '.title'
```

## Parity with MCP

Every MCP tool has a CLI counterpart (or a tracked deferral). See [`docs/parity.md`](../../docs/parity.md) for the full matrix.

## Shell completion

```bash
pipefy --install-completion bash    # or zsh, fish, etc.
```
