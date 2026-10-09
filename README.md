![Pipefy Developers: AI Toolkit (MCP Server, Pipefy CLI, GraphQL SDK, Agent Skills)](docs/images/pipefy-developers-banner.png)

<p align="center">
  <a href="https://github.com/pipefy/ai-toolkit/actions/workflows/ci.yml"><img src="https://github.com/pipefy/ai-toolkit/actions/workflows/ci.yml/badge.svg" alt="CI Status" /></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+" /></a>
  <a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/badge/uv-package%20manager-blueviolet" alt="uv package manager" /></a>
  <a href="https://modelcontextprotocol.io/introduction"><img src="https://img.shields.io/badge/MCP-Server-orange" alt="MCP Server" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License" /></a>
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#installation">Installation</a> •
  <a href="#what-the-toolkit-connects-to-and-installs">What it connects to</a> •
  <a href="#mcp-server">MCP server</a> •
  <a href="#command-line-interface">CLI</a> •
  <a href="#agent-skills">Agent skills</a> •
  <a href="#documentation">Documentation</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#legal">Legal</a>
</p>

---

## Overview

Connect Claude Code, Cursor, and other AI agents to Pipefy. The toolkit has an MCP server, a CLI, and a GraphQL SDK that call Pipefy's API with the permissions of the account you sign in with, plus agent skills for common Pipefy workflows.

| Component | Package / path | Purpose |
|-----------|----------------|---------|
| **MCP server** | `pipefy-mcp-server` | Pipefy tools for MCP clients (Claude Code, Cursor, Claude Desktop, and others). Hosted at `https://mcp.pipefy.com/mcp`, or run locally for the full catalog. |
| **CLI** | `pipefy-cli` | Most MCP capabilities as terminal commands, for scripting and CI. Coverage and MCP-only tools: [`docs/parity.md`](docs/parity.md). |
| **SDK** | `pipefy` | GraphQL client, services, and models shared by the MCP server and the CLI. |
| **Skills** | [`skills/`](skills/) | Markdown playbooks (Anthropic Skills format) for common Pipefy workflows. |

