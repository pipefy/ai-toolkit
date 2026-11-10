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
  <a href="#what-it-connects-to">What it connects to</a> •
  <a href="#mcp-server">MCP server</a> •
  <a href="#command-line-interface">CLI</a> •
  <a href="#agent-skills">Agent skills</a> •
  <a href="#documentation">Documentation</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#legal">Legal</a>
</p>

---

## Overview

Connect Claude Code, Cursor, and other AI agents to Pipefy.

The toolkit has an MCP server, a CLI, and a GraphQL SDK. Those three call Pipefy's API with the signed-in account's permissions. Agent skills cover common Pipefy workflows.

| Component | Package / path | Purpose |
|-----------|----------------|---------|
| **MCP server** | `pipefy-mcp-server` | Pipefy tools for MCP clients (Claude Code, Cursor, Claude Desktop, and others). Hosted at `https://mcp.pipefy.com/mcp`, or run locally for the full catalog. |
| **CLI** | `pipefy-cli` | Most MCP capabilities as terminal commands, for scripting and CI. Coverage and MCP-only tools: [`docs/parity.md`](docs/parity.md). |
| **SDK** | `pipefy` | GraphQL client, services, and models shared by the MCP server and the CLI. |
| **Skills** | [`plugins/pipefy/skills/`](plugins/pipefy/skills/) | Markdown playbooks (Anthropic Skills format) for common Pipefy workflows. |

