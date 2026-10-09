# Installation

Pick a path based on your client and whether you need the full tool set. The root [`README.md`](../README.md) has the first command for each path. This page has each path in full with its common flags and caveats, how to switch between paths, plus [tool-surface selection](#choosing-a-tool-surface) and [testing the Claude Code plugin from a checkout](#test-the-claude-code-plugin-from-a-local-checkout).

- In Cursor and want the fastest start with no local setup? → **Cursor Marketplace plugin**.
- In Claude Code and want the fastest start with no local setup? → **Hosted MCP**.
- In Claude Code and want the CLI, `/pipefy:*` slash commands, or skills on the hosted MCP? → **Claude Code plugin**.
- On Cursor, Claude Desktop, or Codex and need the local-file tools, the CLI, or one command for everything? → **Quick-install script**.
- Terminal, scripting, or CI, with no agent? → **CLI only**.
- Just want the workflow playbooks in any agent? → **Skills only**.

| Install path | MCP server runs on | Tools available | Auth | Also installs | Best for |
|---|---|---|---|---|---|
| **[Cursor Marketplace plugin](#6-cursor-marketplace-plugin)** | Pipefy cloud (HTTPS) | Remote-safe surface; local-file tools withheld | In-client OAuth | skills | Fastest start in Cursor; zero local Python |
| **[Hosted MCP](#1-hosted-mcp-claude-code)** | Pipefy cloud (HTTPS) | Remote-safe surface; local-file tools withheld | In-client OAuth | nothing else | Fastest start in Claude Code; zero local Python |
| **[Claude Code plugin](#2-claude-code-plugin)** | Pipefy cloud (HTTPS) | Remote-safe surface; local-file tools withheld | In-client OAuth | slash commands + skills + CLI | Claude Code users who want slash commands, skills, and the CLI on the hosted MCP |
| **[Quick-install script](#3-quick-install-script)** | Your machine (stdio) | Full [tool surface](../README.md#mcp-server) | `pipefy auth login` | CLI + skills, wired into your client config | Local-file tools, CLI, Claude Desktop / Codex, or one-command full setup |
| **[CLI only](#4-cli-only)** | none (no MCP) | CLI commands ([parity](parity.md)) | login or service account | nothing else | Terminal use, scripting, CI |
| **[Skills only](#5-skills-only)** | none | none | none | markdown playbooks | Adding playbooks to any agent |

> **Claude Code is the recommended client** and the most complete, best-tested path. In Cursor, prefer the [Marketplace plugin](#6-cursor-marketplace-plugin) over the Quick-install script unless you need the local-file tools or the CLI. The Cursor Marketplace listing is a reviewed snapshot; Cursor publishes a new version after it approves each resubmission. Contributors can always load a checkout as a local plugin (section 6). Claude Desktop and Codex use the script.

> **Register exactly one Pipefy MCP server.** Do not mix the hosted HTTP server with a local stdio or plugin server, whatever they are named. To check a machine, including one this repository never installed for you:
>
> ```sh
> curl -LsSf https://raw.githubusercontent.com/pipefy/ai-toolkit/main/uninstall.sh | sh -s -- --scan
> ```
>
> That reports every registration and how each one is reached. It removes nothing, edits nothing, and exits `0` when it finds nothing, `1` when findings remain, `2` when a source could not be inspected. A registration is matched on what it **runs** (the `pipefy-mcp-server` command, a known runner invoking it, or the host `mcp.pipefy.com`), so one registered under any other name is still found. First-time setup checklist to hand your agent: [`skills/onboarding/pipefy-toolkit-setup/SKILL.md`](../skills/onboarding/pipefy-toolkit-setup/SKILL.md). Removing a path, or moving between them: [Uninstalling](#uninstalling-and-switching-between-paths) and [`docs/uninstall.md`](uninstall.md).

> **Too many tools for your client?** The local paths can expose a subset instead of the whole catalog: by subject domain, by persona profile, or as four catalog meta-tools the agent searches on demand. See [Choosing a tool surface](#choosing-a-tool-surface). That selection (`PIPEFY_MCP_TOOLSETS`) applies to the local stdio path only. Any client on the hosted URL receives the remote-safe surface.

**Authentication** (for the local paths; the hosted server uses its own in-client OAuth):

- **Human OAuth (interactive):** `pipefy auth login` runs the browser flow and stores a session in your OS keychain. Pipe access is whatever the signed-in user already has.
- **Service account (unattended / CI):** provision one in [Pipefy Admin](https://app.pipefy.com/) (Admin → Service Accounts), add it to every pipe the tools should touch, and set `PIPEFY_SERVICE_ACCOUNT_CLIENT_ID` / `PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET`.

Full env-var reference and `config.toml` precedence: [`docs/config.md`](config.md).

> **Pre-1.0 note:** builds ship as pre-releases to PyPI on every tag (`uvx` and `uv tool install` resolve them automatically; the stable default lands at **v1.0**). The current line is the release GitHub marks **Latest** ([releases/latest](https://github.com/pipefy/ai-toolkit/releases/latest)); alpha tags are staging cuts. PyPI also carries the staging alphas, so pin a version when you need the same build `install.sh` installs. Installing `pipefy-cli` pulls `pipefy`, `pipefy-auth`, and `pipefy-infra` transitively. To pin a version use the PEP 440 form (`pipefy-cli==X.Y.ZbN` for tag `vX.Y.Z-beta.N`); do **not** pass a global `--prerelease allow` (it lets transitive deps jump to their own pre-releases and can pull a broken build).

## 1. Hosted MCP (Claude Code)

**Pick this when:** you're in Claude Code and want the fastest start with zero local Python. The server runs on Pipefy's infrastructure and exposes the **remote-safe surface**: reads, create / update / delete, and the raw GraphQL escape hatch, within your own API permissions. Withheld are only the tools whose input is a file on your machine (knowledge-base document upload, custom LLM-provider create and update); attachment uploads still work from a URL or a presigned upload target instead of a local path.

```bash
claude mcp add --transport http --scope user --client-id pipefy-mcp pipefy https://mcp.pipefy.com/mcp
```

Complete the browser login when prompted (`claude mcp login pipefy` if the client reports *Needs authentication*). If a local or plugin Pipefy MCP server is already registered, remove it first, under whatever name it carries: a second registration shadows this one and a plugin-provided server ranks below user scope. `./uninstall.sh --scan` names them; the switch is in [`docs/uninstall.md`](uninstall.md#to-hosted). Need the CLI and slash commands too? Use the [Claude Code plugin](#2-claude-code-plugin) instead. Hand-wired local stdio: [`packages/mcp/README.md`](../packages/mcp/README.md).

## 2. Claude Code plugin

**Pick this when:** you're in Claude Code and want the hosted MCP server plus the `/pipefy:*` slash commands, the skill catalog, and the CLI. The plugin's `.mcp.json` is the same hosted URL the Cursor plugin uses (`https://mcp.pipefy.com/mcp`). Local-file tools stay on the [Quick-install script](#3-quick-install-script).

```text
/plugin marketplace add pipefy/ai-toolkit
/plugin install pipefy
/pipefy:install
/pipefy:pipefy-login
```

Type the slash commands **in order** (the model cannot invoke `/plugin …` for you). `/plugin install pipefy` (`/plugin install pipefy@pipefy` is the same install, written with the marketplace name) registers the hosted MCP server plus the `/pipefy:install` and `/pipefy:pipefy-login` commands; `/pipefy:install` runs `uv tool install --force pipefy-cli` from PyPI once to put `pipefy` on PATH (idempotent); `/pipefy:pipefy-login` runs the OAuth browser flow for the CLI. MCP sign-in for the hosted server is the in-client OAuth prompt. Hand-wired local stdio, the macOS `errSecInvalidOwnerEdit` keychain note, and the contributor local-clone alternative: [`packages/mcp/README.md`](../packages/mcp/README.md). To run a local branch as the plugin, see [Test the plugin from a local checkout](#test-the-claude-code-plugin-from-a-local-checkout).

## 3. Quick-install script

**Pick this when:** you need the local-file tools or the CLI, or you're on Claude Desktop or Codex. One command installs the CLI and the local MCP server from the release wheels, optionally adds skills, and registers the server in your client config. In Cursor, prefer the [Marketplace plugin](#6-cursor-marketplace-plugin) unless you need that local surface.

```sh
curl -fsSL https://raw.githubusercontent.com/pipefy/ai-toolkit/main/install.sh \
  | sh -s -- --client cursor
```

Replace `--client cursor` with one of `claude-code`, `claude-desktop`, `codex`, or `none` (prints the snippet to paste). Useful flags: `--yes` (skip prompts), `--no-skills` (skip `npx skills add`), `--version vX.Y.Z` (pin a [Release](https://github.com/pipefy/ai-toolkit/releases)), `--dry-run` (print commands without executing), `--prefix <dir>` (passed to `uv tool install` as `UV_TOOL_DIR`), `--allow-root` (opt-in; refused by default). After install, run `pipefy auth login`; on a headless host, use a service account instead (see [`docs/cli/auth.md`](cli/auth.md#headless--ssh)). The installer puts `pipefy-mcp-server` on PATH, so each client's config collapses to `{"command": "pipefy-mcp-server"}`.

> **Production / shared environments:** pin an explicit release with `--version vX.Y.Z` (and prefer fetching `install.sh` from that same [Release](https://github.com/pipefy/ai-toolkit/releases) tag, not the floating `main` branch). Untagged/`@latest`-style installs are fine for local experiments; they are not the default practice for reproducible or corporate rollouts.

## 4. CLI only

**Pick this when:** you want terminal commands, scripting, or CI, without an agent or MCP server.

```sh
uvx --from pipefy-cli pipefy --help        # ad-hoc, no install

uv tool install pipefy-cli                 # permanent install
pipefy --install-completion                # detects your shell (bash, zsh, fish)
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

**Pick this when:** you're in Cursor and want the hosted MCP server with browser sign-in and no local Python. The plugin ships the skill catalog and points Cursor at `https://mcp.pipefy.com/mcp`. Cursor runs the OAuth flow. The surface is the hosted deployment's remote-safe surface. Withheld are the tools whose input is a file on your machine; attachment uploads still work from a URL or a presigned upload target. Toolset selection (`PIPEFY_MCP_TOOLSETS`) does not apply to the hosted URL; use the [Quick-install script](#3-quick-install-script) when you need that, or the local-file tools.

Install **Pipefy** from the Cursor Marketplace (the listing is a reviewed snapshot; Cursor publishes a new version after it approves each resubmission). Complete the browser sign-in when Cursor prompts, then fully restart Cursor before the first tool call. This path installs no `uv` or CLI and needs no token. This path has no `/install` or `/pipefy-login` commands (those files belong to the [Claude Code plugin](#2-claude-code-plugin), where they surface namespaced as `/pipefy:install` and `/pipefy:pipefy-login`). Skills may appear in the slash palette as `/pipefy-*`.

This path and any user-config Pipefy MCP entry (including one written by `install.sh --client cursor`) both occupy Cursor's MCP list. They are mutually exclusive, the same rule as mixing hosted HTTP with local stdio. The registration key is free text: delete the matching key from `~/.cursor/mcp.json` (Windows: `%USERPROFILE%\.cursor\mcp.json`) and keep the Marketplace plugin. `./uninstall.sh --scan` prints the name it found; the switch is in [`docs/uninstall.md`](uninstall.md#to-the-cursor-marketplace-plugin).

To load this checkout as a local plugin (contributors): Cursor rejects a symlink whose target is outside `~/.cursor/plugins/local` (it logs `loadUserLocalPlugin pipefy rejected`). Copy the plugin files into that directory as a real folder, then fully restart Cursor. If `~/.cursor/plugins/local/pipefy` is already a symlink to this checkout, `rm` the link first; that does not delete the repo. Copying `commands/` is optional: the Cursor manifest declares `"commands": []`, so neither a local copy nor a Marketplace tarball of this repo surfaces `/install` or `/pipefy-login`. Include it if you want the copy to match what ships.

```sh
dest="$HOME/.cursor/plugins/local/pipefy"
if [ -L "$dest" ]; then rm "$dest"; fi
mkdir -p "$dest/assets"
cp -R .cursor-plugin skills LICENSE NOTICE README.md .mcp.json "$dest/"
cp assets/logo.svg "$dest/assets/"
```

Remove a copy with `rm -rf ~/.cursor/plugins/local/pipefy`. Remove only a leftover symlink with `rm ~/.cursor/plugins/local/pipefy`.

## Uninstalling, and switching between paths

`uninstall.sh` sits beside `install.sh` and reverses the script, CLI, hosted-user-config, and Claude Code plugin paths, including one this repository never installed for you. It does **not** uninstall the Cursor Marketplace plugin (that lives in Cursor's plugin UI). `--scan` still reports a competing `~/.cursor/mcp.json` registration if one exists (including `install.sh --client cursor`).

```sh
# Report only: what is on this machine, across every channel and client.
curl -LsSf https://raw.githubusercontent.com/pipefy/ai-toolkit/main/uninstall.sh | sh -s -- --scan

# Then remove what you approve. Approval is asked in three tiers.
curl -LsSf https://raw.githubusercontent.com/pipefy/ai-toolkit/main/uninstall.sh | sh
```

`--scan` changes nothing and exits `0` clean / `1` findings remain / `2` a source could not be inspected. A registration is matched on what it **runs** (the `pipefy-mcp-server` command, a known runner invoking it, or the host `mcp.pipefy.com`), so an entry registered under any other name is still found, and removed under that name. Useful flags: `--dry-run`, `--yes`, `--keep-credentials`, `--keep-config`, `--client <id>`, `--allow-root`.

**Switching paths is remove-then-add**: register exactly one Pipefy MCP server at a time, since a plugin-provided server ranks below user scope and a leftover entry silently wins. Full teardown reference, the per-channel switching recipes, and what is never removed by design: [`docs/uninstall.md`](uninstall.md).

## Install from PyPI by name

The MCP server and CLI also resolve straight from PyPI by name. Until v1.0 these commands pick the newest pre-release, which can be a staging alpha; pin a version for a beta:

```sh
uvx pipefy-mcp-server
uv tool install pipefy-cli
```

Deprecation and semver after v1.0: [`docs/DEPRECATION.md`](DEPRECATION.md).

## Choosing a tool surface

Not every client wants every tool. Three independent controls decide what `tools/list` returns:

| Control | Set with | Effect |
|---|---|---|
| **Launch profile** | `--profile local` / `remote` | The security floor. `local` registers every tool; `remote` serves only the remote-safe surface and validates an inbound bearer per request. |
| **Toolset selection** | `--toolsets` / `PIPEFY_MCP_TOOLSETS` | Narrows within that floor by **subject domain** (`workflow`, `database`, `interfaces`, `automation`, `intelligence`, `analytics`, `governance`, `integration`) or by **persona profile** (`requester`, `operator`, `manager`, `builder`, `admin`, `auditor`); multiple names are unioned. Selection never widens past the floor. |
| **Power discovery** | `--toolsets power` | Replaces the curated tools with four catalog meta-tools (`get_tool_categories`, `search_tools`, `describe_tool`, `execute_tool`) plus the raw-GraphQL tools, so the working set stays small no matter how large the catalog grows. |

The toolset names group tools differently from the per-domain reference in [`docs/mcp/`](mcp/README.md): those guides follow documentation areas, while subject domains follow the job a tool serves (card relations land in `workflow`, table relations in `database`). Passing an unrecognized name is a startup error that prints the full list of valid ones. `--toolsets` / `PIPEFY_MCP_TOOLSETS` is a process-level switch: it applies to the local stdio server only, not to the hosted URL.

Per-name definitions and precedence: [`docs/config.md`](config.md). Taxonomy rationale (why subject domains, why personas overlap): [`packages/mcp/AGENTS.md`](../packages/mcp/AGENTS.md).

## Test the Claude Code plugin from a local checkout

The [Claude Code plugin install](#2-claude-code-plugin) adds the marketplace from the `pipefy/ai-toolkit` GitHub repo, which tracks `main`. To run **your local branch** (e.g. `dev`) as the plugin instead, point the marketplace at your clone:

```text
/plugin marketplace add /absolute/path/to/ai-toolkit
/plugin install pipefy@pipefy
```

Whatever branch is checked out in that clone is what loads. Use the `plugin@marketplace` form (`pipefy@pipefy`) since the marketplace and the plugin share the name `pipefy`. After editing plugin files (skills, commands), run `/reload-plugins` to pick up changes without restarting.

> **Already installed the GitHub version?** A marketplace named `pipefy` can be registered only once, and a marketplace declared in `~/.claude/settings.json` under `extraKnownMarketplaces` is locked: `/plugin marketplace add` becomes a no-op (`already on disk — declared in user settings`) and keeps pointing at GitHub. Run `/plugin marketplace remove pipefy` first (or delete that `extraKnownMarketplaces` entry), **then** add the local path. Why removing a marketplace does not always stick: [`docs/uninstall.md`](uninstall.md#two-things-that-come-back).
