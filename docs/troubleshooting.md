# Troubleshooting

This page lists the common failures, by the symptom that you see. Each entry names the cause and the fix. Where another guide owns the full explanation, the entry links to it.

## Install and registration

### The client reports `Needs authentication` for the hosted server

The browser sign-in did not finish. In Claude Code, run `claude mcp login pipefy` and complete the sign-in. In Cursor, start the sign-in again from the MCP settings.

### Tools come from the wrong server, or a removed server still answers

More than one Pipefy MCP server is registered, possibly under different names. A plugin-provided server ranks below a user-scope entry, so removing the user entry alone falls through to the plugin. Run the scan, which changes nothing:

```sh
curl -LsSf https://raw.githubusercontent.com/pipefy/ai-toolkit/main/uninstall.sh | sh -s -- --scan
```

The scan names every registration and where it lives. Keep one, and remove the rest with the recipe in [Switching channels](uninstall.md#switching-channels).

### A removed marketplace or `.mcp.json` entry comes back

A settings file or a git-tracked `.mcp.json` re-adds it in the next session. [Two things that come back](uninstall.md#two-things-that-come-back) shows how to clear each source.

### `pipefy: command not found`

The CLI is not on `PATH`. In Claude Code with the plugin, run `/pipefy:install`. Otherwise, follow [CLI only](install.md#4-cli-only), and check that `$HOME/.local/bin` is on `PATH`.

### The `/pipefy:*` slash commands are missing

The Claude Code plugin is not installed. Follow [Claude Code plugin](install.md#2-claude-code-plugin), and type its slash commands in the order shown. Cursor has no `/pipefy:*` commands.

### A tool from the reference is missing from the client

The tool list depends on the install path. The hosted server withholds the tools whose input is a file on your machine, and a local server started with `PIPEFY_MCP_TOOLSETS` serves only the selected toolsets. [Choosing a tool surface](mcp/README.md#choose-a-tool-surface) explains both.

## Sign-in and credentials

[`cli/auth.md`](cli/auth.md) owns each of these errors, and the MCP server reads the same credentials as the CLI:

| You see | Go to |
|---|---|
| `Login succeeded but the session could not be stored in your keychain`, or macOS `errSecInvalidOwnerEdit` | [Keychain write failure](cli/auth.md#login-succeeded-but-the-session-could-not-be-stored-in-your-keychain-backend) |
| `Stored Pipefy session could not be refreshed` | [Refresh failure](cli/auth.md#stored-pipefy-session-could-not-be-refreshed-reason) |
| `Missing Pipefy authentication` | [No credential found](cli/auth.md#missing-pipefy-authentication-set-pipefy_token-configure-pipefy_service_account_-or-run-pipefy-auth-login) |
| `String should match pattern` for a `PIPEFY_*` variable | [Invalid variable](cli/auth.md#string-should-match-pattern-regex-any-pipefy_-env-var) |
| Commands run as the wrong user | [Identity mismatch](cli/auth.md#identity-mismatch-commands-run-as-the-wrong-user) |
| `State mismatch on OAuth callback` | [State mismatch](cli/auth.md#state-mismatch-on-oauth-callback-possible-csrf) |
| Login fails on a machine with no browser | [Headless / SSH](cli/auth.md#headless--ssh) |

## Package versions

### An install pulls a broken dependency

A global `--prerelease allow` lets every transitive dependency resolve to its own pre-release. Remove the flag: `uvx` and `uv tool install` already resolve the toolkit's pre-releases on their own.

### A pinned version does not resolve

PyPI uses the PEP 440 form of the release tag. The tag `v0.6.0-beta.1` installs as `pipefy-cli==0.6.0b1`, and `v0.5.0-alpha.1` installs as `0.5.0a1`.

## Still stuck

Open an issue with the [bug report form](https://github.com/pipefy/ai-toolkit/issues/new/choose), or write to **<dev@pipefy.com>**. Report a security problem privately, as [`SECURITY.md`](../SECURITY.md) describes.

---

Found a problem on this page? [Open an issue](https://github.com/pipefy/ai-toolkit/issues/new?template=docs_problem.yml&page=docs/troubleshooting.md), or [edit the page](https://github.com/pipefy/ai-toolkit/edit/main/docs/troubleshooting.md).