Feedback and issues: [GitHub Issues](https://github.com/pipefy/ai-toolkit/issues) · **dev@pipefy.com**

---

## Installation

Pick the row for your client and run its command. Flags, caveats, and the remaining steps are in [`docs/install.md`](docs/install.md).

| You are in | Path | Start with |
|---|---|---|
| Claude Code, fastest start | [Hosted MCP](docs/install.md#1-hosted-mcp-claude-code) | `claude mcp add --transport http --scope user --client-id pipefy-mcp pipefy https://mcp.pipefy.com/mcp` |
| Claude Code, with skills, slash commands, and the CLI | [Claude Code plugin](docs/install.md#2-claude-code-plugin) | `/plugin marketplace add pipefy/ai-toolkit`, then `/plugin install pipefy`; `/pipefy:install` adds the CLI and `/pipefy:pipefy-login` signs it in |
| Cursor | [Cursor Marketplace plugin](docs/install.md#6-cursor-marketplace-plugin) | Install **Pipefy** from the Cursor Marketplace |
| Cursor, Claude Desktop, or Codex on macOS or Linux, when you need the local-file tools or the CLI | [Quick-install script](docs/install.md#3-quick-install-script) | Run the install script with `--client cursor`, `claude-desktop`, or `codex` |
| A terminal, a script, or CI | [CLI only](docs/install.md#4-cli-only) | `uv tool install pipefy-cli`, then `pipefy auth login` |
| Any Markdown-aware agent, playbooks only | [Skills only](docs/install.md#5-skills-only) | `npx skills add pipefy/ai-toolkit` |

Register exactly one Pipefy MCP server at a time: the hosted URL, a local server, or a plugin. The [scan command](docs/install.md#uninstalling-and-switching-between-paths) reports what a machine already has and changes nothing. Removing or switching paths: [`docs/uninstall.md`](docs/uninstall.md).

The hosted server signs you in through your client's OAuth prompt. The local paths use `pipefy auth login` (browser OAuth), a service account for unattended use, or a `PIPEFY_TOKEN`. Reference: [`docs/config.md`](docs/config.md) and [`docs/cli/auth.md`](docs/cli/auth.md).

---

## What the toolkit connects to and installs

Network traffic goes to Pipefy hosts and to the storage URLs Pipefy issues, except during installation and when you pass a URL to download:

- **`app.pipefy.com`** (or the host in `PIPEFY_BASE_URL`; `api.pipefy.com` answers the same way): Pipefy's GraphQL API, called with the permissions of the signed-in user, service account, or `PIPEFY_TOKEN`. The `pipefy-api-fallback` skill, used only after the MCP tools and introspection fail, has the agent call this API directly with `curl`, reading the service account or token from `PIPEFY_*` environment variables after telling you which one it will use. GraphQL requests carry `User-Agent: pipefy-sdk/<version> (<surface>)`, `X-Client-Name`, and `X-Client-Version`; the MCP server also reports where it runs (`(mcp; local)` or `(mcp; hosted)` and `X-Client-Deployment`). The toolkit sends no other telemetry.
- **`mcp.pipefy.com`**: Pipefy's hosted MCP server, used by the Hosted MCP path and both plugins. Sign-in is browser OAuth with the public client id `pipefy-mcp`.
- **`signin.pipefy.com`** (or the issuer in `PIPEFY_AUTH_URL`): `pipefy auth login` opens your browser and receives the redirect on `127.0.0.1`. The CLI and the local MCP server refresh that session here, and `pipefy auth logout` revokes it. These requests carry `User-Agent: pipefy-auth/<version>`, `X-Client-Name: auth`, and `X-Client-Version`.
- **`ipaas.pipefy.com`** (or the host in `PIPEFY_IPAAS_URL`): the iPaaS (Advanced Automations) tools.
- **File transfers**: attachment and knowledge-base uploads go to presigned storage URLs that Pipefy issues. A `file_url` you pass is downloaded by the tool, or by Pipefy's server on the hosted path. Report and job exports download from signed Pipefy links.

What the installers and `pipefy auth login` add to your machine:

- **Quick-install script** (macOS and Linux): asks before installing [`uv`](https://docs.astral.sh/uv/) from `astral.sh` when it is missing; uv's installer may add `~/.local/bin` to your shell profile. Reads the newest non-alpha release (or the `--version` tag) from the GitHub API and runs `uv tool install` for `pipefy-cli` and `pipefy-mcp-server` with that release's wheels, including its `pipefy`, `pipefy-auth`, and `pipefy-infra` wheels. Third-party dependencies come from PyPI, and uv may download a Python 3.11+ interpreter when it finds none. With `--client cursor`, `claude-desktop`, or `codex`, writes a `pipefy` entry into that client's config unless one exists. Records the run in `~/.local/state/pipefy/install-receipt` for `uninstall.sh`, and asks before running `npx skills add` (skip with `--no-skills`).
- **`/pipefy:install`** (Claude Code plugin): asks before running `uv tool install --force pipefy-cli` from PyPI.
- **Scan command** (`pipefy-toolkit-setup` skill and [`docs/uninstall.md`](docs/uninstall.md)): downloads `uninstall.sh` from this repository on GitHub and runs it with `--scan`, which reads every source listed under [Scope](docs/uninstall.md#scope), the OS keychain included, and prints what it found. It changes nothing.
- **`npx skills add`**: downloads the third-party `skills` tool from npm and this repository from GitHub, then installs the skills for your agent. The `skills` tool sends its own usage telemetry to `skills.sh` unless `DISABLE_TELEMETRY` or `DO_NOT_TRACK` is set.
- **`pipefy auth login`**: stores the session through Python `keyring`, normally in the OS keychain. With `PIPEFY_KEYCHAIN_BACKEND=file` it is a plaintext file, `keyring.cfg`, in the Pipefy config folder. On a machine where `keyring` finds no OS keychain, it can fall back to its own plaintext file, `python_keyring/keyring_pass.cfg` in the user data folder (`~/.local/share` on Linux). Login and token refresh also keep a lock file, `refresh.lock`, in the Pipefy config folder (`~/.config/pipefy`, or `%APPDATA%\pipefy` on Windows).

---

## MCP server

The local server registers the full catalog (canonical names: `PIPEFY_TOOL_NAMES` in [`registry.py`](packages/mcp/src/pipefy_mcp/tools/registry.py)). The hosted URL serves the remote-safe surface: everything except the tools that read a file from your machine (knowledge-base document upload, custom LLM-provider create and update). There, the attachment tools take a `file_url` instead of a `file_path`.

Per-domain tool reference: [`docs/mcp/`](docs/mcp/README.md). Shared conventions: [`docs/mcp/tools/cross-cutting.md`](docs/mcp/tools/cross-cutting.md). Narrowing the local server to a subset of tools: [Choosing a tool surface](docs/install.md#choosing-a-tool-surface).

---

## Command-line interface

The `pipefy` CLI mirrors the MCP capabilities that [`docs/parity.md`](docs/parity.md) marks as shipped. Most commands print Rich tables by default and JSON with `--json`. On destructive commands, `--yes` skips the prompt; without it, interactive confirmation still runs. `pipefy graphql exec` refuses a mutation unless `--yes` is set.

```sh
pipefy pipe list --json
pipefy card get 123456789
pipefy introspect query pipe
```

Guides: [`docs/cli/`](docs/cli/README.md) and [`packages/cli/README.md`](packages/cli/README.md).

---

## Agent skills

[`skills/`](skills/) holds workflow playbooks (prerequisites, tool tables, steps, success criteria) for any agent that reads Markdown. Catalog: [`skills/README.md`](skills/README.md). Authoring guide: [`skills/AGENTS.md`](skills/AGENTS.md).

---

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/install.md`](docs/install.md) | Every install path in full, switching between them, tool-surface selection, and testing the Claude Code plugin from a checkout. |
| [`docs/README.md`](docs/README.md) | Index of docs by surface (MCP, CLI, SDK) and shared guides. |
| [`docs/config.md`](docs/config.md) | `PIPEFY_*` environment variables, `config.toml` schema and path, precedence chain. |
| [`docs/parity.md`](docs/parity.md) | MCP tool ↔ CLI command matrix. |
| [`docs/uninstall.md`](docs/uninstall.md) | `uninstall.sh --scan` and teardown, and switching between the hosted, local, and plugin channels. |
| [`docs/MIGRATION.md`](docs/MIGRATION.md) | Notes for existing MCP users; configuration remains compatible. |
| [`AGENTS.md`](AGENTS.md) | Repository layout, development workflow, and guidelines for contributors and agents. |
| [`RELEASE.md`](RELEASE.md) | Versioning and release process. |

---

## Contributing

Contributions are welcome via issues and pull requests. Commits must include a [DCO](https://developercertificate.org/) sign-off (`git commit -s`). Skills: [`CONTRIBUTING.md`](CONTRIBUTING.md). MCP, CLI, and SDK: [`AGENTS.md`](AGENTS.md). For a field type the tools do not map, open an issue with the field type and the expected behavior.

---

## Legal

This toolkit (MCP server, CLI, SDK, and skill/blueprint playbooks) is licensed under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for trademark reservations.

Your access to and use of the Pipefy platform through this toolkit is governed by the [Pipefy Solutions Terms and Conditions](https://www.pipefy.com/terms-and-conditions/) ([versão em português](https://www.pipefy.com/pt-br/termos-e-condicoes/)) and, for AI features, by the Pipefy AI Additional Terms (to be published and incorporated by reference into those terms), including their acceptable use provisions. Using this toolkit requires a Pipefy account; nothing in the Apache 2.0 license grants rights to the Pipefy service.

**Templates, not advice.** Skills and blueprints are configurable templates provided for general informational purposes. They do not constitute legal, HR, financial, tax, or other professional advice, and must be reviewed, configured, and validated by qualified professionals before production use. Each published blueprint ships with a `COMPLIANCE.md` describing its intended purpose, out-of-scope uses, AI risk classification, and default human-oversight settings (see [`docs/compliance/COMPLIANCE.template.md`](docs/compliance/COMPLIANCE.template.md)).

**AI-generated output.** Outputs produced by AI features may contain errors or omissions and must be independently verified before being relied upon.

**Beta software.** Pre-1.0 releases are provided "AS IS", without warranties of any kind, and may change or be discontinued at any time. See the full disclaimer in [TERMS.md](TERMS.md).

Security reports: see [SECURITY.md](SECURITY.md). Contributions: see [CONTRIBUTING.md](CONTRIBUTING.md).