- **Feedback:** [GitHub Issues](https://github.com/pipefy/ai-toolkit/issues)
- **Email:** **dev@pipefy.com**

---

## Installation

Pick the row for your client and run its command. Flags, caveats, and the remaining steps are in [`docs/install.md`](docs/install.md).

| You are in | Path | Start with |
|---|---|---|
| **Claude Code, fastest start** | [Hosted MCP](docs/install.md#1-hosted-mcp-claude-code) | `claude mcp add --transport http --scope user --client-id pipefy-mcp pipefy https://mcp.pipefy.com/mcp` |
| **Claude Code, with skills, slash commands, and the CLI** | [Claude Code plugin](docs/install.md#2-claude-code-plugin) | `/plugin install pipefy --marketplace pipefy/ai-toolkit` for Claude Code 2.1.275 or later. The install guide has the two-step form for older versions. `/pipefy:install` adds the CLI. `/pipefy:pipefy-login` signs it in. |
| **Cursor** | [Cursor Marketplace plugin](docs/install.md#6-cursor-marketplace-plugin) | Install **Pipefy** from the Cursor Marketplace |
| **Cursor, Claude Desktop, or Codex on macOS or Linux, when you need the local-file tools or the CLI** | [Quick-install script](docs/install.md#3-quick-install-script) | Run the install script with `--client cursor`, `claude-desktop`, or `codex` |
| **A terminal, a script, or CI** | [CLI only](docs/install.md#4-cli-only) | `uv tool install pipefy-cli`, then `pipefy auth login` |
| **Any Markdown-aware agent, playbooks only** | [Skills only](docs/install.md#5-skills-only) | `npx skills add pipefy/ai-toolkit` |

- **One MCP server.** Register exactly one Pipefy MCP server at a time. Use the hosted URL, a local server, or a plugin. The [scan command](docs/install.md#uninstalling-and-switching-between-paths) reports what a machine already has. It changes nothing. To remove or switch paths, see [`docs/uninstall.md`](docs/uninstall.md).
- **Sign-in.** The hosted server uses your client's OAuth prompt. Local paths use `pipefy auth login` (browser OAuth), a service account for unattended use, or a `PIPEFY_TOKEN`. See [`docs/config.md`](docs/config.md) and [`docs/cli/auth.md`](docs/cli/auth.md).

---

## What it connects to

- **Pipefy hosts and storage URLs.** The toolkit calls Pipefy hosts and the storage URLs Pipefy issues.
- **Client headers.** Requests carry a client name and version. The toolkit sends no other telemetry.
- **What an install can add.** An install can add uv, the CLI, a local MCP server, one client config entry, skills, and a keychain session.
- **Third-party skills telemetry.** The `skills` tool sends its own telemetry unless the environment contains `DISABLE_TELEMETRY` or `DO_NOT_TRACK`.

Hosts, headers, and files: [`docs/trust.md`](docs/trust.md).

---

## MCP server

- **Local server.** It registers the full catalog. Canonical names are `PIPEFY_TOOL_NAMES` in [`registry.py`](packages/mcp/src/pipefy_mcp/tools/registry.py).
- **Hosted server.** `https://mcp.pipefy.com/mcp` serves the remote-safe surface. It omits tools that read a file on your machine. Those tools are knowledge-base document upload, and custom LLM-provider create and update.
- **Attachments on the hosted server.** Attachment tools take a `file_url` instead of a `file_path`.
- **Tool reference:** [`docs/mcp/`](docs/mcp/README.md)
- **Shared conventions:** [`docs/mcp/tools/cross-cutting.md`](docs/mcp/tools/cross-cutting.md)
- **Narrow the local server:** [Choosing a tool surface](docs/install.md#choosing-a-tool-surface)

---

## Command-line interface

- The `pipefy` CLI mirrors the MCP capabilities that [`docs/parity.md`](docs/parity.md) marks as shipped.
- Most commands print Rich tables by default and JSON with `--json`.
- On destructive commands, `--yes` skips the prompt.
- Without `--yes`, interactive confirmation still runs.
- `pipefy graphql exec` refuses a mutation unless the command includes `--yes`.

```sh
pipefy pipe list --json
pipefy card get 123456789
pipefy introspect query pipe
```

- **Guides:** [`docs/cli/`](docs/cli/README.md) and [`packages/cli/README.md`](packages/cli/README.md)

---

## Agent skills

- [`plugins/pipefy/skills/`](plugins/pipefy/skills/) holds workflow playbooks for any agent that reads Markdown.
- Each playbook has prerequisites, a tool table, steps, and success criteria.
- **Catalog:** [`plugins/pipefy/README.md`](plugins/pipefy/README.md)
- **Authoring guide:** [`plugins/AGENTS.md`](plugins/AGENTS.md)

---

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/install.md`](docs/install.md) | Every install path in full, switching between them, tool-surface selection, and testing the Claude Code plugin from a checkout. |
| [`docs/trust.md`](docs/trust.md) | Hosts the toolkit calls, request headers, and files an install or login writes. |
| [`docs/README.md`](docs/README.md) | Index of docs by surface (MCP, CLI, SDK) and shared guides. |
| [`docs/config.md`](docs/config.md) | `PIPEFY_*` environment variables, `config.toml` schema and path, precedence chain. |
| [`docs/parity.md`](docs/parity.md) | MCP tool ↔ CLI command matrix. |
| [`docs/uninstall.md`](docs/uninstall.md) | `uninstall.sh --scan` and teardown, and switching between the hosted, local, and plugin channels. |
| [`docs/MIGRATION.md`](docs/MIGRATION.md) | Notes for existing MCP users. Configuration remains compatible. |
| [`AGENTS.md`](AGENTS.md) | Repository layout, development workflow, and guidelines for contributors and agents. |
| [`RELEASE.md`](RELEASE.md) | Versioning and release process. |

---

## Contributing

You can contribute through an issue or a pull request. Each commit needs a [DCO](https://developercertificate.org/) sign-off (`git commit -s`).

- **Skills.** Playbook rules, frontmatter, and review steps are in [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **MCP, CLI, and SDK.** Repository layout, tests, and new capabilities are in [`AGENTS.md`](AGENTS.md).
- **Field types.** If the tools do not map a field type, open an issue with that type and the behavior you expect.

---

## Legal

This toolkit is under the [Apache License 2.0](LICENSE), and use of Pipefy is governed by Pipefy's terms. Read [TERMS.md](TERMS.md) for the full notice.

- **License.** The MCP server, the CLI, the SDK, and the skill and blueprint playbooks are under that license. Pipefy keeps its trademarks. See [NOTICE](NOTICE).
- **Platform terms.** Your use of the Pipefy platform through this toolkit is governed by the [Pipefy Solutions Terms and Conditions](https://www.pipefy.com/terms-and-conditions/) ([versão em português](https://www.pipefy.com/pt-br/termos-e-condicoes/)). AI features also follow the Pipefy AI Additional Terms. Those terms are not published yet, and they will be incorporated by reference into the platform terms, including their acceptable use provisions. You need a Pipefy account. The Apache 2.0 license grants no rights to the Pipefy service.
- **Templates.** Skills and blueprints are configurable templates for general informational purposes. They are not legal, HR, financial, tax, or other professional advice. Qualified professionals must review, configure, and validate them before production use. Each published blueprint ships with a `COMPLIANCE.md` that states the intended purpose, out-of-scope uses, AI risk classification, and default human-oversight settings. See [`docs/compliance/COMPLIANCE.template.md`](docs/compliance/COMPLIANCE.template.md).
- **AI output.** Outputs from AI features may contain errors or omissions. Review each output on your own before you rely on it.
- **Beta.** Pre-1.0 releases are provided "AS IS", without warranties of any kind. They may change or be discontinued at any time.

Report security issues through [SECURITY.md](SECURITY.md). Community standards are in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
