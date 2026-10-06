# Install the toolkit

This guide installs the MCP server, the CLI, or the skills, and wires the MCP server into your client. For a guided first run on the recommended path, follow [`quickstart.md`](quickstart.md) instead.

## Choose a path

Six paths install the toolkit. Pick one based on your client and whether you need the full tool set:

- **In Cursor and want the fastest start with no local setup?** → **Cursor Marketplace plugin**.
- **In Claude Code and want the fastest start with no local setup?** → **Hosted MCP**.
- **In Claude Code and want the CLI, `/pipefy:*` slash commands, or skills on the hosted MCP?** → **Claude Code plugin**.
- **On Cursor, Claude Desktop, or Codex and need the local-file tools, the CLI, or one command for everything?** → **Quick-install script**.
- **Terminal, scripting, or CI, with no agent?** → **CLI only**.
- **Just want the workflow playbooks in any agent?** → **Skills only**.

| Install path | MCP server runs on | Tools available | Auth | Also installs | Best for |
|---|---|---|---|---|---|
| **[Cursor Marketplace plugin](#6-cursor-marketplace-plugin)** | Pipefy cloud (HTTPS) | Remote-safe surface; local-file tools withheld | In-client OAuth | skills | Fastest start in Cursor; zero local Python |
| **[Hosted MCP](#1-hosted-mcp-claude-code)** | Pipefy cloud (HTTPS) | Remote-safe surface: all but the few local-file tools | In-client OAuth | nothing else | Fastest start in Claude Code; zero local Python |
| **[Claude Code plugin](#2-claude-code-plugin)** | Pipefy cloud (HTTPS) | Remote-safe surface; local-file tools withheld | In-client OAuth | slash commands + skills + CLI | Claude Code users who want slash commands, skills, and the CLI on the hosted MCP |
| **[Quick-install script](#3-quick-install-script)** | Your machine (stdio) | Full [tool surface](../README.md#mcp-server) | `pipefy auth login` | CLI + skills, wired into your client config | Local-file tools, CLI, Claude Desktop / Codex, or one-command full setup |
| **[CLI only](#4-cli-only)** | — (no MCP) | CLI commands ([parity](parity.md)) | login or service account | — | Terminal use, scripting, CI |
| **[Skills only](#5-skills-only)** | — | — | — | markdown playbooks | Adding playbooks to any agent |

> **Claude Code is the recommended client** and the most complete, best-tested path today. In Cursor, prefer the [Marketplace plugin](#6-cursor-marketplace-plugin) over the Quick-install script unless you need the local-file tools or the CLI. The Marketplace listing tracks `main`. Contributors can load a checkout as a local plugin: see [Test the Cursor plugin from a local checkout](contributing/development.md#test-the-cursor-plugin-from-a-local-checkout). Claude Desktop and Codex still use the script.

## Before you install

> **Register exactly one Pipefy MCP server** — do not mix the hosted HTTP server with a local stdio or plugin server, whatever they are named. To check a machine, including one this repository never installed for you:
>
> ```sh
> curl -LsSf https://raw.githubusercontent.com/pipefy/ai-toolkit/main/uninstall.sh | sh -s -- --scan
> ```
>
> That reports every registration and how each one is reached. It removes nothing, edits nothing, and exits `0` when it finds nothing, `1` when findings remain, `2` when a source could not be inspected. A registration is matched on what it **runs** — the `pipefy-mcp-server` command, a known runner invoking it, or the host `mcp.pipefy.com` — so one registered under any other name is still found. First-time setup checklist to hand your agent: [`skills/onboarding/pipefy-toolkit-setup/SKILL.md`](../skills/onboarding/pipefy-toolkit-setup/SKILL.md). Removing a path, or moving between them: [Uninstalling](#uninstalling-and-switching-between-paths) and [`docs/uninstall.md`](uninstall.md).

> **Too many tools for your client?** The local paths can expose a subset instead of the whole catalog — by subject domain, by tool profile, or as four catalog meta-tools the agent searches on demand. See [Choosing a tool surface](../README.md#choosing-a-tool-surface). That selection (`PIPEFY_MCP_TOOLSETS`) applies to the local stdio path only. Any client on the hosted URL always receives the remote-safe floor.

**Authentication** (for the local paths; the hosted server uses its own in-client OAuth):

- **Human OAuth (interactive):** `pipefy auth login` runs the browser flow and stores a session in your OS keychain. Pipe access is whatever the signed-in user already has.
- **Service account (unattended / CI):** provision one in [Pipefy Admin](https://app.pipefy.com/) (Admin → Service Accounts), add it to every pipe the tools should touch, and set `PIPEFY_SERVICE_ACCOUNT_CLIENT_ID` / `PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET`.

Full env-var reference and `config.toml` precedence: [`docs/config.md`](config.md).

> **Pre-1.0 note:** builds ship as pre-releases to PyPI on every tag, and `uvx` and `uv tool install` resolve them automatically. The stable default lands at **v1.0**, and the current line is always the [latest release](https://github.com/pipefy/ai-toolkit/releases/latest). `pipefy-cli` and `pipefy-mcp-server` each bring `pipefy`, `pipefy-auth`, and `pipefy-infra` with them. To pin a version, or to recover from a broken dependency, see [Package versions](troubleshooting.md#package-versions).

## 1. Hosted MCP (Claude Code)

**Pick this when:** you're in Claude Code and want the fastest start with zero local Python. The server runs on Pipefy's infrastructure and exposes the **remote-safe surface**: reads, create / update / delete, and the raw GraphQL escape hatch — everything your own API permissions allow. Withheld are only the tools whose input is a file on your machine (knowledge-base document upload, custom LLM-provider credential files); attachment uploads still work from a URL or a presigned upload target instead of a local path.

```bash
claude mcp add --transport http --scope user --client-id pipefy-mcp pipefy https://mcp.pipefy.com/mcp
```

Complete the browser login when prompted (`claude mcp login pipefy` if the client reports *Needs authentication*). If a local or plugin Pipefy MCP server is already registered, remove it first — under whatever name it carries, since a second registration shadows this one and a plugin-provided server ranks below user scope. `./uninstall.sh --scan` names them; the switch is in [`docs/uninstall.md`](uninstall.md#to-hosted). Need the CLI and slash commands too? Use the [Claude Code plugin](#2-claude-code-plugin) instead. Hand-wired local stdio: [`packages/mcp/README.md`](../packages/mcp/README.md).

## 2. Claude Code plugin

**Pick this when:** you're in Claude Code and want the hosted MCP server plus the `/pipefy:*` slash commands, the skill catalog, and the CLI. The plugin's `.mcp.json` is the same hosted URL the Cursor plugin uses (`https://mcp.pipefy.com/mcp`). Local-file tools stay on the [Quick-install script](#3-quick-install-script).

```text
/plugin marketplace add pipefy/ai-toolkit
/plugin install pipefy
/pipefy:install
/pipefy:pipefy-login
```

Type the slash commands **in order** (the model cannot invoke `/plugin …` for you). `/plugin install pipefy` registers the hosted MCP server plus the `/pipefy:install` and `/pipefy:pipefy-login` commands; `/pipefy:install` runs `uv tool install` once to put `pipefy` on PATH (idempotent); `/pipefy:pipefy-login` runs the OAuth browser flow for the CLI. MCP sign-in for the hosted server is the in-client OAuth prompt. Hand-wired local stdio: [`packages/mcp/README.md`](../packages/mcp/README.md). Keychain errors: [`docs/cli/auth.md`](cli/auth.md#troubleshooting). To run a local branch as the plugin, see [Test the Claude Code plugin from a local checkout](contributing/development.md#test-the-claude-code-plugin-from-a-local-checkout).

## 3. Quick-install script

**Pick this when:** you need the local-file tools or the CLI, or you're on Claude Desktop or Codex — one command installs the CLI + local MCP server, optionally adds skills, and registers the server in your client config. In Cursor, prefer the [Marketplace plugin](#6-cursor-marketplace-plugin) unless you need that local surface.

```sh
curl -fsSL https://raw.githubusercontent.com/pipefy/ai-toolkit/main/install.sh \
  | sh -s -- --client cursor
```

Replace `--client cursor` with one of `claude-code`, `claude-desktop`, `codex`, or `none` (prints the snippet to paste). Useful flags: `--yes` (skip prompts), `--no-skills` (skip `npx skills add`), `--version vX.Y.Z` (pin a [Release](https://github.com/pipefy/ai-toolkit/releases)), `--dry-run` (print commands without executing), `--allow-root` (opt-in; refused by default). After install, run `pipefy auth login` (`--device` on headless systems). The installer puts `pipefy-mcp-server` on PATH, so each client's config collapses to `{"command": "pipefy-mcp-server"}`.

> **Production / shared environments:** pin an explicit release with `--version vX.Y.Z` (and prefer fetching `install.sh` from that same [Release](https://github.com/pipefy/ai-toolkit/releases) tag, not the floating `main` branch). Untagged/`@latest`-style installs are fine for local experiments; they are not the default practice for reproducible or corporate rollouts.

## 4. CLI only

**Pick this when:** you want terminal commands, scripting, or CI — no agent or MCP.

```sh
uvx --from pipefy-cli pipefy --help        # ad-hoc, no install

uv tool install pipefy-cli                 # permanent install
pipefy --install-completion bash           # or zsh, fish
pipefy auth login                          # browser OAuth, session in OS keychain
```

CLI deep-dives (auth precedence, `--token` / `PIPEFY_TOKEN`, parity matrix): [`packages/cli/README.md`](../packages/cli/README.md) and [`docs/cli/`](cli/README.md).

## 5. Skills only

**Pick this when:** you just want the workflow playbooks in any Markdown-aware agent (Cursor, Claude Code, Codex, and others).

```sh
npx skills add pipefy/ai-toolkit                           # all skills
npx skills add pipefy/ai-toolkit --skill pipefy-pipes-and-cards
```

Catalog and authoring guide: [`skills/README.md`](../skills/README.md).

## 6. Cursor Marketplace plugin

**Pick this when:** you're in Cursor and want the hosted MCP server with browser sign-in and no local Python. The plugin ships the skill catalog and points Cursor at `https://mcp.pipefy.com/mcp`. Cursor runs the OAuth flow. The surface is the hosted deployment's remote-safe floor. Withheld are the tools whose input is a file on your machine; attachment uploads still work from a URL or a presigned upload target. Toolset selection (`PIPEFY_MCP_TOOLSETS`) does not apply to the hosted URL — use the [Quick-install script](#3-quick-install-script) when you need that, or the local-file tools.

Install **Pipefy** from the Cursor Marketplace (the listing tracks `main`). Complete the browser sign-in when Cursor prompts, then fully restart Cursor before the first tool call. No `uv`, no CLI, no token paste. This path has no `/install` or `/pipefy-login` commands (those files belong to the [Claude Code plugin](#2-claude-code-plugin), where they surface namespaced as `/pipefy:install` and `/pipefy:pipefy-login`). Skills may appear in the slash palette as `/pipefy-*`.

This path and any user-config Pipefy MCP entry (including one written by `install.sh --client cursor`) both occupy Cursor's MCP list. They are mutually exclusive — the same rule as mixing hosted HTTP with local stdio. The registration key is free text: delete the matching key from `~/.cursor/mcp.json` (Windows: `%USERPROFILE%\.cursor\mcp.json`) and keep the Marketplace plugin. `./uninstall.sh --scan` prints the name it found; the switch is in [`docs/uninstall.md`](uninstall.md#to-the-cursor-marketplace-plugin).

## Uninstalling, and switching between paths

`uninstall.sh` sits beside `install.sh` and reverses the script, CLI, hosted-user-config, and Claude Code plugin paths, including one this repository never installed for you. It does **not** uninstall the Cursor Marketplace plugin (that lives in Cursor's plugin UI). `--scan` still reports a competing `~/.cursor/mcp.json` registration if one exists (including `install.sh --client cursor`).

```sh
# Report only: what is on this machine, across every channel and client.
curl -LsSf https://raw.githubusercontent.com/pipefy/ai-toolkit/main/uninstall.sh | sh -s -- --scan

# Then remove what you approve. Approval is asked in three tiers.
curl -LsSf https://raw.githubusercontent.com/pipefy/ai-toolkit/main/uninstall.sh | sh
```

`--scan` changes nothing and exits `0` clean / `1` findings remain / `2` a source could not be inspected. A registration is matched on what it **runs** — the `pipefy-mcp-server` command, a known runner invoking it, or the host `mcp.pipefy.com` — so an entry registered under any other name is still found, and removed under that name. Useful flags: `--dry-run`, `--yes`, `--keep-credentials`, `--keep-config`, `--client <id>`.

**Switching paths is remove-then-add**: register exactly one Pipefy MCP server at a time, since a plugin-provided server ranks below user scope and a leftover entry silently wins. Full teardown reference, the per-channel switching recipes, and what is never removed by design: [`docs/uninstall.md`](uninstall.md).

## Post-1.0 (PyPI, preview)

Once the stable line lands, the MCP server and CLI resolve straight from PyPI by name:

```sh
uvx pipefy-mcp-server
uv tool install pipefy-cli
```

Deprecation and semver (post-1.0): [`docs/DEPRECATION.md`](DEPRECATION.md).
