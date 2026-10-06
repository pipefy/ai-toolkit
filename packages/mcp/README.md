# pipefy-mcp-server

MCP server for Pipefy, for AI agents (Cursor, Claude Desktop, Claude Code, Codex, and any MCP-compatible client). Depends on [`pipefy`](../sdk/README.md) for all GraphQL and API logic.

## Install

```sh
uvx pipefy-mcp-server
```

`pipefy-mcp-server` and its workspace dependencies (`pipefy`, `pipefy-auth`, `pipefy-infra`) are published to PyPI, so `uvx` resolves the whole set from there. While the toolkit ships only pre-release versions (the 0.x line), `uvx` resolves the latest pre-release automatically; once a stable release exists it resolves that instead. Do not pass a global `--prerelease allow`: it also lets transitive dependencies jump to their own pre-releases, which can pull a broken build.

For per-client wiring (Claude Code / Cursor / Claude Desktop / Codex), see [root `README.md#installation`](../../README.md#installation). To remove the server, see [`docs/uninstall.md`](../../docs/uninstall.md).

## Configuration

Set the following environment variables (or add them to a `.env` file in the working directory, or pin them in `~/.config/pipefy/config.toml`):

```env
PIPEFY_SERVICE_ACCOUNT_CLIENT_ID=your_client_id
PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET=your_client_secret
```

[`docs/config.md`](../../docs/config.md) is the reference for every `PIPEFY_*` variable, including the non-prod URLs and the legacy names. [`docs/cli/auth.md`](../../docs/cli/auth.md#troubleshooting) covers keychain errors.

## Claude Code: local stdio

Use this when you want the full local tool surface rather than the [hosted MCP](../../README.md#1-hosted-mcp-claude-code). Do not also register the Claude Code plugin under the same server name.

```bash
claude mcp add --scope project pipefy \
  -- uvx pipefy-mcp-server
claude mcp add-env pipefy PIPEFY_SERVICE_ACCOUNT_CLIENT_ID <YOUR_CLIENT_ID>
claude mcp add-env pipefy PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET <YOUR_CLIENT_SECRET>
```

The plugin's `.mcp.json` points at the hosted URL (`https://mcp.pipefy.com/mcp`). To run local stdio after you installed the plugin, uninstall the plugin or disable its server first.

## Tools

The root [`README.md`](../../README.md#mcp-server) lists the tool domains, with a link to the reference for each. [`cross-cutting.md`](../../docs/mcp/tools/cross-cutting.md) covers the behavior that every tool shares.
